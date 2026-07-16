from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from parser import (
    ArrayLiteral,
    Assign,
    AwaitExpr,
    BinaryOp,
    Block,
    BoolLiteral,
    BreakStmt,
    CallExpr,
    ClassDecl,
    ContinueStmt,
    DictLiteral,
    DoWhileStmt,
    ExportStmt,
    FloatLiteral,
    ForStmt,
    FuncDecl,
    Identifier,
    IfStmt,
    ImportStmt,
    IndexAccess,
    IntLiteral,
    LambdaExpr,
    MemberAccess,
    MatchStmt,
    NewExpr,
    Node,
    NullLiteral,
    Program,
    ReturnStmt,
    StringLiteral,
    StructDecl,
    ThrowStmt,
    TryCatch,
    UnaryOp,
    VarDecl,
    WhileStmt,
)


class SemanticError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(f"{message}" if line == 0 else f"{message} at line {line}, column {column}")
        self.message = message
        self.line = line
        self.column = column


class SymbolTable:
    def __init__(self, parent: Optional["SymbolTable"] = None):
        self.parent = parent
        self.symbols: Dict[str, Any] = {}

    def define(self, name: str, value: Any = None) -> None:
        self.symbols[name] = value

    def get(self, name: str) -> Any:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.get(name)
        return None

    def has(self, name: str) -> bool:
        return name in self.symbols or (self.parent is not None and self.parent.has(name))


