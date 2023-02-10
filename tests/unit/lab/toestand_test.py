import dataclasses
import unittest.mock
from typing import Any, Callable, Dict, Optional, TypeVar, cast

import ipyvuetify as v
import react_ipywidgets as react
from typing_extensions import TypedDict

import solara
import solara as sol
from solara.lab.toestand import (
    Field,
    FieldDict,
    FieldList,
    ModelBase,
    Reactive,
    Ref,
    reactive,
    use_sync_external_store,
)
from solara.server import app, kernel
from tests.unit.common import click

S = TypeVar("S")  # used for state


la = Reactive("lala")
la.value


def field(value: S) -> Field[S]:
    return Field(value)


class Bears(ModelBase, frozen=True):
    type = field(cast(Optional[str], "brown"))
    count = field(1)


class BearsReactive(Reactive[Bears]):
    def increase_population(self):
        self.fields.count.value = self.fields.count.value + 1


count = Reactive[int](0)
bears = BearsReactive(Bears())


# def test_ref():
#     assert count.value == 0
#     count.value = 1
#     assert count.value == 1
#     mock = unittest.mock.Mock()
#     unsub = count.subscribe(mock)
#     count.value = 2
#     mock.assert_called_with(2)
#     unsub()
#     count.value = 3
#     mock.assert_called_with(2)


B = TypeVar("B", bound=Bears)


def test_exp():
    assert bears.fields.type.value == "brown"
    bears.fields.type.value = "brown"
    bears.fields.type.value = "purple"
    assert bears.fields.type.value == "purple"
    bears.fields.type.value = "brown"
    # bears.fields.type.value = 2


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


def test_subscribe():
    # bear_store = BearReactive(bears)
    # bears = Bears()
    mock = unittest.mock.Mock()
    mock_type = unittest.mock.Mock()
    mock_count = unittest.mock.Mock()
    unsub = []
    unsub += [bears.subscribe(mock)]
    unsub += [bears.fields.type.subscribe(mock_type)]
    unsub += [bears.fields.count.subscribe(mock_count)]
    mock.assert_not_called()
    bears.update(type="purple")
    mock_count.assert_not_called()
    mock_type.assert_called_with("purple")
    mock.assert_called_with(Bears(type="purple", count=1))

    mock_type.reset_mock()
    bears.update(count=3)
    mock.assert_called_with(Bears(type="purple", count=3))
    mock_type.assert_not_called()
    mock_count.assert_called_with(3)
    for u in unsub:
        u()


def test_scopes(no_app_context):
    mock_global = unittest.mock.Mock()
    unsub = []
    unsub += [bears.subscribe(mock_global)]

    kernel_shared = kernel.Kernel()
    assert app.current_context[app.get_current_thread_key()] is None

    context1 = app.AppContext(id="toestand-1", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})
    context2 = app.AppContext(id="toestand-2", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})

    with context1:
        mock1 = unittest.mock.Mock()
        unsub += [bears.subscribe(mock1)]
    with context2:
        mock2 = unittest.mock.Mock()
        unsub += [bears.subscribe(mock2)]

    mock_global.assert_not_called()

    with context2:
        bears.update(type="purple")
    mock_global.assert_not_called()
    mock1.assert_not_called()
    mock2.assert_called_with(Bears(type="purple", count=1))
    mock2.reset_mock()

    with context1:
        bears.update(count=3)
    mock_global.assert_not_called()
    mock1.assert_called_with(Bears(type="brown", count=3))
    mock2.assert_not_called()
    mock1.reset_mock()

    bears.update(type="yellow")
    mock_global.assert_called_with(Bears(type="yellow", count=1))
    mock1.assert_not_called()
    mock2.assert_not_called()

    mock_global.reset_mock()
    for u in unsub:
        u()


def test_store_primitive():
    string_value = Reactive[str]("foo")
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

    assert count.get() == 3
    assert last.get() == 3
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


