import dataclasses
import unittest.mock
from typing import Callable, Dict, List, TypeVar

import ipyvuetify as v
import react_ipywidgets as react
from typing_extensions import TypedDict

import solara as sol
from solara.server import app, kernel
from solara.toestand import Store, SubStorageAttr, X, use_sync_external_store

from .common import click


@dataclasses.dataclass(frozen=True)
class BearState:
    type: str
    count: int = dataclasses.field()


B = TypeVar("B", bound=BearState)


class BearStore(Store[B]):
    def increase_population(self):
        self.update(count=self.get().count + 1)


bear_state: BearState = BearState(type="brown", count=1)


def test_store_bare():
    # no need for subclasses
    mock = unittest.mock.Mock()
    store = Store[dict]({"string": "foo", "int": 42})
    unsub = store.subscribe(mock)
    mock.assert_not_called()
    store.update(string="bar")
    mock.assert_called_with({"string": "bar", "int": 42})

    unsub()


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
    store = Store[Country](nl)
    unsub = store.subscribe(mock)
    mock.assert_not_called()
    country = store.fields
    population_accessor = X(store.fields.cities[0].population)
    population_accessor.set(10)

    mock.assert_called_with(
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people=people_copy,
            dicator=Person(name="Jos", height=1.8),
        )
    )

    X(country.people["Jos"].height).set(1.9)
    assert people == people_copy
    mock.assert_called_with(
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={"Jos": Person(name="Jos", height=1.9)},
            dicator=Person(name="Jos", height=1.8),
        )
    )

    X(country.people["Jos"].height).update(lambda x: x + 0.1)
    mock.assert_called_with(
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={"Jos": Person(name="Jos", height=2.0)},
            dicator=Person(name="Jos", height=1.8),
        ),
    )

    X(country.people).update(lambda x: {**x, "Maria": Person(name="Maria", height=1.7)})
    mock.assert_called_with(
        Country(
            dicator=Person(name="Jos", height=1.8),
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={
                "Jos": Person(name="Jos", height=2.0),
                "Maria": Person(name="Maria", height=1.7),
            },
        )
    )
    X(country.dicator.height).set(2.0)
    mock.assert_called_with(
        Country(
            dicator=Person(name="Jos", height=2.0),
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={
                "Jos": Person(name="Jos", height=2.0),
                "Maria": Person(name="Maria", height=1.7),
            },
        )
    )

    unsub()


def test_bear_store_basics():
    mock = unittest.mock.Mock()
    bear_store = BearStore(bear_state)
    unsub = bear_store.subscribe(mock)
    mock.assert_not_called()
    bear_store.increase_population()
    mock.assert_called_with(BearState(type="brown", count=2))
    bear_store.increase_population()
    assert mock.call_count == 2
    mock.assert_called_with(BearState(type="brown", count=3))

    setter = bear_store.setter(bear_store.fields.count)
    setter(5)
    assert mock.call_count == 3
    mock.assert_called_with(BearState(type="brown", count=5))

    unsub()
    bear_store.increase_population()
    assert mock.call_count == 3


def test_bear_store_basics_dict():
    class BearState(TypedDict):
        type: str
        count: int

    bear_state = BearState(type="brown", count=1)

    class BearStore(Store[BearState]):
        def increase_population(self):
            self.update(count=self.get()["count"] + 1)

    mock = unittest.mock.Mock()
    bear_store = BearStore(bear_state)
    unsub = bear_store.subscribe(mock)
    mock.assert_not_called()
    bear_store.increase_population()
    mock.assert_called_with(BearState(type="brown", count=2))
    bear_store.increase_population()
    assert mock.call_count == 2
    mock.assert_called_with(BearState(type="brown", count=3))

    setter = bear_store.setter(bear_store.fields["count"])
    setter(5)
    assert mock.call_count == 3
    mock.assert_called_with(BearState(type="brown", count=5))

    unsub()
    bear_store.increase_population()
    assert mock.call_count == 3


def test_bear_store_react():
    bear_store = BearStore(bear_state)

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
    context1 = app.AppContext(id="1", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})
    context2 = app.AppContext(id="2", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})
    for context in [context1, context2]:
        with context:
            rc.render(el)
            # el = App()
            # box, rc = react.render(el, handle_error=False)
            assert rc._find(v.Alert).widget.children[0] == "1 bears around here"
            click(rc._find(v.Btn).widget)
            assert rc._find(v.Alert).widget.children[0] == "2 bears around here"

    with context2:
        rc.render(el)
        assert rc._find(v.Alert).widget.children[0] == "2 bears around here"
        click(rc._find(v.Btn).widget)
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"

    with context1:
        rc.render(el)
        assert rc._find(v.Alert).widget.children[0] == "2 bears around here"
        click(rc._find(v.Btn).widget)
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"
        click(rc._find(v.Btn).widget)
        assert rc._find(v.Alert).widget.children[0] == "4 bears around here"
        click(rc._find(v.Btn).widget)
        assert rc._find(v.Alert).widget.children[0] == "5 bears around here"

    with context2:
        rc.render(el)
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"
        click(rc._find(v.Btn).widget)
        assert rc._find(v.Alert).widget.children[0] == "4 bears around here"


