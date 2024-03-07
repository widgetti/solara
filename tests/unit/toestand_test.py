import dataclasses
import threading
import unittest.mock
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, TypeVar

import ipyvuetify as v
import react_ipywidgets as react
from typing_extensions import TypedDict

import solara
import solara as sol
import solara.lab
import solara.toestand as toestand
from solara.server import kernel, kernel_context
from solara.toestand import Reactive, Ref, State, use_sync_external_store

from .common import click

HERE = Path(__file__).parent


@dataclasses.dataclass(frozen=True)
class Bears:
    type: str
    count: int = dataclasses.field()


B = TypeVar("B", bound=Bears)


class BearReactive(Reactive[B]):
    def increase_population(self):
        self.update(count=self.get().count + 1)


bears: Bears = Bears(type="brown", count=1)


def test_store_bare():
    # no need for subclasses
    mock = unittest.mock.Mock()
    mock_change = unittest.mock.Mock()
    store = Reactive[dict]({"string": "foo", "int": 42})
    unsub = store.subscribe(mock)
    unsub_change = store.subscribe_change(mock_change)
    mock.assert_not_called()
    mock_change.assert_not_called()
    store.update(string="bar")
    mock.assert_called_with({"string": "bar", "int": 42})
    mock_change.assert_called_with({"string": "bar", "int": 42}, {"string": "foo", "int": 42})

    unsub()
    unsub_change()


def test_list_index_error():
    mock = unittest.mock.Mock()
    mock_change = unittest.mock.Mock()
    values = solara.reactive([1, 2, 3])
    item3 = Ref(values.fields[2])
    unsub = item3.subscribe(mock)
    unsub_change = item3.subscribe_change(mock_change)
    values.value = [1, 2, 4]
    mock.assert_called_with(4)
    mock_change.assert_called_with(4, 3)
    mock.reset_mock()
    mock_change.reset_mock()
    values.value = [1, 2]
    mock.assert_not_called()
    mock_change.assert_not_called()
    unsub()
    unsub_change()


def test_dict_index_error():
    mock = unittest.mock.Mock()
    mock_change = unittest.mock.Mock()
    values = solara.reactive({"a": 1, "b": 2, "c": 3})
    item3 = Ref(values.fields["c"])
    unsub = item3.subscribe(mock)
    unsub_change = item3.subscribe_change(mock_change)
    values.value = {"a": 1, "b": 2, "c": 4}
    mock.assert_called_with(4)
    mock_change.assert_called_with(4, 3)
    mock.reset_mock()
    mock_change.reset_mock()
    values.value = {"a": 1, "b": 2}
    mock.assert_not_called()
    mock_change.assert_not_called()
    unsub()
    unsub_change()


def test_subscribe():
    bear_store = BearReactive(bears)
    mock = unittest.mock.Mock()
    mock_type = unittest.mock.Mock()
    mock_count = unittest.mock.Mock()
    unsub = []
    unsub += [bear_store.subscribe(mock)]
    unsub += [Ref(bear_store.fields.type).subscribe(mock_type)]
    unsub += [Ref(bear_store.fields.count).subscribe(mock_count)]
    mock.assert_not_called()
    bear_store.update(type="purple")
    mock.assert_called_with(Bears(type="purple", count=1))
    mock_type.assert_called_with("purple")
    mock_count.assert_not_called()

    mock_type.reset_mock()
    bear_store.update(count=3)
    mock.assert_called_with(Bears(type="purple", count=3))
    mock_type.assert_not_called()
    mock_count.assert_called_with(3)
    for u in unsub:
        u()


def test_scopes(no_kernel_context):
    bear_store = BearReactive(bears)
    mock_global = unittest.mock.Mock()
    unsub = []
    unsub += [bear_store.subscribe(mock_global)]

    kernel_shared = kernel.Kernel()
    assert kernel_context.current_context[kernel_context.get_current_thread_key()] is None

    context1 = kernel_context.VirtualKernelContext(id="toestand-1", kernel=kernel_shared, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="toestand-2", kernel=kernel_shared, session_id="session-2")

    with context1:
        mock1 = unittest.mock.Mock()
        unsub += [bear_store.subscribe(mock1)]
    with context2:
        mock2 = unittest.mock.Mock()
        unsub += [bear_store.subscribe(mock2)]

    mock_global.assert_not_called()

    with context2:
        bear_store.update(type="purple")
    mock_global.assert_not_called()
    mock1.assert_not_called()
    mock2.assert_called_with(Bears(type="purple", count=1))
    mock2.reset_mock()

    with context1:
        bear_store.update(count=3)
    mock_global.assert_not_called()
    mock1.assert_called_with(Bears(type="brown", count=3))
    mock2.assert_not_called()
    mock1.reset_mock()

    bear_store.update(type="yellow")
    mock_global.assert_called_with(Bears(type="yellow", count=1))
    mock1.assert_not_called()
    mock2.assert_not_called()

    mock_global.reset_mock()
    for u in unsub:
        u()


