from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


class ParseError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"{message} at line {line}, column {column}")
        self.message = message
        self.line = line
        self.column = column


class Node:
    pass


@dataclass
class Program(Node):
    statements: List[Node]


@dataclass
class Block(Node):
    statements: List[Node]


@dataclass
class VarDecl(Node):
    name: str
    initializer: Optional[Node] = None
    type_annotation: Optional[str] = None
    is_const: bool = False


@dataclass
class Assign(Node):
    target: Node
    value: Node


@dataclass
class FuncDecl(Node):
    name: str
    params: List[Tuple[str, Optional[str]]]
    body: Block
    return_type: Optional[str] = None
    is_async: bool = False
    is_constructor: bool = False


@dataclass
class LambdaExpr(Node):
    params: List[Tuple[str, Optional[str]]]
    body: Node


@dataclass
class CallExpr(Node):
    callee: Node
    args: List[Node]


@dataclass
class ReturnStmt(Node):
    value: Optional[Node] = None


@dataclass
class ClassDecl(Node):
    name: str
    base: Optional[str]
    body: List[Node]


@dataclass
class NewExpr(Node):
    callee: Node
    args: List[Node]


@dataclass
class MemberAccess(Node):
    object: Node
    member: str


@dataclass
class IfStmt(Node):
    condition: Node
    then_body: Node
    else_body: Optional[Node] = None


@dataclass
class WhileStmt(Node):
    condition: Node
    body: Node


@dataclass
class ForStmt(Node):
    target: str
    iterable: Node
    body: Node


@dataclass
class DoWhileStmt(Node):
    body: Node
    condition: Node


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


@dataclass
class BinaryOp(Node):
    op: str
    left: Node
    right: Node


@dataclass
class UnaryOp(Node):
    op: str
    operand: Node


@dataclass
class TernaryOp(Node):
    condition: Node
    if_true: Node
    if_false: Node


@dataclass
class ArrayLiteral(Node):
    elements: List[Node]


@dataclass
class DictLiteral(Node):
    entries: List[Tuple[Node, Node]]


@dataclass
class IndexAccess(Node):
    target: Node
    index: Node


@dataclass
class ImportStmt(Node):
    module: str


@dataclass
class ExportStmt(Node):
    value: Node


@dataclass
class TryCatch(Node):
    try_body: Node
    catch_name: Optional[str] = None
    catch_type: Optional[str] = None
    catch_body: Optional[Node] = None
    finally_body: Optional[Node] = None


@dataclass
class ThrowStmt(Node):
    value: Node


@dataclass
class AwaitExpr(Node):
    value: Node


@dataclass
class MatchStmt(Node):
    value: Node
    cases: List[Tuple[Node, Node]]


@dataclass
class StructDecl(Node):
    name: str
    body: List[Node]


@dataclass
class Identifier(Node):
    name: str


@dataclass
class IntLiteral(Node):
    value: int


@dataclass
class FloatLiteral(Node):
    value: float


@dataclass
class StringLiteral(Node):
    value: str


@dataclass
class BoolLiteral(Node):
    value: bool