def test_simplest():
    from solara.toestand import Store

    settings = Store({"bears": 2, "theme": "dark"})
    unsub = settings.subscribe(print)  # noqa

    settings.update(theme="light")
    # prints: {"bears": 2, "theme": "light"}

    unsub()  # remove event listener
    theme_accessor = X(settings.fields["theme"])

    # Now use it in a React component

    import react_ipywidgets as react

    renders = 0

    import solara as sol

    @react.component
    def ThemeInfo():
        # the lambda function here is called a selector, it 'selects' out the state you want
        # theme = settings.use(lambda state: state["theme"])
        theme = X(settings.fields["theme"]).use()
        return sol.Info(f"Using theme {theme}")

    @react.component
    def ThemeSelector():
        theme, set_theme = X(settings.fields["theme"]).use_state()
        with sol.ToggleButtonsSingle(theme, on_value=set_theme) as main:
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
class FishState:
    fishes: int


F = TypeVar("F", bound=FishState)


class FishStore(Store[F]):
    def jump(self):
        print("jump")  # noqa


@dataclasses.dataclass(frozen=True)
class AppStateComposite:
    bear: BearState
    fish: FishState


class AppStore(Store[AppStateComposite]):
    bears: BearStore

    def __post__init__(self, storage):
        # for composite stores, manually create the substores
        sub = SubStorageAttr(storage=storage, key="bear")
        self.bears = BearStore(self.get().bear, storage=sub)
        # it's ok not to have a substore for fish

    def eat(self):
        state = self.get()
        bears = state.bear.count
        fish = FishState(fishes=max(0, state.fish.fishes - bears))
        self.update(fish=fish)


def test_app_composite():
    mock = unittest.mock.Mock()
    fish_state = FishState(fishes=4)
    app_state = AppStateComposite(bear=bear_state, fish=fish_state)
    app_store = AppStore(app_state)
    app_store.subscribe(mock)

    assert app_store.get().bear.count == 1
    assert app_store.bears.get().count == 1
    assert app_store.get().fish.fishes == 4

    mock.assert_not_called()
    app_store.eat()
    assert app_store.get().fish.fishes == 3
    assert mock.call_count == 1
    mock.assert_called_with(AppStateComposite(bear=BearState(type="brown", count=1), fish=FishState(fishes=3)))

    app_store.bears.increase_population()
    mock.assert_called_with(AppStateComposite(bear=BearState(type="brown", count=2), fish=FishState(fishes=3)))
    assert mock.call_count == 2
    assert app_store.get().bear.count == 2
    assert app_store.bears.get().count == 2
    assert app_store.get().fish.fishes == 3

    app_store.eat()
    assert app_store.get().fish.fishes == 1
    assert mock.call_count == 3
    mock.assert_called_with(AppStateComposite(bear=BearState(type="brown", count=2), fish=FishState(fishes=1)))
    app_store.eat()
    assert app_store.get().fish.fishes == 0
    assert mock.call_count == 4
    mock.assert_called_with(AppStateComposite(bear=BearState(type="brown", count=2), fish=FishState(fishes=0)))


@dataclasses.dataclass(frozen=True)
class AppStateInherit(BearState, FishState):
    pass


class AppStoreInherit(BearStore[AppStateInherit], FishStore[AppStateInherit], Store[AppStateInherit]):
    def eat(self):
        state = self.get()
        bears = state.count
        self.update(fishes=max(0, state.fishes - bears))


def test_app_inherit():
    mock = unittest.mock.Mock()
    app_state = AppStateInherit(type="brown", count=1, fishes=4)
    app_store = AppStoreInherit(app_state)
    app_store.subscribe(mock)

    assert app_store.get().count == 1
    assert app_store.get().fishes == 4

    mock.assert_not_called()
    app_store.eat()
    assert app_store.get().fishes == 3
    assert mock.call_count == 1
    mock.assert_called_with(AppStateInherit(type="brown", count=1, fishes=3))

    app_store.increase_population()
    mock.assert_called_with(AppStateInherit(type="brown", count=2, fishes=3))
    assert mock.call_count == 2
    assert app_store.get().count == 2
    assert app_store.get().count == 2
    assert app_store.get().fishes == 3

    app_store.eat()
    assert app_store.get().fishes == 1
    assert mock.call_count == 3
    mock.assert_called_with(AppStateInherit(type="brown", count=2, fishes=1))
    app_store.eat()
    assert app_store.get().fishes == 0
    assert mock.call_count == 4
    mock.assert_called_with(AppStateInherit(type="brown", count=2, fishes=0))


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

#     bear_store = BearStore({"type": "brown", "count": 1}, storage=sol.scope.application)
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
