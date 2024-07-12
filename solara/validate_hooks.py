import ast
import inspect
import re
import typing as t
from enum import Enum
import sys
import warnings

DEFAULT_USE_FUNCTIONS = ("^use_.*$",)


class InvalidReactivityCause(Enum):
    USE_AFTER_RETURN = "early return"
    CONDITIONAL_USE = "conditional"
    LOOP_USE = "loop"
    NESTED_FUNCTION_USE = "nested function"
    VARIABLE_ASSIGNMENT = "assignment"
    EXCEPTION_USE = "exception"


if sys.version_info < (3, 11):
    ScopeNodeType = t.Union[ast.For, ast.While, ast.If, ast.Try, ast.FunctionDef]
    TryNodes = (ast.Try,)
else:
    # except* nodes are only standardized in 3.11+
    ScopeNodeType = t.Union[ast.For, ast.While, ast.If, ast.Try, ast.TryStar, ast.FunctionDef]
    TryNodes = (ast.Try, ast.TryStar)


class HookValidationError(Exception):
    def __init__(self, cause: InvalidReactivityCause, message: str):
        self.cause = cause
        super().__init__(message)


class HookValidator(ast.NodeVisitor):
    def __init__(self, component: t.Callable, use_functions=DEFAULT_USE_FUNCTIONS):
        self.use_functions = [re.compile(use_func) for use_func in use_functions]

        self.root_function_return: t.Optional[ast.Return] = None
        self.outer_scope: t.Optional[ScopeNodeType] = None

        self.filename = component.__code__.co_filename
        self.line_offset = component.__code__.co_firstlineno - 1
        self.component = component

        self.source = inspect.getsource(self.component)
        # lines before we dedent
        self.lines = self.source.split("\n")
        # dedent the source code to avoid indentation errors
        parsed_source = inspect.cleandoc(self.source)
        parsed = ast.parse(parsed_source)
        # Get nodes from inside the function body
        func_definition = t.cast(ast.FunctionDef, parsed.body[0])
        self.function_scope: ast.FunctionDef = func_definition
        self._root_function_scope = self.function_scope

    def run(self):
        import solara.settings

        if solara.settings.main.check_hooks == "off":
            return
        func_def_line = self.lines[self._root_function_scope.lineno - 1]
        if "#" in func_def_line:
            comment = func_def_line[func_def_line.index("#") + 1 :]
            if "noqa" in comment:
                return
        try:
            for node in self._root_function_scope.body:
                self.visit(node)
        except HookValidationError as e:
            if solara.settings.main.check_hooks == "error":
                raise e
            elif solara.settings.main.check_hooks == "warn":
                warnings.warn(str(e))

    def matches_use_function(self, name: str) -> bool:
        return any(use_func.match(name) for use_func in self.use_functions)

    def node_to_scope_cause(self, node: ScopeNodeType) -> InvalidReactivityCause:
        if isinstance(node, ast.If):
            return InvalidReactivityCause.CONDITIONAL_USE
        elif isinstance(node, (ast.For, ast.While)):
            return InvalidReactivityCause.LOOP_USE
        elif isinstance(node, ast.FunctionDef):
            return InvalidReactivityCause.NESTED_FUNCTION_USE
        elif isinstance(node, TryNodes):
            return InvalidReactivityCause.EXCEPTION_USE
        else:
            raise ValueError(f"Unexpected scope node type: {node}, line={node.lineno}")

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
            raise ValueError(f"Unexpected function node type: {func}, line={node.lineno}")
        if self.matches_use_function(id_):
            self.error_on_early_return(node, id_)
            self.error_on_invalid_scope(node, id_)
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self._visit_children_using_scope(node)

    def visit_For(self, node: ast.For):
        self._visit_children_using_scope(node)

    def visit_While(self, node: ast.While):
        self._visit_children_using_scope(node)

    def visit_Try(self, node: ast.Try) -> t.Any:
        self._visit_children_using_scope(node)

    if sys.version_info >= (3, 11):

        def visit_TryStar(self, node: ast.TryStar) -> t.Any:
            self._visit_children_using_scope(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        old_function_scope = self.function_scope
        self.function_scope = node
        self._visit_children_using_scope(node)
        self.function_scope = old_function_scope

    def _visit_children_using_scope(self, node: ScopeNodeType):
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
            message = "Assigning a variable to a reactive function is not allowed since it complicates the tracking of valid hook use."

            raise HookValidationError(
                InvalidReactivityCause.VARIABLE_ASSIGNMENT,
                f"{self.get_source_context(line)}: {message}",
            )

    def error_on_early_return(self, use_node: ast.Call, use_node_id: str):
        """
        Checks if the latest use of a reactive function occurs after the earliest return
        """
        if self.root_function_return and self.root_function_return.lineno <= use_node.lineno:
            offset_return = self.root_function_return.lineno + self.line_offset
            offset_use = use_node.lineno + self.line_offset
            raise HookValidationError(
                InvalidReactivityCause.USE_AFTER_RETURN,
                f"{self.get_source_context(offset_use)}: `{use_node_id}` found despite early return on line {offset_return}",
            )

    def error_on_invalid_scope(self, use_node: ast.Call, use_node_id: str):
        """
        Checks if the latest use of a reactive function occurs after the earliest return
        """
        if self.outer_scope is None:
            return
        offset_use = use_node.lineno + self.line_offset
        cause = self.node_to_scope_cause(self.outer_scope)

        scope_line = self.outer_scope.lineno + self.line_offset
        line = self.lines[use_node.lineno - 1]
        # check if we have a # noqa comment
        if "#" in line:
            comment = line[line.index("#") + 1 :]
            if "noqa" in comment:
                return
        raise HookValidationError(
            cause,
            f"{self.get_source_context(offset_use)}: `{use_node_id}` found within a {cause.value} created on line {scope_line}",
        )

    def get_source_context(self, lineno):
        return f"{self.filename}:{lineno}: {self.component.__qualname__}"
