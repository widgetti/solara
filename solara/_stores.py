import copy
import dataclasses
import inspect
from typing import Callable, ContextManager, Generic, Optional, Union, cast
import warnings
from .toestand import ValueBase, KernelStore, S, _find_outside_solara_frame
import solara.util


class _PublicValueNotSet:
    pass


class _SetValueNotSet:
    pass


@dataclasses.dataclass
class StoreValue(Generic[S]):
    private: S  # the internal private value, should never be mutated
    public: Union[S, _PublicValueNotSet]  # this is the value that is exposed in .get(), it is a deep copy of private
    get_traceback: Optional[inspect.Traceback]
    set_value: Union[S, _SetValueNotSet]  # the value that was set using .set(..), we deepcopy this to set private
    set_traceback: Optional[inspect.Traceback]


class MutateDetectorStore(ValueBase[S]):
    def __init__(self, store: KernelStore[StoreValue[S]], equals=solara.util.equals_extra):
        self._storage = store
        self._enabled = True
        super().__init__(equals=equals)

    @property
    def lock(self):
        return self._storage.lock

    def get(self) -> S:
        self.check_mutations()
        self._ensure_public_exists()
        value = self._storage.get()
        # value.public is of type Optional[S], so it's tempting to check for None here,
        # but S could include None as a valid value, so best we can do is cast
        public_value = cast(S, value.public)
        return public_value

    def peek(self) -> S:
        """Return the value without automatically subscribing to listeners."""
        self.check_mutations()
        store_value = self._storage.peek()
        self._ensure_public_exists()
        public_value = cast(S, store_value.public)
        return public_value

    def set(self, value: S):
        self.check_mutations()
        self._ensure_public_exists()
        private = copy.deepcopy(value)
        self._check_equals(private, value)
        frame = _find_outside_solara_frame()
        if frame is not None:
            frame_info = inspect.getframeinfo(frame)
        else:
            frame_info = None
        store_value = StoreValue(private=private, public=_PublicValueNotSet(), get_traceback=None, set_value=value, set_traceback=frame_info)
        self._storage.set(store_value)

    def check_mutations(self):
        self._storage._check_mutation()
        if not self._enabled:
            return
        store_value = self._storage.peek()
        if not isinstance(store_value.public, _PublicValueNotSet) and not self.equals(store_value.public, store_value.private):
            tb = store_value.get_traceback
            # TODO: make the error message as elaborate as below
            msg = (
                f"Reactive variable was read when it had the value of {store_value.private!r}, but was later mutated to {store_value.public!r}.\n"
                "Mutation should not be done on the value of a reactive variable, as in production mode we would be unable to track changes.\n"
            )
            if tb:
                if tb.code_context:
                    code = tb.code_context[0]
                else:
                    code = "<No code context available>"
                msg += f"The last value was read in the following code:\n" f"{tb.filename}:{tb.lineno}\n" f"{code}"
            raise ValueError(msg)
        elif not isinstance(store_value.set_value, _SetValueNotSet) and not self.equals(store_value.set_value, store_value.private):
            tb = store_value.set_traceback
            msg = f"""Reactive variable was set with a value of {store_value.private!r}, but was later mutated mutated to {store_value.set_value!r}.

Mutation should not be done on the value of a reactive variable, as in production mode we would be unable to track changes.

Bad:
    mylist = reactive([]]
    some_values = [1, 2, 3]
    mylist.value = some_values  # you give solara a reference to your list
    some_values.append(4)  # but later mutate it (solara cannot detect this change, so a render will not be triggered)
    # if later on a re-render happens for a different reason, you will read of the mutated list.

Good (if you want the reactive variable to be updated):
    mylist = reactive([]]
    some_values = [1, 2, 3]
    mylist.value = some_values
    mylist.value = some_values + [4]

Good (if you want to keep mutating your own list):
    mylist = reactive([]]
    some_values = [1, 2, 3]
    mylist.value = some_values.copy()  # this gives solara a copy of the list
    some_values.append(4)  # you are free to mutate your own list, solara will not see this

"""
            if tb:
                if tb.code_context:
                    code = tb.code_context[0]
                else:
                    code = "<No code context available>"
                msg += "The last time the value was set was at:\n" f"{tb.filename}:{tb.lineno}\n" f"{code}"
            raise ValueError(msg)

    def _ensure_public_exists(self):
        store_value = self._storage.peek()
        if isinstance(store_value.public, _PublicValueNotSet):
            with self.lock:
                if isinstance(store_value.public, _PublicValueNotSet):
                    frame = _find_outside_solara_frame()
                    if frame is not None:
                        frame_info = inspect.getframeinfo(frame)
                    else:
                        frame_info = None
                    store_value.public = copy.deepcopy(store_value.private)
                    self._check_equals(store_value.public, store_value.private)
                    store_value.get_traceback = frame_info

    def _check_equals(self, a: S, b: S):
        if not self._enabled:
            return
        if not self.equals(a, b):
            frame = _find_outside_solara_frame()
            if frame is not None:
                frame_info = inspect.getframeinfo(frame)
            else:
                frame_info = None

            warn = """The equals function for this reactive value returned False when comparing a deepcopy to itself.

This reactive variable will not be able to detect mutations correctly, and is therefore disabled.

To avoid this warning, and to ensure that mutation detection works correctly, please provide a better equals function to the reactive variable.
A good choice for dataframes and numpy arrays might be solara.util.equals_pickle, which will also attempt to compare the pickled values of the objects.

Example:
df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
reactive_df = solara.reactive(df, equals=solara.util.equals_pickle)
"""
            tb = frame_info
            if tb:
                if tb.code_context:
                    code = tb.code_context[0]
                else:
                    code = "<No code context available>"
                warn += "This warning was triggered from:\n" f"{tb.filename}:{tb.lineno}\n" f"{code}"
            warnings.warn(warn)
            self._enabled = False

    def subscribe(self, listener: Callable[[S], None], scope: Optional[ContextManager] = None):
        def listener_wrapper(new: StoreValue[S], previous: StoreValue[S]):
            self._ensure_public_exists()
            assert not isinstance(new.public, _PublicValueNotSet)
            assert not isinstance(previous.public, _PublicValueNotSet)
            previous_value = previous.set_value if not isinstance(previous.set_value, _SetValueNotSet) else previous.private
            new_value = new.set_value
            assert not isinstance(new_value, _SetValueNotSet)
            if not self.equals(new_value, previous_value):
                listener(new_value)

        return self._storage.subscribe_change(listener_wrapper, scope=scope)

    def subscribe_change(self, listener: Callable[[S, S], None], scope: Optional[ContextManager] = None):
        def listener_wrapper(new: StoreValue[S], previous: StoreValue[S]):
            self._ensure_public_exists()
            assert not isinstance(new.public, _PublicValueNotSet)
            assert not isinstance(previous.public, _PublicValueNotSet)
            previous_value = previous.set_value if not isinstance(previous.set_value, _SetValueNotSet) else previous.private
            new_value = new.set_value
            assert not isinstance(new_value, _SetValueNotSet)
            if not self.equals(new_value, previous_value):
                listener(new_value, previous_value)

        return self._storage.subscribe_change(listener_wrapper, scope=scope)