def test_nested_update():
    # this effectively test the RLock vs Lock
    bear_store = BearReactive(bears)

    mock = unittest.mock.Mock()
    mock_type = unittest.mock.Mock()
    mock_count = unittest.mock.Mock()
    unsub = []
    unsub += [bear_store.subscribe(mock)]
    unsub += [Ref(bear_store.fields.type).subscribe(mock_type)]
    unsub += [Ref(bear_store.fields.count).subscribe(mock_count)]

    def reset_count(new_type):
        bear_store.update(count=0)

    Ref(bear_store.fields.type).subscribe(reset_count)
    Ref(bear_store.fields.type).value = "purple"
    mock.assert_called_with(Bears(type="purple", count=0))
    mock_type.assert_called_with("purple")
    mock_count.assert_called_with(0)
    for u in unsub:
        u()


def test_store_nested():
    @dataclasses.dataclass(frozen=True)
    class City:
        name: str
        population: int

    @dataclasses.dataclass(frozen=True)
    class Person:
        name: str
        height: float

    @dataclasses.dataclass(frozen=True)
    class Country:
        dicator: Person
        name: str
        cities: List[City] = dataclasses.field(default_factory=list)
        people: Dict[str, Person] = dataclasses.field(default_factory=dict)

    # no need for subclasses
    mock = unittest.mock.Mock()
    people = {"Jos": Person(name="Jos", height=1.8)}
    people_copy = people.copy()
    nl = Country(
        name="Netherlands",
        cities=[City(name="Amsterdam", population=1000000)],
        people=people,
        dicator=Person(name="Jos", height=1.8),
    )
    store = Reactive[Country](nl)
    unsub = store.subscribe(mock)
    mock.assert_not_called()
    country = store.fields
    population_accessor = Ref(store.fields.cities[0].population)
    assert population_accessor.get() == 1000000
    population_accessor.set(10)
    assert population_accessor.get() == 10

    mock.assert_called_with(
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people=people_copy,
            dicator=Person(name="Jos", height=1.8),
        )
    )

    Ref(country.people["Jos"].height).set(1.9)
    assert people == people_copy
    mock.assert_called_with(
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={"Jos": Person(name="Jos", height=1.9)},
            dicator=Person(name="Jos", height=1.8),
        )
    )

    Ref(country.people["Jos"].height).value = 2.1
    assert people == people_copy
    mock.assert_called_with(
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={"Jos": Person(name="Jos", height=2.1)},
            dicator=Person(name="Jos", height=1.8),
        )
    )

    # TODO: new name?
    # Ref(country.people["Jos"].height).set(lambda x: x + 0.1)
    # mock.assert_called_with(
    #     Country(
    #         name="Netherlands",
    #         cities=[City(name="Amsterdam", population=10)],
    #         people={"Jos": Person(name="Jos", height=2.0)},
    #         dicator=Person(name="Jos", height=1.8),
    #     ),
    # )

    Ref(country.people).update(lambda x: {**x, "Maria": Person(name="Maria", height=1.7)})
    mock.assert_called_with(
        Country(
            dicator=Person(name="Jos", height=1.8),
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={
                "Jos": Person(name="Jos", height=2.1),
                "Maria": Person(name="Maria", height=1.7),
            },
        )
    )
    Ref(country.dicator.height).set(2.0)
    mock.assert_called_with(
        Country(
            dicator=Person(name="Jos", height=2.0),
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={
                "Jos": Person(name="Jos", height=2.1),
                "Maria": Person(name="Maria", height=1.7),
            },
        )
    )

    unsub()


def test_bear_store_basics():
    mock = unittest.mock.Mock()
    bear_store = BearReactive(bears)
    unsub = bear_store.subscribe(mock)
    mock.assert_not_called()
    bear_store.increase_population()
    mock.assert_called_with(Bears(type="brown", count=2))
    bear_store.increase_population()
    assert mock.call_count == 2
    mock.assert_called_with(Bears(type="brown", count=3))

    setter = bear_store.setter(bear_store.fields.count)
    setter(5)
    assert mock.call_count == 3
    mock.assert_called_with(Bears(type="brown", count=5))

    unsub()
    bear_store.increase_population()
    assert mock.call_count == 3

    # now test a subfield
    mock_count = unittest.mock.Mock()
    count = Ref(bear_store.fields.count)
    bear_store.subscribe(mock)
    count.subscribe(mock_count)
    count.set(4)
    assert count.get() == 4
    assert bear_store.get() == Bears(type="brown", count=4)
    mock.assert_called_with(Bears(type="brown", count=4))
    mock_count.assert_called_with(4)