def test_nested_update():
    # this effectively test the RLock vs Lock
    mock = unittest.mock.Mock()
    mock_type = unittest.mock.Mock()
    mock_count = unittest.mock.Mock()
    unsub = []
    unsub += [bears.subscribe(mock)]
    unsub += [bears.fields.type.subscribe(mock_type)]
    unsub += [bears.fields.count.subscribe(mock_count)]

    def reset_count(new_type):
        bears.update(count=0)

    bears.fields.type.subscribe(reset_count)
    bears.fields.type.value = "purple"
    mock.assert_called_with(Bears(type="purple", count=0))
    mock_type.assert_called_with("purple")
    mock_count.assert_called_with(0)
    for u in unsub:
        u()


def test_store_nested():
    class City(ModelBase, frozen=True):
        name: Field[str] = Field("Amsterdam")
        population: Field[int] = Field(1000000)

    class Person(ModelBase, frozen=True):
        name: Field[str] = Field("--")
        height: Field[float] = Field(0.0)

    class Country(ModelBase, frozen=True):
        dicator: Field[Person] = Field[Person](Person(name="Jos", height=1.8))
        name: Field[str] = Field("Netherlands")
        cities: FieldList[City] = FieldList[City](default_factory=list)
        people: FieldDict[str, Person] = FieldDict[str, Person](default_factory=dict)

    # no need for subclasses
    mock = unittest.mock.Mock()
    people = {"Jos": Person(name="Jos", height=1.8)}
    people_copy = people.copy()
    nl = Reactive[Country](
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=1000000)],
            people=people,
            dicator=Person(name="Jos", height=1.8),
        )
    )
    # store = Reactive[Country](nl)
    unsub = nl.subscribe(mock)
    mock.assert_not_called()
    # country = store.fields
    # population_accessor = Ref(store.fields.cities[0].population)
    # Country.dicator._name

    population_accessor = nl.fields.cities[0].population
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

    nl.fields.people["Jos"].height.set(1.9)
    assert people == people_copy
    mock.assert_called_with(
        Country(
            name="Netherlands",
            cities=[City(name="Amsterdam", population=10)],
            people={"Jos": Person(name="Jos", height=1.9)},
            dicator=Person(name="Jos", height=1.8),
        )
    )

    nl.fields.people["Jos"].height.value = 2.1
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
    nl.fields.people.update(lambda x: {**x, "Maria": Person(name="Maria", height=1.7)})
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
    nl.fields.dicator.fields.height.set(2.0)
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


def test_bear_basics():
    mock = unittest.mock.Mock()
    unsub = bears.subscribe(mock)
    mock.assert_not_called()
    bears.increase_population()
    assert mock.call_count == 1
    mock.assert_called_with(Bears(type="brown", count=2))
    bears.increase_population()
    assert mock.call_count == 2
    mock.assert_called_with(Bears(type="brown", count=3))

    # setter = bears.setter(bears.fields.count)
    setter = bears.fields.count.set
    setter(5)
    assert mock.call_count == 3
    mock.assert_called_with(Bears(type="brown", count=5))

    unsub()
    bears.increase_population()
    assert mock.call_count == 3

    # now test a subfield
    mock_count = unittest.mock.Mock()
    # count = Ref(bears.fields.count)
    count = bears.fields.count
    bears.subscribe(mock)
    count.subscribe(mock_count)
    count.set(4)
    assert count.get() == 4
    assert bears.get() == Bears(type="brown", count=4)
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
    setter(5)
    assert mock.call_count == 3
    mock.assert_called_with(Bears(type="brown", count=5))

    unsub()
    bear_store.increase_population()
    assert mock.call_count == 3