@dataclass
class NullLiteral(Node):
    pass


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    def parse(self) -> Program:
        statements = []
        while not self._is("EOF"):
            if self._is("SEMICOLON"):
                self._advance()
                continue
            if self._is("RBRACE"):
                break
            statements.append(self.parse_statement())
        return Program(statements)

    def parse_statement(self) -> Node:
        token = self.current()
        if self._is("KEYWORD") and token.value in {"let", "const"}:
            return self.parse_var_decl(token.value == "const")
        if self._is("KEYWORD") and token.value == "func":
            return self.parse_func_decl()
        if self._is("IDENTIFIER") and token.value == "constructor":
            return self.parse_constructor_decl()
        if self._is("KEYWORD") and token.value == "async":
            self._advance()
            if not self._is("KEYWORD") or self.current().value != "func":
                raise self.error("Expected function after async")
            func = self.parse_func_decl(is_async=True)
            return func
        if self._is("KEYWORD") and token.value == "class":
            return self.parse_class_decl()
        if self._is("KEYWORD") and token.value == "import":
            return self.parse_import_stmt()
        if self._is("KEYWORD") and token.value == "export":
            return self.parse_export_stmt()
        if self._is("KEYWORD") and token.value == "if":
            return self.parse_if_stmt()
        if self._is("KEYWORD") and token.value == "while":
            return self.parse_while_stmt()
        if self._is("KEYWORD") and token.value == "for":
            return self.parse_for_stmt()
        if self._is("KEYWORD") and token.value == "do":
            return self.parse_do_while_stmt()
        if self._is("KEYWORD") and token.value == "return":
            return self.parse_return_stmt()
        if self._is("KEYWORD") and token.value == "break":
            self._advance()
            return BreakStmt()
        if self._is("KEYWORD") and token.value == "continue":
            self._advance()
            return ContinueStmt()
        if self._is("KEYWORD") and token.value == "try":
            return self.parse_try_catch()
        if self._is("KEYWORD") and token.value == "throw":
            self._advance()
            return ThrowStmt(self.parse_expression())
        if self._is("KEYWORD") and token.value == "struct":
            return self.parse_struct_decl()
        if self._is("KEYWORD") and token.value == "match":
            return self.parse_match_stmt()
        if self._peek_value("LBRACE"):
            return self.parse_block()
        expr = self.parse_expression()
        if self._peek_value("SEMICOLON"):
            self._advance()
        return expr

    def parse_block(self) -> Block:
        self.expect("LBRACE", "Expected '{'")
        statements = []
        while not self._is("EOF") and not self._peek_value("RBRACE"):
            if self._peek_value("SEMICOLON"):
                self._advance()
                continue
            statements.append(self.parse_statement())
        self.expect("RBRACE", "Expected '}'")
        return Block(statements)

    def parse_var_decl(self, is_const: bool) -> Node:
        self._advance()
        name = self.expect_value("IDENTIFIER", "Expected identifier")
        type_annotation = None
        if self._peek_value("COLON"):
            self._advance()
            type_annotation = self.expect_identifier_or_type()
        initializer = None
        if self._peek_value("ASSIGN"):
            self._advance()
            initializer = self.parse_expression()
        if self._peek_value("SEMICOLON"):
            self._advance()
        return VarDecl(name, initializer, type_annotation, is_const)

    def parse_func_decl(self, is_async: bool = False) -> FuncDecl:
        self._advance()
        name = self.expect_value("IDENTIFIER", "Expected function name")
        params = []
        self.expect("LPAREN", "Expected '('")
        if not self._peek_value("RPAREN"):
            while True:
                param_name = self.expect_value("IDENTIFIER", "Expected parameter name")
                type_annotation = None
                if self._peek_value("COLON"):
                    self._advance()
                    type_annotation = self.expect_identifier_or_type()
                params.append((param_name, type_annotation))
                if self._peek_value("COMMA"):
                    self._advance()
                    continue
                break
        self.expect("RPAREN", "Expected ')'" )

        return_type = None
        if self._peek_value("ARROW"):
            self._advance()
            return_type = self.expect_identifier_or_type()
        body = self.parse_block()
        return FuncDecl(name, params, body, return_type, is_async, name == "constructor")

    def parse_constructor_decl(self) -> FuncDecl:
        self._advance()
        params = []
        self.expect("LPAREN", "Expected '('")
        if not self._peek_value("RPAREN"):
            while True:
                param_name = self.expect_value("IDENTIFIER", "Expected parameter name")
                type_annotation = None
                if self._peek_value("COLON"):
                    self._advance()
                    type_annotation = self.expect_identifier_or_type()
                params.append((param_name, type_annotation))
                if self._peek_value("COMMA"):
                    self._advance()
                    continue
                break
        self.expect("RPAREN", "Expected ')'" )
        body = self.parse_block()
        return FuncDecl("constructor", params, body, None, False, True)

    def parse_class_decl(self) -> ClassDecl:
        self._advance()
        name = self.expect_value("IDENTIFIER", "Expected class name")
        base = None
        if self._peek_value("KEYWORD") and self.current().value == "extends":
            self._advance()
            base = self.expect_identifier_or_type()
        body = self.parse_block().statements
        return ClassDecl(name, base, body)

    def parse_import_stmt(self) -> ImportStmt:
        self._advance()
        module = self.expect_identifier_or_type()
        if self._peek_value("SEMICOLON"):
            self._advance()
        return ImportStmt(module)

    def parse_export_stmt(self) -> ExportStmt:
        self._advance()
        return ExportStmt(self.parse_expression())

    def parse_if_stmt(self) -> IfStmt:
        self._advance()
        condition = self.parse_expression()
        then_body = self.parse_statement()
        else_body = None
        if self._peek_value("KEYWORD") and self.current().value == "else":
            self._advance()
            else_body = self.parse_statement()
        return IfStmt(condition, then_body, else_body)

    def parse_while_stmt(self) -> WhileStmt:
        self._advance()
        condition = self.parse_expression()
        body = self.parse_statement()
        return WhileStmt(condition, body)

    def parse_for_stmt(self) -> ForStmt:
        self._advance()
        target = self.expect_value("IDENTIFIER", "Expected loop variable")
        self._advance()
        self.expect("KEYWORD", "Expected 'in'")
        self._advance()
        iterable = self.parse_expression()
        body = self.parse_statement()
        return ForStmt(target, iterable, body)

    def parse_do_while_stmt(self) -> DoWhileStmt:
        self._advance()
        body = self.parse_statement()
        self.expect("KEYWORD", "Expected 'while'")
        self._advance()
        condition = self.parse_expression()
        if self._peek_value("SEMICOLON"):
            self._advance()
        return DoWhileStmt(body, condition)

    def parse_return_stmt(self) -> ReturnStmt:
        self._advance()
        value = None
        if not self._peek_value("SEMICOLON") and not self._peek_value("RBRACE") and not self._is("EOF"):
            value = self.parse_expression()
        if self._peek_value("SEMICOLON"):
            self._advance()
        return ReturnStmt(value)

    def parse_try_catch(self) -> TryCatch:
        self._advance()
        try_body = self.parse_statement()
        catch_name = None
        catch_type = None
        catch_body = None
        finally_body = None
        if self._peek_value("KEYWORD") and self.current().value == "catch":
            self._advance()
            self.expect("LPAREN", "Expected '(' after catch")
            self._advance()
            if self._peek_value("IDENTIFIER"):
                catch_name = self.current().value
                self._advance()
                if self._peek_value("COLON"):
                    self._advance()
                    catch_type = self.expect_identifier_or_type()
            self.expect("RPAREN", "Expected ')' after catch parameter")
            self._advance()
            catch_body = self.parse_statement()
        if self._peek_value("KEYWORD") and self.current().value == "finally":
            self._advance()
            finally_body = self.parse_statement()
        return TryCatch(try_body, catch_name, catch_type, catch_body, finally_body)

    def parse_struct_decl(self) -> StructDecl:
        self._advance()
        name = self.expect_value("IDENTIFIER", "Expected struct name")
        self._advance()
        body = self.parse_block().statements
        return StructDecl(name, body)

    def parse_match_stmt(self) -> MatchStmt:
        self._advance()
        value = self.parse_expression()
        cases = []
        self.expect("LBRACE", "Expected '{' after match")
        self._advance()
        while not self._peek_value("RBRACE"):
            if self._peek_value("SEMICOLON"):
                self._advance()
                continue
            pattern = self.parse_expression()
            self.expect("ARROW", "Expected '=>' in match case")
            self._advance()
            body = self.parse_expression()
            cases.append((pattern, body))
        self.expect("RBRACE", "Expected '}'")
        self._advance()
        return MatchStmt(value, cases)

    def parse_expression(self) -> Node:
        return self.parse_assignment()

    def parse_assignment(self) -> Node:
        expr = self.parse_ternary()
        if self._peek_value("ASSIGN"):
            self._advance()
            value = self.parse_assignment()
            return Assign(expr, value)
        return expr

    def parse_ternary(self) -> Node:
        expr = self.parse_or()
        if self._peek_value("QUESTION"):
            self._advance()
            if_true = self.parse_expression()
            self.expect("COLON", "Expected ':' in ternary")
            self._advance()
            if_false = self.parse_expression()
            return TernaryOp(expr, if_true, if_false)
        return expr

    def parse_or(self) -> Node:
        expr = self.parse_and()
        while self._peek_value("OR") or (self._peek_value("KEYWORD") and self.current().value == "or"):
            op = self.current().type
            self._advance()
            right = self.parse_and()
            expr = BinaryOp("or" if op == "OR" else "or", expr, right)
        return expr

    def parse_and(self) -> Node:
        expr = self.parse_equality()
        while self._peek_value("AND") or (self._peek_value("KEYWORD") and self.current().value == "and"):
            op = self.current().type
            self._advance()
            right = self.parse_equality()
            expr = BinaryOp("and" if op == "AND" else "and", expr, right)
        return expr

    def parse_equality(self) -> Node:
        expr = self.parse_comparison()
        while self._peek_value("EQ") or self._peek_value("NEQ"):
            op = self.current().type
            self._advance()
            right = self.parse_comparison()
            expr = BinaryOp("==" if op == "EQ" else "!=", expr, right)
        return expr

    def parse_comparison(self) -> Node:
        expr = self.parse_additive()
        while self._peek_value("LT") or self._peek_value("GT") or self._peek_value("LEQ") or self._peek_value("GEQ"):
            op = self.current().type
            self._advance()
            right = self.parse_additive()
            expr = BinaryOp({"LT": "<", "GT": ">", "LEQ": "<=", "GEQ": ">="}[op], expr, right)
        return expr

    def parse_additive(self) -> Node:
        expr = self.parse_multiplicative()
        while self._peek_value("PLUS") or self._peek_value("MINUS"):
            op = self.current().type
            self._advance()
            right = self.parse_multiplicative()
            expr = BinaryOp("+" if op == "PLUS" else "-", expr, right)
        return expr

    def parse_multiplicative(self) -> Node:
        expr = self.parse_unary()
        while self._peek_value("STAR") or self._peek_value("SLASH") or self._peek_value("PERCENT"):
            op = self.current().type
            self._advance()
            right = self.parse_unary()
            expr = BinaryOp("*" if op == "STAR" else "/" if op == "SLASH" else "%", expr, right)
        return expr

    def parse_unary(self) -> Node:
        if self._peek_value("NOT") or self._peek_value("MINUS") or self._peek_value("PLUS"):
            op = self.current().type
            self._advance()
            operand = self.parse_unary()
            return UnaryOp("not" if op == "NOT" else "-" if op == "MINUS" else "+", operand)
        return self.parse_power()

    def parse_power(self) -> Node:
        expr = self.parse_postfix()
        if self._peek_value("POWER"):
            self._advance()
            right = self.parse_unary()
            expr = BinaryOp("**", expr, right)
        return expr

    def parse_postfix(self) -> Node:
        expr = self.parse_primary()
        while True:
            if self._peek_value("LPAREN"):
                self._advance()
                args = []
                if not self._peek_value("RPAREN"):
                    while True:
                        args.append(self.parse_expression())
                        if self._peek_value("COMMA"):
                            self._advance()
                            continue
                        break
                self.expect("RPAREN", "Expected ')' after argument list")
                self._advance()
                expr = CallExpr(expr, args)
            elif self._peek_value("LBRACKET"):
                self._advance()
                index = self.parse_expression()
                self.expect("RBRACKET", "Expected ']'")
                self._advance()
                expr = IndexAccess(expr, index)
            elif self._peek_value("DOT"):
                self._advance()
                member = self.expect_value("IDENTIFIER", "Expected member name")
                self._advance()
                expr = MemberAccess(expr, member)
            else:
                break
        return expr

    def parse_primary(self) -> Node:
        token = self.current()
        if self._is("INT"):
            self._advance()
            return IntLiteral(int(token.value))
        if self._is("FLOAT"):
            self._advance()
            return FloatLiteral(float(token.value))
        if self._is("STRING"):
            self._advance()
            return StringLiteral(token.value)
        if self._is("BOOL"):
            self._advance()
            return BoolLiteral(bool(token.value))
        if self._is("KEYWORD") and token.value == "null":
            self._advance()
            return NullLiteral()
        if self._peek_value("IDENTIFIER") and self._peek_next_value("FAT_ARROW"):
            name = self.current().value
            self._advance()
            self._advance()
            body = self.parse_expression()
            return LambdaExpr([(name, None)], body)
        if self._peek_value("LPAREN"):
            self._advance()
            if self._peek_value("RPAREN"):
                self._advance()
                return LambdaExpr([], Block([]))
            if self._peek_value("IDENTIFIER") or self._peek_value("KEYWORD"):
                if self._peek_next_value("COMMA") or self._peek_next_value("RPAREN") or self._peek_next_value("COLON"):
                    params = []
                    while True:
                        name = self.expect_value("IDENTIFIER", "Expected parameter name")
                        self._advance()
                        type_annotation = None
                        if self._peek_value("COLON"):
                            self._advance()
                            type_annotation = self.expect_identifier_or_type()
                        params.append((name, type_annotation))
                        if self._peek_value("COMMA"):
                            self._advance()
                            continue
                        break
                    self.expect("RPAREN", "Expected ')' in lambda parameters")
                    self._advance()
                    self.expect("FAT_ARROW", "Expected '=>' in lambda")
                    self._advance()
                    body = self.parse_expression()
                    return LambdaExpr(params, body)
            expr = self.parse_expression()
            self.expect("RPAREN", "Expected ')' after expression")
            self._advance()
            return expr
        if self._peek_value("LBRACKET"):
            self._advance()
            elements = []
            if not self._peek_value("RBRACKET"):
                while True:
                    elements.append(self.parse_expression())
                    if self._peek_value("COMMA"):
                        self._advance()
                        continue
                    break
            self.expect("RBRACKET", "Expected ']' for array literal")
            self._advance()
            return ArrayLiteral(elements)
        if self._peek_value("LBRACE"):
            self._advance()
            entries = []
            while not self._peek_value("RBRACE"):
                key = self.parse_expression()
                self.expect("COLON", "Expected ':' in dictionary literal")
                self._advance()
                value = self.parse_expression()
                entries.append((key, value))
                if self._peek_value("COMMA"):
                    self._advance()
                    continue
                break
            self.expect("RBRACE", "Expected '}' for dictionary literal")
            self._advance()
            return DictLiteral(entries)
        if self._peek_value("IDENTIFIER"):
            name = self.current().value
            self._advance()
            if name == "await":
                return AwaitExpr(self.parse_primary())
            if name == "new":
                callee = self.parse_primary()
                args = []
                if self._peek_value("LPAREN"):
                    self._advance()
                    if not self._peek_value("RPAREN"):
                        while True:
                            args.append(self.parse_expression())
                            if self._peek_value("COMMA"):
                                self._advance()
                                continue
                            break
                    self.expect("RPAREN", "Expected ')' after constructor arguments")
                    self._advance()
                return NewExpr(callee, args)
            return Identifier(name)
        raise self.error("Unexpected token in expression")

    def expect(self, token_type: str, message: str) -> None:
        if not self._peek_value(token_type):
            raise self.error(message)
        self._advance()

    def expect_value(self, token_type: str, message: str) -> str:
        if not self._peek_value(token_type):
            raise self.error(message)
        token = self.current()
        self._advance()
        return token.value

    def expect_identifier_or_type(self) -> str:
        if self._peek_value("IDENTIFIER"):
            value = self.current().value
            self._advance()
            return value
        if self._peek_value("KEYWORD"):
            value = self.current().value
            self._advance()
            return value
        if self._is("STRING"):
            value = self.current().value
            self._advance()
            return value
        raise self.error("Expected identifier or type")

    def current(self):
        return self.tokens[self.index]

    def _advance(self) -> None:
        self.index += 1

    def _peek_value(self, token_type: str) -> bool:
        return self.current().type == token_type

    def _is(self, token_type: str) -> bool:
        return self.current().type == token_type

    def _peek_next_value(self, token_type: str) -> bool:
        return self.tokens[self.index + 1].type == token_type if self.index + 1 < len(self.tokens) else False

    def error(self, message: str) -> ParseError:
        token = self.current()
        return ParseError(message, token.line, token.column)


def parse_tokens(tokens):
    return Parser(tokens).parse()
