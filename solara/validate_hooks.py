import ast
import inspect
import typing as t
from enum import Enum

DEFAULT_USE_FUNCTIONS = (
    "use_state",
    "use_reactive",
    "use_thread",
    "use_task",
    "use_effect",
    "use_memo",
)


class InvalidReactivityCauses(Enum):
    USE_AFTER_RETURN = "early return"
    CONDITIONAL_USE = "conditional"
    LOOP_USE = "loop"
    NESTED_FUNCTION_USE = "nested function"
    VARIABLE_ASSIGNMENT = "assignment"


ScopeNodesType = t.Union[ast.For, ast.While, ast.If, ast.FunctionDef]


class HookValidationError(Exception):
    def __init__(self, cause: InvalidReactivityCauses, message: str):
        self.cause = cause
        super().__init__(message)


class HookValidator(ast.NodeVisitor):
    def __init__(self, component: t.Callable, use_functions=DEFAULT_USE_FUNCTIONS):
        self.use_functions = use_functions

        self.root_function_return: t.Optional[ast.Return] = None
        self.outer_scope: t.Optional[ScopeNodesType] = None

        self.filename = component.__code__.co_filename
        self.line_offset = component.__code__.co_firstlineno - 1
        self.component = component

        parsed = ast.parse(inspect.getsource(self.component))
        # Get nodes from inside the function body
        func_definition = t.cast(ast.FunctionDef, parsed.body[0])
        self.function_scope: ast.FunctionDef = func_definition
        self._root_function_scope = self.function_scope

    def run(self):
        for node in self._root_function_scope.body:
            self.visit(node)

    def visit_Call(self, node: ast.Call):
        """Records calls of use functions, i.e. solara.use_state(...)"""

        func = node.func
        if isinstance(func, ast.Call):
            # Nested function, it will appear in another node later
            return
        if isinstance(func, ast.Name):
            id_ = func.id
        elif isinstance(func, ast.Attribute):
            id_ = func.attr
        else:
            raise ValueError(f"Unexpected function node type: {func}, {func.lineno=}")
        if id_ in self.use_functions:
            self.error_on_early_return(node, id_)
            self.error_on_invalid_scope(node, id_)
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self._visit_children_using_scope(node)

    def visit_For(self, node: ast.For):
        self._visit_children_using_scope(node)

    def visit_While(self, node: ast.While):
        self._visit_children_using_scope(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_function_scope = self.function_scope
        self.function_scope = node
        self._visit_children_using_scope(node)
        self.function_scope = old_function_scope

    def _visit_children_using_scope(self, node: ScopeNodesType):
        outer_scope = self.outer_scope
        self.outer_scope = node
        for child in node.body:
            self.visit(child)
        self.outer_scope = outer_scope

    def visit_Assign(self, node: ast.Assign):
        self.error_on_invalid_assign(node)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        """
        Records the earliest return statement in the function
        """
        # Returns are valid in nested functions
        if self.function_scope != self._root_function_scope:
            return
        self.root_function_return = node
        self.generic_visit(node)

    def error_on_invalid_assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Attribute) and node.value.attr in self.use_functions:
            line = node.lineno + self.line_offset
            message = f"Assigning a variable to a reactive function on line {line} is not" " allowed since it complicates the tracking of valid hook use."

            raise HookValidationError(
                InvalidReactivityCauses.VARIABLE_ASSIGNMENT,
                f"{self.get_function_name()}: {message}",
            )

    def error_on_early_return(self, use_node: ast.Call, use_node_id: str):
        """
        Checks if the latest use of a reactive function occurs after the earliest return
        """
        if self.root_function_return and self.root_function_return.lineno <= use_node.lineno:
            offset_return = self.root_function_return.lineno + self.line_offset
            offset_use = use_node.lineno + self.line_offset
            raise HookValidationError(
                InvalidReactivityCauses.USE_AFTER_RETURN,
                f"{self.get_function_name()}: `{use_node_id}` found on line" f" {offset_use} despite early return on line {offset_return}",
            )

    def error_on_invalid_scope(self, use_node: ast.Call, use_node_id: str):
        """
        Checks if the latest use of a reactive function occurs after the earliest return
        """
        if self.outer_scope is None:
            return
        offset_use = use_node.lineno + self.line_offset
        if isinstance(self.outer_scope, ast.If):
            cause = InvalidReactivityCauses.CONDITIONAL_USE
        elif isinstance(self.outer_scope, (ast.For, ast.While)):
            cause = InvalidReactivityCauses.LOOP_USE
        elif isinstance(self.outer_scope, ast.FunctionDef):
            cause = InvalidReactivityCauses.NESTED_FUNCTION_USE
        else:
            raise ValueError(f"Unexpected scope node: {self.outer_scope}")

        scope_line = self.outer_scope.lineno + self.line_offset
        raise HookValidationError(
            cause,
            f"{self.get_function_name()}: `{use_node_id}` found on line" f" {offset_use} within a {cause.value} created on line {scope_line}",
        )

    def get_function_name(self):
        return f"{self.filename} - {self.component.__qualname__}"