def test_bear_store_react():
    # bear_store = BearReactive(bears)

    @react.component
    def BearCounter():
        bear_count = bears.use(lambda bear: bear.count)
        return sol.Info(f"{bear_count} bears around here")

    @react.component
    def Controls():
        return sol.Button("add bear", on_click=bears.increase_population)

    @react.component
    def App():
        with sol.VBox() as main:
            BearCounter()
            Controls()
        return main

    el = App()
    box, rc = react.render(el, handle_error=False)
    assert rc.find(v.Alert).widget.children[0] == "1 bears around here"
    click(rc.find(v.Btn).widget)
    assert rc.find(v.Alert).widget.children[0] == "2 bears around here"

    # the storage should live in the app context to support multiple users/connections
    kernel_shared = kernel.Kernel()
    context1 = app.AppContext(id="bear-1", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})
    context2 = app.AppContext(id="bear-2", kernel=kernel_shared, control_sockets=[], widgets={}, templates={})
    rcs = []
    for context in [context1, context2]:
        with context:
            rc.render(el)
            el = App()
            box, rc = react.render(el, handle_error=False)
            rcs.append(rc)
            assert rc._find(v.Alert).widget.children[0] == "1 bears around here"
            assert bears.fields.count.value == 1
            click(rc._find(v.Btn).widget)
            assert bears.fields.count.value == 2
            assert rc._find(v.Alert).widget.children[0] == "2 bears around here"

    rc = rcs[1]
    with context2:
        rc.render(el)
        assert bears.fields.count.value == 2
        assert rc._find(v.Alert).widget.children[0] == "2 bears around here"
        click(rc._find(v.Btn).widget)
        assert bears.fields.count.value == 3
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"

    rc = rcs[0]
    with context1:
        rc.render(el)
        assert bears.fields.count.value == 2
        assert rc._find(v.Alert).widget.children[0] == "2 bears around here"
        click(rc._find(v.Btn).widget)
        assert bears.fields.count.value == 3
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"
        click(rc._find(v.Btn).widget)
        assert bears.fields.count.value == 4
        assert rc._find(v.Alert).widget.children[0] == "4 bears around here"
        click(rc._find(v.Btn).widget)
        assert bears.fields.count.value == 5
        assert rc._find(v.Alert).widget.children[0] == "5 bears around here"

    rc = rcs[1]
    with context2:
        rc.render(el)
        assert bears.fields.count.value == 3
        assert rc._find(v.Alert).widget.children[0] == "3 bears around here"
        click(rc._find(v.Btn).widget)
        assert bears.fields.count.value == 4
        assert rc._find(v.Alert).widget.children[0] == "4 bears around here"
        bears.fields.count.value = 10
        assert rc._find(v.Alert).widget.children[0] == "10 bears around here"


def test_simplest():

    settings = reactive(cast(Dict[Any, Any], {"bears": 2, "theme": "dark"}))
    unsub = settings.subscribe(print)  # noqa

    settings.update(theme="light")
    # prints: {"bears": 2, "theme": "light"}

    unsub()  # remove event listener
    theme_accessor = cast(Field[str], settings.fields["theme"])  # type: ignore

    # Now use it in a React component

    import react_ipywidgets as react

    renders = 0

    import solara as sol

    @react.component
    def ThemeInfo():
        # the lambda function here is called a selector, it 'selects' out the state you want
        # theme = settings.use(lambda state: state["theme"])
        theme = theme_accessor.use_value()
        return sol.Info(f"Using theme {theme}")

    @react.component
    def ThemeSelector():
        theme, set_theme = theme_accessor.use_state()
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


class Fish(ModelBase, frozen=True):
    fishes: Field[int] = Field(0)


F = TypeVar("F", bound=Fish)


class FishReactive(Reactive[F]):
    def jump(self):
        print("jump")  # noqa


class AppStateComposite(ModelBase, frozen=True):
    bear: Field[Bears] = Field(Bears())
    fish: Field[Fish] = Field(Fish(fishes=1))