def test_bear_store_basics_dict():
    class Bears(TypedDict):
        type: str
        count: int

    bears = Bears(type="brown", count=1)

    class BearReactive(Reactive[Bears]):
        def increase_population(self):
            self.update(count=self.get()["count"] + 1)

    mock = unittest.mock.Mock()
    bear_store = BearReactive(bears)
    unsub = bear_store.subscribe(mock)
    mock.assert_not_called()
    bear_store.increase_population()
    mock.assert_called_with(Bears(type="brown", count=2))
    bear_store.increase_population()
    assert mock.call_count == 2
    mock.assert_called_with(Bears(type="brown", count=3))

    setter = bear_store.setter(bear_store.fields["count"])  # type: ignore
    setter(5)  # type: ignore
    assert mock.call_count == 3
    mock.assert_called_with(Bears(type="brown", count=5))

    unsub()
    bear_store.increase_population()
    assert mock.call_count == 3


def test_bear_store_react():
    bear_store = BearReactive(bears)

    @react.component
    def BearCounter():
        bear_count = bear_store.use(lambda bear: bear.count)
        return sol.Info(f"{bear_count} bears around here")

    @react.component
    def Controls():
        return sol.Button("add bear", on_click=bear_store.increase_population)

    @react.component
    def App():
        with sol.VBox() as main:
            BearCounter()
            Controls()
        return main

    el = App()
    box, rc = react.render(el, handle_error=False)
    assert rc._find(v.Alert).widget.children[0] == "1 bears around here"
    click(rc._find(v.Btn).widget)
    assert rc._find(v.Alert).widget.children[0] == "2 bears around here"

    # the storage should live in the app context to support multiple users/connections
    kernel_shared = kernel.Kernel()
    context1 = kernel_context.VirtualKernelContext(id="bear-1", kernel=kernel_shared, session_id="session-1")
    context2 = kernel_context.VirtualKernelContext(id="bear-2", kernel=kernel_shared, session_id="session-2")
    rcs = []
    for context in [context1, context2]:
        with context:
            el = App()
            box, rc = react.render(el, handle_error=False)
            rcs.append(rc)
            # el = App()
            # box, rc = react.render(el, handle_error=False)
            assert rc._find(v.Alert).widget.children[0] == "1 bears around here"
            assert Ref(bear_store.fields.count).value == 1
            click(rc._find(v.Btn).widget)
            assert rc._find(v.Alert).widget.children[0] == "2 bears around here"
            assert Ref(bear_store.fields.count).value == 2

    rc = rcs[1]
    with context2:
        rc.render(el)
        assert Ref(bear_store.fields.count).value == 2
        assert rc._find(v.Alert).widget.children[0] == "2 bears around here"
        click(rc._find(v.Btn).widget)
        assert Ref(bear_store.fields.count).value == 3
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"

    rc = rcs[0]
    with context1:
        rc.render(el)
        assert Ref(bear_store.fields.count).value == 2
        assert rc._find(v.Alert).widget.children[0] == "2 bears around here"
        click(rc._find(v.Btn).widget)
        assert Ref(bear_store.fields.count).value == 3
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"
        click(rc._find(v.Btn).widget)
        assert Ref(bear_store.fields.count).value == 4
        assert rc._find(v.Alert).widget.children[0] == "4 bears around here"
        click(rc._find(v.Btn).widget)
        assert Ref(bear_store.fields.count).value == 5
        assert rc._find(v.Alert).widget.children[0] == "5 bears around here"

    rc = rcs[1]
    with context2:
        rc.render(el)
        assert Ref(bear_store.fields.count).value == 3
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"
        click(rc._find(v.Btn).widget)
        assert Ref(bear_store.fields.count).value == 4
        assert rc._find(v.Alert).widget.children[0] == "4 bears around here"
        Ref(bear_store.fields.count).value = 10
        assert rc._find(v.Alert).widget.children[0] == "10 bears around here"