@dataclass
class SemanticAnalyzer:
    root: Optional[Node] = None
    current_scope: Optional[SymbolTable] = None
    current_function: Optional[FuncDecl] = None
    current_class: Optional[ClassDecl] = None
    in_loop: int = 0
    loop_stack: List[bool] = field(default_factory=list)
    errors: List[SemanticError] = field(default_factory=list)

    def analyze(self, root: Node) -> Node:
        self.root = root
        self.current_scope = SymbolTable()
        self._visit_program(root)
        if self.errors:
            raise self.errors[0]
        return root

    def _visit_program(self, node: Program) -> None:
        self.current_scope.define("print")
        self.current_scope.define("input")
        self.current_scope.define("len")
        self.current_scope.define("range")
        self.current_scope.define("int")
        self.current_scope.define("float")
        self.current_scope.define("str")
        self.current_scope.define("bool")
        self.current_scope.define("type")
        self.current_scope.define("isinstance")
        self.current_scope.define("list")
        self.current_scope.define("dict")
        self.current_scope.define("set")
        self.current_scope.define("open")
        self.current_scope.define("math")
        self.current_scope.define("io")
        self.current_scope.define("string")
        self.current_scope.define("Error")
        self.current_scope.define("super")
        for stmt in node.statements:
            self._visit(stmt)

    def _visit(self, node: Node) -> None:
        if node is None:
            return
        if isinstance(node, Program):
            self._visit_program(node)
        elif isinstance(node, Block):
            self._visit_block(node)
        elif isinstance(node, VarDecl):
            self._visit_var_decl(node)
        elif isinstance(node, Assign):
            self._visit_assign(node)
        elif isinstance(node, FuncDecl):
            self._visit_func_decl(node)
        elif isinstance(node, ClassDecl):
            self._visit_class_decl(node)
        elif isinstance(node, IfStmt):
            self._visit_if_stmt(node)
        elif isinstance(node, WhileStmt):
            self._visit_while_stmt(node)
        elif isinstance(node, ForStmt):
            self._visit_for_stmt(node)
        elif isinstance(node, DoWhileStmt):
            self._visit_do_while_stmt(node)
        elif isinstance(node, ReturnStmt):
            self._visit_return_stmt(node)
        elif isinstance(node, BreakStmt):
            self._visit_break_stmt(node)
        elif isinstance(node, ContinueStmt):
            self._visit_continue_stmt(node)
        elif isinstance(node, BinaryOp):
            self._visit_binary_op(node)
        elif isinstance(node, UnaryOp):
            self._visit_unary_op(node)
        elif isinstance(node, CallExpr):
            self._visit_call_expr(node)
        elif isinstance(node, NewExpr):
            self._visit_new_expr(node)
        elif isinstance(node, MemberAccess):
            self._visit_member_access(node)
        elif isinstance(node, IndexAccess):
            self._visit_index_access(node)
        elif isinstance(node, ImportStmt):
            self._visit_import_stmt(node)
        elif isinstance(node, ExportStmt):
            self._visit_export_stmt(node)
        elif isinstance(node, TryCatch):
            self._visit_try_catch(node)
        elif isinstance(node, ThrowStmt):
            self._visit_throw_stmt(node)
        elif isinstance(node, AwaitExpr):
            self._visit_await_expr(node)
        elif isinstance(node, ArrayLiteral):
            self._visit_array_literal(node)
        elif isinstance(node, DictLiteral):
            self._visit_dict_literal(node)
        elif isinstance(node, MatchStmt):
            self._visit_match_stmt(node)
        elif isinstance(node, StructDecl):
            self._visit_struct_decl(node)
        elif isinstance(node, Identifier):
            self._visit_identifier(node)
        elif isinstance(node, IntLiteral):
            node.type = "int"
        elif isinstance(node, FloatLiteral):
            node.type = "float"
        elif isinstance(node, StringLiteral):
            node.type = "string"
        elif isinstance(node, BoolLiteral):
            node.type = "bool"
        elif isinstance(node, NullLiteral):
            node.type = "null"
        elif isinstance(node, LambdaExpr):
            self._visit_lambda_expr(node)
        else:
            node.type = "unknown"

    def _visit_block(self, node: Block) -> None:
        scope = SymbolTable(self.current_scope)
        prev_scope = self.current_scope
        self.current_scope = scope
        for stmt in node.statements:
            self._visit(stmt)
        self.current_scope = prev_scope

    def _visit_var_decl(self, node: VarDecl) -> None:
        if self.current_scope.has(node.name):
            raise SemanticError(f"Duplicate declaration: {node.name}", 0, 0)
        self.current_scope.define(node.name)
        if node.initializer is not None:
            self._visit(node.initializer)
        node.type = node.type_annotation or "unknown"

    def _visit_assign(self, node: Assign) -> None:
        self._visit(node.value)
        if isinstance(node.target, Identifier):
            if not self.current_scope.has(node.target.name):
                raise SemanticError(f"Undeclared identifier: {node.target.name}")
            node.target.type = self.current_scope.get(node.target.name)
            node.type = node.value.type if hasattr(node.value, "type") else "unknown"
        else:
            self._visit(node.target)
            node.type = node.value.type if hasattr(node.value, "type") else "unknown"

    def _visit_func_decl(self, node: FuncDecl) -> None:
        if self.current_scope.has(node.name):
            raise SemanticError(f"Duplicate declaration: {node.name}")
        self.current_scope.define(node.name, node.return_type or "func")
        prev_func = self.current_function
        prev_class = self.current_class
        self.current_function = node
        self.current_class = None
        scope = SymbolTable(self.current_scope)
        for pname, _ in node.params:
            scope.define(pname, "unknown")
        prev_scope = self.current_scope
        self.current_scope = scope
        self._visit(node.body)
        self.current_scope = prev_scope
        self.current_function = prev_func
        self.current_class = prev_class
        node.type = node.return_type or "func"

    def _visit_class_decl(self, node: ClassDecl) -> None:
        if self.current_scope.has(node.name):
            raise SemanticError(f"Duplicate declaration: {node.name}")
        self.current_scope.define(node.name, "class")
        prev_class = self.current_class
        self.current_class = node
        for stmt in node.body:
            self._visit(stmt)
        self.current_class = prev_class
        node.type = "class"

    def _visit_if_stmt(self, node: IfStmt) -> None:
        self._visit(node.condition)
        self._visit(node.then_body)
        if node.else_body is not None:
            self._visit(node.else_body)

    def _visit_while_stmt(self, node: WhileStmt) -> None:
        self._visit(node.condition)
        self.in_loop += 1
        self._visit(node.body)
        self.in_loop -= 1

    def _visit_for_stmt(self, node: ForStmt) -> None:
        self._visit(node.iterable)
        self.in_loop += 1
        self.current_scope.define(node.target)
        self._visit(node.body)
        self.in_loop -= 1

    def _visit_do_while_stmt(self, node: DoWhileStmt) -> None:
        self.in_loop += 1
        self._visit(node.body)
        self._visit(node.condition)
        self.in_loop -= 1

    def _visit_return_stmt(self, node: ReturnStmt) -> None:
        if node.value is not None:
            self._visit(node.value)
        if self.current_function is None:
            raise SemanticError("Return outside function")
        node.type = self.current_function.return_type or "unknown"

    def _visit_break_stmt(self, node: BreakStmt) -> None:
        if self.in_loop <= 0:
            raise SemanticError("Break outside loop")

    def _visit_continue_stmt(self, node: ContinueStmt) -> None:
        if self.in_loop <= 0:
            raise SemanticError("Continue outside loop")

    def _visit_binary_op(self, node: BinaryOp) -> None:
        self._visit(node.left)
        self._visit(node.right)
        node.type = "unknown"

    def _visit_unary_op(self, node: UnaryOp) -> None:
        self._visit(node.operand)
        node.type = "unknown"

    def _visit_call_expr(self, node: CallExpr) -> None:
        self._visit(node.callee)
        for arg in node.args:
            self._visit(arg)
        node.type = "unknown"

    def _visit_new_expr(self, node: NewExpr) -> None:
        self._visit(node.callee)
        for arg in node.args:
            self._visit(arg)
        node.type = "object"

    def _visit_member_access(self, node: MemberAccess) -> None:
        self._visit(node.object)
        node.type = "unknown"

    def _visit_index_access(self, node: IndexAccess) -> None:
        self._visit(node.target)
        self._visit(node.index)
        node.type = "unknown"

    def _visit_import_stmt(self, node: ImportStmt) -> None:
        self.current_scope.define(node.module)

    def _visit_export_stmt(self, node: ExportStmt) -> None:
        self._visit(node.value)

    def _visit_try_catch(self, node: TryCatch) -> None:
        self._visit(node.try_body)
        if node.catch_body is not None:
            self._visit(node.catch_body)
        if node.finally_body is not None:
            self._visit(node.finally_body)

    def _visit_throw_stmt(self, node: ThrowStmt) -> None:
        self._visit(node.value)

    def _visit_await_expr(self, node: AwaitExpr) -> None:
        self._visit(node.value)
        node.type = "unknown"

    def _visit_array_literal(self, node: ArrayLiteral) -> None:
        for item in node.elements:
            self._visit(item)
        node.type = "list"

    def _visit_dict_literal(self, node: DictLiteral) -> None:
        for key, value in node.entries:
            self._visit(key)
            self._visit(value)
        node.type = "dict"

    def _visit_match_stmt(self, node: MatchStmt) -> None:
        self._visit(node.value)
        for pattern, body in node.cases:
            self._visit(pattern)
            self._visit(body)

    def _visit_struct_decl(self, node: StructDecl) -> None:
        self.current_scope.define(node.name, "struct")

    def _visit_lambda_expr(self, node: LambdaExpr) -> None:
        prev_scope = self.current_scope
        scope = SymbolTable(prev_scope)
        self.current_scope = scope
        for pname, _ in node.params:
            scope.define(pname)
        self._visit(node.body)
        self.current_scope = prev_scope
        node.type = "func"

    def _visit_identifier(self, node: Identifier) -> None:
        if not self.current_scope.has(node.name):
            raise SemanticError(f"Undeclared identifier: {node.name}")
        node.type = self.current_scope.get(node.name) or "unknown"


def analyze_ast(ast: Node) -> Node:
    return SemanticAnalyzer().analyze(ast)
