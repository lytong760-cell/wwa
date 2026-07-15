from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

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


@dataclass
class Instruction:
    opcode: str
    operand: Optional[object] = None
    line_number: int = 0


class CodeGen:
    def __init__(self):
        self.instructions: List[Instruction] = []

    def generate(self, node: Node) -> List[Instruction]:
        self._visit(node)
        self.instructions.append(Instruction("HALT", None, 0))
        return self.instructions

    def _visit(self, node: Node) -> None:
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
            self._emit("LOAD_CONST", node.value, node.line if hasattr(node, "line") else 0)
        elif isinstance(node, FloatLiteral):
            self._emit("LOAD_CONST", node.value, node.line if hasattr(node, "line") else 0)
        elif isinstance(node, StringLiteral):
            self._emit("LOAD_CONST", node.value, node.line if hasattr(node, "line") else 0)
        elif isinstance(node, BoolLiteral):
            self._emit("LOAD_CONST", node.value, node.line if hasattr(node, "line") else 0)
        elif isinstance(node, NullLiteral):
            self._emit("LOAD_CONST", None, node.line if hasattr(node, "line") else 0)
        elif isinstance(node, LambdaExpr):
            self._visit_lambda_expr(node)

    def _visit_program(self, node: Program) -> None:
        for stmt in node.statements:
            self._visit(stmt)

    def _visit_block(self, node: Block) -> None:
        for stmt in node.statements:
            self._visit(stmt)

    def _visit_var_decl(self, node: VarDecl) -> None:
        if node.initializer is not None:
            self._visit(node.initializer)
        self._emit("STORE_VAR", node.name, 0)

    def _visit_assign(self, node: Assign) -> None:
        self._visit(node.value)
        self._emit("STORE_VAR", node.target.name if isinstance(node.target, Identifier) else "", 0)

    def _visit_func_decl(self, node: FuncDecl) -> None:
        self._emit("MAKE_FUNC", node.name, 0)

    def _visit_class_decl(self, node: ClassDecl) -> None:
        self._emit("LOAD_CONST", node.name, 0)

    def _visit_if_stmt(self, node: IfStmt) -> None:
        self._visit(node.condition)
        false_jump = self._emit("JUMP_IF_FALSE", None, 0)
        self._visit(node.then_body)
        end_jump = self._emit("JUMP", None, 0)
        self._patch_jump(false_jump)
        if node.else_body is not None:
            self._visit(node.else_body)
        self._patch_jump(end_jump)

    def _visit_while_stmt(self, node: WhileStmt) -> None:
        loop_start = len(self.instructions)
        self._visit(node.condition)
        false_jump = self._emit("JUMP_IF_FALSE", None, 0)
        self._visit(node.body)
        self._emit("JUMP", loop_start, 0)
        self._patch_jump(false_jump)

    def _visit_for_stmt(self, node: ForStmt) -> None:
        self._visit(node.iterable)
        self._emit("STORE_VAR", node.target, 0)
        self._visit(node.body)

    def _visit_do_while_stmt(self, node: DoWhileStmt) -> None:
        self._visit(node.body)
        self._visit(node.condition)
        self._emit("JUMP_IF_TRUE", len(self.instructions), 0)

    def _visit_return_stmt(self, node: ReturnStmt) -> None:
        if node.value is not None:
            self._visit(node.value)
        self._emit("RETURN", None, 0)

    def _visit_break_stmt(self, node: BreakStmt) -> None:
        self._emit("JUMP", None, 0)

    def _visit_continue_stmt(self, node: ContinueStmt) -> None:
        self._emit("JUMP", None, 0)

    def _visit_binary_op(self, node: BinaryOp) -> None:
        self._visit(node.left)
        self._visit(node.right)
        self._emit({"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "MOD", "**": "POW", "==": "EQ", "!=": "NEQ", "<": "LT", ">": "GT", "<=": "LEQ", ">=": "GEQ", "and": "AND", "or": "OR"}[node.op], None, 0)

    def _visit_unary_op(self, node: UnaryOp) -> None:
        self._visit(node.operand)
        self._emit({"not": "NOT", "-": "NEG", "+": "POS"}[node.op], None, 0)

    def _visit_call_expr(self, node: CallExpr) -> None:
        for arg in node.args:
            self._visit(arg)
        self._visit(node.callee)
        self._emit("CALL", len(node.args), 0)

    def _visit_new_expr(self, node: NewExpr) -> None:
        for arg in node.args:
            self._visit(arg)
        self._emit("NEW_OBJECT", node.callee.name if isinstance(node.callee, Identifier) else None, 0)

    def _visit_member_access(self, node: MemberAccess) -> None:
        self._visit(node.object)
        self._emit("LOAD_ATTR", node.member, 0)

    def _visit_index_access(self, node: IndexAccess) -> None:
        self._visit(node.target)
        self._visit(node.index)
        self._emit("INDEX_GET", None, 0)

    def _visit_import_stmt(self, node: ImportStmt) -> None:
        self._emit("IMPORT", node.module, 0)

    def _visit_export_stmt(self, node: ExportStmt) -> None:
        self._visit(node.value)

    def _visit_try_catch(self, node: TryCatch) -> None:
        self._emit("PUSH_TRY", None, 0)
        self._visit(node.try_body)
        self._emit("POP_TRY", None, 0)

    def _visit_throw_stmt(self, node: ThrowStmt) -> None:
        self._visit(node.value)
        self._emit("THROW", None, 0)

    def _visit_await_expr(self, node: AwaitExpr) -> None:
        self._visit(node.value)
        self._emit("AWAIT", None, 0)

    def _visit_array_literal(self, node: ArrayLiteral) -> None:
        for item in node.elements:
            self._visit(item)
        self._emit("BUILD_LIST", len(node.elements), 0)

    def _visit_dict_literal(self, node: DictLiteral) -> None:
        for key, value in node.entries:
            self._visit(key)
            self._visit(value)
        self._emit("BUILD_DICT", len(node.entries), 0)

    def _visit_match_stmt(self, node: MatchStmt) -> None:
        self._visit(node.value)
        self._emit("MATCH", None, 0)

    def _visit_struct_decl(self, node: StructDecl) -> None:
        self._emit("LOAD_CONST", node.name, 0)

    def _visit_identifier(self, node: Identifier) -> None:
        self._emit("LOAD_VAR", node.name, 0)

    def _emit(self, opcode: str, operand: Optional[object], line_number: int) -> int:
        self.instructions.append(Instruction(opcode, operand, line_number))
        return len(self.instructions) - 1

    def _patch_jump(self, index: int) -> None:
        self.instructions[index].operand = len(self.instructions)


def generate_bytecode(ast: Node) -> List[Instruction]:
    return CodeGen().generate(ast)