def test_simplest():
    settings = State({"bears": 2, "theme": "dark"})
    unsub = settings.subscribe(print)  # noqa

    settings.update(theme="light")
    # prints: {"bears": 2, "theme": "light"}

    unsub()  # remove event listener
    theme_accessor = Ref(settings.fields["theme"])  # type: ignore

    # Now use it in a React component

    import react_ipywidgets as react

    renders = 0

    import solara as sol

    @react.component
    def ThemeInfo():
        # the lambda function here is called a selector, it 'selects' out the state you want
        # theme = settings.use(lambda state: state["theme"])
        theme = Ref(settings.fields["theme"]).use_value()  # type: ignore
        return sol.Info(f"Using theme {theme}")

    @react.component
    def ThemeSelector():
        theme, set_theme = Ref(settings.fields["theme"]).use_state()  # type: ignore
        with sol.ToggleButtonsSingle(theme, on_value=set_theme) as main:  # type: ignore
            sol.Button("dark")
            sol.Button("light")
        return main

    @react.component
    def Test():
        nonlocal renders
        renders += 1
        with sol.VBox() as main:
            ThemeInfo()
            ThemeSelector()
        return main

    box, rc = react.render(Test(), handle_error=False)
    assert rc._find(v.Alert).widget.children[0] == "Using theme light"
    assert rc._find(v.BtnToggle).widget.v_model == 1
    theme_accessor.set("dark")
    assert rc._find(v.Alert).widget.children[0] == "Using theme dark"
    assert rc._find(v.BtnToggle).widget.v_model == 0
    rc._find(v.BtnToggle).widget.v_model = 1
    assert rc._find(v.Alert).widget.children[0] == "Using theme light"
    renders_before = renders
    settings.update(bears=3)
    assert renders == renders_before


@dataclasses.dataclass(frozen=True)
class Fish:
    fishes: int


F = TypeVar("F", bound=Fish)


class FishReactive(Reactive[F]):
    def jump(self):
        print("jump")  # noqa


@dataclasses.dataclass(frozen=True)
class AppStateComposite:
    bear: Bears
    fish: Fish


class AppState(Reactive[AppStateComposite]):
    bears: BearReactive

    def __post__init__(self):
        # for composite stores, manually create the substores
        self.bears = BearReactive(Ref(self.fields.bear))
        # it's ok not to have a substore for fish

    def eat(self):
        state = self.get()
        bears = state.bear.count
        fish = Fish(fishes=max(0, state.fish.fishes - bears))
        self.update(fish=fish)


def test_store_primitive():
    string_value = State("foo")
    mock = unittest.mock.Mock()
    unsub = string_value.subscribe(mock)
    mock.assert_not_called()
    string_value.set("bar")
    mock.assert_called_with("bar")
    unsub()


def test_store_computed():
    list_store = Reactive[list]([1, 2, 3])

    count = list_store.computed(len)
    last = list_store.computed(lambda x: x[-1] if x else None)

    assert count._auto_subscriber.value.reactive_used is None
    assert count.get() == 3
    assert count._auto_subscriber.value.reactive_used == {list_store}

    assert last._auto_subscriber.value.reactive_used is None
    assert last.get() == 3
    assert last._auto_subscriber.value.reactive_used == {list_store}
    mock = unittest.mock.Mock()
    mock_last = unittest.mock.Mock()
    unsub = count.subscribe(mock)
    unsub_last = last.subscribe(mock_last)
    mock.assert_not_called()
    mock_last.assert_not_called()
    list_store.set([1, 2, 3, 42])
    mock.assert_called_with(4)
    mock_last.assert_called_with(42)
    unsub()
    unsub_last()
    list_store.set([])
    mock.assert_called_with(4)
    mock_last.assert_called_with(42)


def test_app_composite():
    mock = unittest.mock.Mock()
    fish_state = Fish(fishes=4)
    app_state = AppStateComposite(bear=bears, fish=fish_state)
    app_store = AppState(app_state)
    app_store.subscribe(mock)

    assert app_store.get().bear.count == 1
    assert app_store.bears.get().count == 1
    assert app_store.get().fish.fishes == 4

    mock.assert_not_called()
    app_store.eat()
    assert app_store.get().fish.fishes == 3
    assert mock.call_count == 1
    mock.assert_called_with(AppStateComposite(bear=Bears(type="brown", count=1), fish=Fish(fishes=3)))

    app_store.bears.increase_population()  # type: ignore
    mock.assert_called_with(AppStateComposite(bear=Bears(type="brown", count=2), fish=Fish(fishes=3)))
    assert mock.call_count == 2
    assert app_store.get().bear.count == 2
    assert app_store.bears.get().count == 2
    assert app_store.get().fish.fishes == 3

    app_store.eat()
    assert app_store.get().fish.fishes == 1
    assert mock.call_count == 3
    mock.assert_called_with(AppStateComposite(bear=Bears(type="brown", count=2), fish=Fish(fishes=1)))
    app_store.eat()
    assert app_store.get().fish.fishes == 0
    assert mock.call_count == 4
    mock.assert_called_with(AppStateComposite(bear=Bears(type="brown", count=2), fish=Fish(fishes=0)))