class AppState(Reactive[AppStateComposite]):
    bears: BearsReactive

    def __post__init__(self):
        # for composite stores, manually create the substores
        self.bears = BearsReactive(self.fields.bear)
        # it's ok not to have a substore for fish

    def eat(self):
        state = self.get()
        bears = state.bear.count
        fish = Fish(fishes=max(0, state.fish.fishes - bears))
        self.update(fish=fish)


def test_app_composite():
    mock = unittest.mock.Mock()
    fish_state = Fish(fishes=4)
    app_state = AppStateComposite(bear=bears.value, fish=fish_state)
    app_store = AppState(app_state)
    app_store.subscribe(mock)

    assert app_store.fields.bear.fields.count.value == 1
    assert app_store.bears.get().count == 1
    assert app_store.get().fish.fishes == 4

    mock.assert_not_called()
    app_store.eat()
    assert app_store.get().fish.fishes == 3
    assert mock.call_count == 1
    mock.assert_called_with(AppStateComposite(bear=Bears(type="brown", count=1), fish=Fish(fishes=3)))

    app_store.bears.increase_population()
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


# @dataclass(frozen=True)
# class AppInherit(Bears, Fish):
#     pass


# class AppStateInherit(BearReactive[AppInherit], FishReactive[AppInherit], Reactive[AppInherit]):
#     def eat(self):
#         state = self.get()
#         bears = state.count
#         self.update(fishes=max(0, state.fishes - bears))


# def test_app_inherit():
#     mock = unittest.mock.Mock()
#     app = AppInherit(type="brown", count=1, fishes=4)
#     app_store = AppStateInherit(app)
#     app_store.subscribe(mock)

#     assert app_store.get().count == 1
#     assert app_store.get().fishes == 4

#     mock.assert_not_called()
#     app_store.eat()
#     assert app_store.get().fishes == 3
#     assert mock.call_count == 1
#     mock.assert_called_with(AppInherit(type="brown", count=1, fishes=3))

#     app_store.increase_population()
#     mock.assert_called_with(AppInherit(type="brown", count=2, fishes=3))
#     assert mock.call_count == 2
#     assert app_store.get().count == 2
#     assert app_store.get().count == 2
#     assert app_store.get().fishes == 3

#     app_store.eat()
#     assert app_store.get().fishes == 1
#     assert mock.call_count == 3
#     mock.assert_called_with(AppInherit(type="brown", count=2, fishes=1))
#     app_store.eat()
#     assert app_store.get().fishes == 0
#     assert mock.call_count == 4
#     mock.assert_called_with(AppInherit(type="brown", count=2, fishes=0))


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


# # TODO:
# # def test_store_scope_application():
# #     import solara as sol
# #     import solara.scope

# #     bear_store = BearReactive({"type": "brown", "count": 1}, storage=sol.scope.application)
# #     try:
# #         assert bear_store.get() == {"type": "brown", "count": 1}

# #         @react.component
# #         def BearCounter():
# #             bears = bear_store.use(lambda bear: bear.count)
# #             # bears = app_store.use(lambda app: app.bear.count)
# #             return sol.Info(f"{bears} bears around here")

# #         @react.component
# #         def Controls():
# #             return sol.Button("add bear", on_click=bear_store.increase_population)

# #         @react.component
# #         def App():
# #             with sol.VBox() as main:
# #                 BearCounter()
# #                 Controls()
# #             return main

# #         app = App()
# #         box, rc = react.render(app, handle_error=False)

# #         assert rc._find(v.Alert).widget.children[0] == "1 bears around here"
# #         bear_store.increase_population()
# #         assert rc._find(v.Alert).widget.children[0] == "2 bears around here"

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

    df_store = Reactive(DataFrame(df=df))
    mock.reset_mock()
    unsub = df_store.subscribe(mock)
    mock.assert_not_called()
    df_store.set(DataFrame(df=df2))
    mock.assert_called_once()
    mock.reset_mock()
    Ref(df_store.fields.df).set(df)
    mock.assert_called_once()
    unsub()