@dataclasses.dataclass(frozen=True)
class AppInherit(Bears, Fish):
    pass


class AppStateInherit(BearReactive[AppInherit], FishReactive[AppInherit], Reactive[AppInherit]):
    def eat(self):
        state = self.get()
        bears = state.count
        self.update(fishes=max(0, state.fishes - bears))


def test_app_inherit():
    mock = unittest.mock.Mock()
    app = AppInherit(type="brown", count=1, fishes=4)
    app_store = AppStateInherit(app)
    app_store.subscribe(mock)

    assert app_store.get().count == 1
    assert app_store.get().fishes == 4

    mock.assert_not_called()
    app_store.eat()
    assert app_store.get().fishes == 3
    assert mock.call_count == 1
    mock.assert_called_with(AppInherit(type="brown", count=1, fishes=3))

    app_store.increase_population()
    mock.assert_called_with(AppInherit(type="brown", count=2, fishes=3))
    assert mock.call_count == 2
    assert app_store.get().count == 2
    assert app_store.get().count == 2
    assert app_store.get().fishes == 3

    app_store.eat()
    assert app_store.get().fishes == 1
    assert mock.call_count == 3
    mock.assert_called_with(AppInherit(type="brown", count=2, fishes=1))
    app_store.eat()
    assert app_store.get().fishes == 0
    assert mock.call_count == 4
    mock.assert_called_with(AppInherit(type="brown", count=2, fishes=0))


def test_use_external_store():
    state = {"a": 1, "b": 2, "c": 3}
    update = lambda: None  # noqa

    def subscribe(callback: Callable[[], None]) -> Callable[[], None]:
        nonlocal update
        update = callback

        def cleanup():
            nonlocal update
            update = lambda: None  # noqa

        return cleanup

    renders = 0
    state_last = {}

    @react.component
    def Test():
        nonlocal renders
        nonlocal state_last
        state_last = use_sync_external_store(subscribe, lambda: state)
        renders += 1
        return sol.Button()

    box, rc = react.render(Test(), handle_error=False)
    assert renders == 1
    update()
    assert renders == 1
    assert state_last == state
    state = state.copy()
    state["b"] = 12
    update()
    assert state_last == state
    assert renders == 2


# TODO:
# def test_store_scope_application():
#     import solara as sol
#     import solara.scope

#     bear_store = BearReactive({"type": "brown", "count": 1}, storage=sol.scope.application)
#     try:
#         assert bear_store.get() == {"type": "brown", "count": 1}

#         @react.component
#         def BearCounter():
#             bears = bear_store.use(lambda bear: bear.count)
#             # bears = app_store.use(lambda app: app.bear.count)
#             return sol.Info(f"{bears} bears around here")

#         @react.component
#         def Controls():
#             return sol.Button("add bear", on_click=bear_store.increase_population)

#         @react.component
#         def App():
#             with sol.VBox() as main:
#                 BearCounter()
#                 Controls()
#             return main

#         app = App()
#         box, rc = react.render(app, handle_error=False)

#         assert rc._find(v.Alert).widget.children[0] == "1 bears around here"
#         bear_store.increase_population()
#         assert rc._find(v.Alert).widget.children[0] == "2 bears around here"


#         storage_key = bear_store.storage_key
#         redis_dict = bear_store._storage.observable_dict
#         redis_dict[storage_key] = {"type": "brown", "count": 3}
#         # TODO: wait for the store to update
#         time.sleep(0.1)
#         # assert rc._find(v.Alert).wait_for_widget.children[0] == "3 bears around here"
#         # assert rc._find(v.Alert).wait_for_single().widget.children[0] == "3 bears around here"
#         rc._find(v.Alert).widget.children[0] == "3 bears around here"
#     finally:
#         bear_store._storage.delete()
def test_dataframe():
    mock = unittest.mock.Mock()
    import pandas as pd

    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    df2 = df.copy()
    store = Reactive[pd.DataFrame](df)
    unsub = store.subscribe(mock)
    mock.assert_not_called()
    store.set(df)
    mock.assert_not_called()
    store.set(df2)
    mock.assert_called_with(df2)

    unsub()
    store.set(df)

    @solara.component
    def Test():
        df = store.use_value()
        return solara.Info(repr(id(df)))

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Alert).widget.children[0] == repr(id(df))
    df2 = df.copy()
    store.set(df2)
    assert rc.find(v.Alert).widget.children[0] == repr(id(df2))

    @dataclasses.dataclass(frozen=True)
    class DataFrame:
        df: Optional[pd.DataFrame] = dataclasses.field()

    df_store = Reactive[DataFrame](DataFrame(df=df))
    mock.reset_mock()
    unsub = Ref(df_store.fields).subscribe(mock)
    mock.assert_not_called()
    df_store.set(DataFrame(df=df2))
    mock.assert_called_once()
    mock.reset_mock()
    Ref(df_store.fields.df).set(df)
    mock.assert_called_once()
    unsub()


def test_thread_local():
    def test1():
        assert solara.lab.thread_local.reactive_used is None

    t = threading.Thread(target=test1)
    t.start()
    t.join()

    def test2():
        myset: Set[solara.lab.ValueBase] = set()
        solara.lab.local.reactive_used = myset
        assert solara.lab.thread_local.reactive_used is myset

    t = threading.Thread(target=test2)
    t.start()
    t.join()

    def test3():
        assert solara.lab.thread_local.reactive_used is None

    t = threading.Thread(target=test3)
    t.start()
    t.join()


def test_reactive_auto_subscribe(kernel_context):
    x = Reactive(1)
    y = Reactive("hi")
    extra = Reactive("extra")
    count = Reactive(1)

    @solara.component
    def Test():
        if x.value == 0:
            _ = extra.value  # access conditional
        _ = x.value  # access twice
        return solara.IntSlider(label=y.value, value=x.value)

    @solara.component
    def Main():
        for i in range(count.value):
            Test()
        if count.value == 0:
            return solara.Info("no slider")

    box, rc = solara.render(Main(), handle_error=False)
    assert rc.find(v.Slider).widget.v_model == 1
    x.value = 2
    assert rc.find(v.Slider).widget.v_model == 2
    y.value = "hello"
    assert rc.find(v.Slider).widget.label == "hello"
    assert len(x._storage.listeners2) == 1
    # force an extra listener
    x.value = 0
    # and remove it
    x.value = 1

    count.value = 2
    assert len(rc.find(v.Slider)) == 2
    assert len(x._storage.listeners2[kernel_context.id]) == 2
    x.value = 3
    assert rc.find(v.Slider)[0].widget.v_model == 3
    assert len(x._storage.listeners2[kernel_context.id]) == 2

    count.value = 1
    assert len(rc.find(v.Slider)) == 1
    count.value = 0
    assert len(rc.find(v.Slider)) == 0

    rc.close()
    assert not x._storage.listeners[kernel_context.id]
    assert not x._storage.listeners2[kernel_context.id]


def test_reactive_auto_subscribe_sub():
    bears = Reactive(Bears(type="brown", count=1))
    renders = 0

    ref = Ref(bears.fields.count)
    reactive_used = None

    @solara.component
    def Test():
        nonlocal reactive_used
        nonlocal renders
        reactive_used = toestand.thread_local.reactive_used
        renders += 1
        count = ref.value
        return solara.Info(f"{count} bears around here")

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Alert).widget.children[0] == "1 bears around here"
    assert reactive_used == {ref}
    ref.value += 1
    assert rc.find(v.Alert).widget.children[0] == "2 bears around here"
    assert reactive_used == {ref}
    # now check that we didn't listen to the while object, just count changes
    renders_before = renders
    Ref(bears.fields.type).value = "pink"
    assert renders == renders_before


def test_reactive_auto_subscribe_cleanup(kernel_context):
    x = Reactive(1)
    y = Reactive("hi")
    renders = 0

    @solara.component
    def Test():
        nonlocal renders
        renders += 1
        if x.value == 42:
            _ = y.value  # access conditional
        if x.value == 0:
            _ = y.value  # access conditional
            x.value = 100
        return solara.IntSlider("test", value=x.value)

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Slider).widget.v_model == 1
    assert renders == 1
    assert len(x._storage.listeners2) == 1
    assert len(y._storage.listeners2) == 0
    x.value = 42
    assert renders == 2
    assert len(x._storage.listeners2[kernel_context.id]) == 1
    assert len(y._storage.listeners2[kernel_context.id]) == 1

    # this triggers two renders, where during the first one we use y, but the seconds we don't
    x.value = 0
    assert rc.find(v.Slider).widget.v_model == 100
    assert len(x._storage.listeners2[kernel_context.id]) == 1
    # which means we shouldn't have a listener on y
    assert len(y._storage.listeners2[kernel_context.id]) == 0

    rc.close()
    assert not x._storage.listeners[kernel_context.id]
    assert not y._storage.listeners2[kernel_context.id]


def test_reactive_auto_subscribe_subfield_limit(kernel_context):
    bears = Reactive(Bears(type="brown", count=1))
    renders = 0
    reactive_used = None

    @solara.component
    def Test():
        nonlocal renders
        nonlocal reactive_used
        reactive_used = toestand.thread_local.reactive_used
        renders += 1
        _ = bears.value  # access it to trigger the subscription
        return solara.IntSlider("test", value=Ref(bears.fields.count).value)

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Slider).widget.v_model == 1
    assert renders == 1
    assert reactive_used is not None
    assert len(reactive_used) == 2  # bears and bears.fields.count
    Ref(bears.fields.count).value = 2
    assert renders == 2
    assert len(reactive_used) == 2  # bears and bears.fields.count
    rc.close()
    assert not bears._storage.listeners[kernel_context.id]
    assert not bears._storage.listeners2[kernel_context.id]


def test_reactive_batch_update():
    count = Reactive(1)
    mock1 = unittest.mock.Mock()
    mock2 = unittest.mock.Mock()

    @solara.component
    def Test1():
        mock1(count.value)
        return solara.IntSlider("test", value=count.value)

    @solara.component
    def Test2():
        mock2(count.value)
        return solara.IntSlider("test", value=count.value)

    @solara.component
    def Test():
        Test1()
        Test2()

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Slider)[0].widget.v_model == 1
    assert rc.find(v.Slider)[1].widget.v_model == 1
    assert rc.render_count == 1
    assert mock1.call_count == 1
    assert mock2.call_count == 1
    count.value = 2
    assert mock1.call_count == 2
    assert mock2.call_count == 2
    assert rc.find(v.Slider)[0].widget.v_model == 2
    assert rc.find(v.Slider)[1].widget.v_model == 2
    assert mock1.call_count == 2
    assert mock2.call_count == 2
    assert rc.render_count == 2


def test_repr():
    x = Reactive(1)
    assert repr(x).startswith("<Reactive value=1")
    assert str(x) == "1"
    y = Reactive("hi")
    assert repr(y).startswith("<Reactive value='hi'")
    assert str(y) == "'hi'"

    class Foo:
        bar = Reactive(1)

    assert repr(Foo.bar).startswith("<Reactive Foo.bar value=1")
    assert str(Foo.bar) == "Foo.bar=1"

    bears = Reactive(Bears(type="brown", count=1))
    s = repr(bears.fields.count)
    assert s.startswith("<Field <Reactive value=Bears(type='brown', count=1)")
    assert s.endswith(".count>")


def test_use_reactive_update():
    control = Reactive(0)
    var1 = Reactive(1)
    var2 = Reactive(2)

    @solara.component
    def Test():
        var: Reactive[int]
        if control.value == 0:
            var = solara.use_reactive(var1)
        else:
            var = solara.use_reactive(var2)

        return solara.IntSlider("test: " + str(var.value), value=var)

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Slider).widget.v_model == 1
    assert rc.find(v.Slider).widget.label == "test: 1"
    control.value = 1
    assert rc.find(v.Slider).widget.v_model == 2
    assert rc.find(v.Slider).widget.label == "test: 2"
    # the slider should be using the same reactive variable (var2)
    rc.find(v.Slider).widget.v_model = 1
    assert var2.value == 1
    assert rc.find(v.Slider).widget.label == "test: 1"
    rc.close()


def test_use_reactive_ref():
    reactive_var = Reactive({"a": 1})
    reactive_ref = Ref(reactive_var.fields["a"])

    reactive_ref_test: Reactive[int] = None

    @solara.component
    def Test():
        nonlocal reactive_ref_test
        reactive_ref_test = solara.use_reactive(reactive_ref)
        return solara.IntSlider("test: " + str(reactive_ref.value), value=reactive_ref_test)

    box, rc = solara.render(Test(), handle_error=False)
    assert reactive_ref_test is not None
    assert reactive_ref_test.value == 1
    rc.close()


def test_use_reactive_on_change():
    control = Reactive(0)
    var1 = Reactive(1)
    var2 = Reactive(2)
    mock1 = unittest.mock.Mock()
    mock2 = unittest.mock.Mock()

    @solara.component
    def Test():
        var: Reactive[int]
        if control.value == 0:
            var = solara.use_reactive(var1, on_change=mock1)
        else:
            var = solara.use_reactive(var2, on_change=mock2)

        return solara.IntSlider("test", value=var)

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Slider).widget.v_model == 1
    assert mock1.call_count == 0
    assert mock2.call_count == 0
    # if it changes downstream, it should trigger on_change
    rc.find(v.Slider).widget.v_model = 10
    assert mock1.call_count == 1
    assert mock2.call_count == 0

    control.value = 1
    assert mock1.call_count == 1
    assert mock2.call_count == 0
    assert rc.find(v.Slider).widget.v_model == 2
    rc.find(v.Slider).widget.v_model = 20
    assert mock1.call_count == 1
    assert mock2.call_count == 1

    control.value = 0
    assert rc.find(v.Slider).widget.v_model == 10
    rc.find(v.Slider).widget.v_model = 100
    assert mock1.call_count == 2
    assert mock2.call_count == 1

    rc.close()


def test_reactive_var_in_use_effect():

    var = Reactive(1)

    @solara.component
    def Test():
        def modify():
            var.value = 2

        solara.use_effect(modify)
        # note: just pass the value, not the reactive variable
        # otherwise the test passes. It is important *this*
        # component listens to the reactive variable.
        return solara.IntSlider("test", value=var.value)

    box, rc = solara.render(Test(), handle_error=False)
    assert rc.find(v.Slider).widget.v_model == 2


def test_singleton():
    from solara.toestand import Singleton

    calls = 0

    def factory():
        nonlocal calls
        calls += 1
        return Bears(type="brown", count=1)

    s = Singleton(factory)
    assert calls == 0
    assert s.get() == Bears(type="brown", count=1)
    assert calls == 1
    assert s.get() == Bears(type="brown", count=1)
    assert calls == 1


def test_computed():
    context_id = "1"
    from solara.toestand import Computed

    x = Reactive(1)
    y = Reactive(2)
    calls = 0

    def conditional_add():
        nonlocal calls
        calls += 1
        if x.value == 0:
            return 42
        else:
            return x.value + y.value

    z = Computed(conditional_add)
    assert z._auto_subscriber.value.reactive_used is None
    assert z.value == 3
    assert z._auto_subscriber.value.reactive_used == {x, y}
    # assert z._auto_subscriber.subscribed == 1
    assert len(x._storage.listeners[context_id]) == 0
    assert len(x._storage.listeners2[context_id]) == 1
    assert len(y._storage.listeners[context_id]) == 0
    assert len(y._storage.listeners2[context_id]) == 1
    assert calls == 1
    x.value = 2
    assert z.value == 4
    assert z._auto_subscriber.value.reactive_used == {x, y}
    assert calls == 2
    y.value = 3
    assert z.value == 5
    assert z._auto_subscriber.value.reactive_used == {x, y}
    assert calls == 3
    assert len(x._storage.listeners2[context_id]) == 1
    assert len(y._storage.listeners2[context_id]) == 1

    # now we do not depend on y anymore
    x.value = 0
    assert z.value == 42
    assert z._auto_subscriber.value.reactive_used == {x}
    assert len(x._storage.listeners2[context_id]) == 1
    assert len(y._storage.listeners2[context_id]) == 0
    assert calls == 4
    y.value = 4
    assert z.value == 42
    assert z._auto_subscriber.value.reactive_used == {x}
    assert calls == 4


def test_computed_reload(no_kernel_context):
    import solara.server.reload
    from solara.server.app import AppScript

    name = str(HERE / "toestand_computed_reload.py")
    # if we reload, the _type counter will reset, but we will not
    # execute all reactive variables again, which causes a mismatch between
    # the reactive variable id's
    solara.toestand.KernelStore._type_counter.clear()
    app = AppScript(name)
    try:
        assert len(app.routes) == 1
        route = app.routes[0]
        c = app.run()
        kernel_shared = kernel.Kernel()
        kernel_context = solara.server.kernel_context.VirtualKernelContext(id="1", kernel=kernel_shared, session_id="session-1")
        with kernel_context:
            root = solara.RoutingProvider(children=[c], routes=app.routes, pathname="/")
            box, rc = solara.render(root, handle_error=False)
            kernel_context.app_object = rc
            text = rc.find(v.TextField)
            assert text.widget.v_model == "2.0"
            route.module.value_reactive.value = 2  # type: ignore
            module = route.module
            assert text.widget.v_model == "3.0"
            solara.server.reload.reloader.requires_reload = True
            kernel_context.restart()
        solara.toestand.KernelStore._type_counter.clear()
        c = app.run()
        with kernel_context:
            route = app.routes[0]
            root = solara.RoutingProvider(children=[c], routes=app.routes, pathname="/")
            box, rc = solara.render(root, handle_error=False)
            kernel_context.app_object = rc
            text = rc.find(v.TextField)
            assert text.widget.v_model == "3.0"
            assert route.module is not module
            route.module.value_reactive.value = 3  # type: ignore
            assert text.widget.v_model == "4.0"
    finally:
        app.close()
