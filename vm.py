from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from codegen import Instruction
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


class VMError(Exception):
    def __init__(self, message: str, line: int = 0):
        super().__init__(f"{message}" if line == 0 else f"{message} at line {line}")
        self.message = message
        self.line = line


@dataclass
class Frame:
    locals: Dict[str, Any] = field(default_factory=dict)
    return_value: Any = None


class VirtualMachine:
    def __init__(self):
        self.globals: Dict[str, Any] = self._builtin_globals()
        self._module_cache: Dict[str, Any] = {}

    def run(self, instructions: List[Instruction], ast: Optional[Node] = None) -> Any:
        if ast is not None:
            return self._execute_ast(ast, self.globals)
        return None

    def _execute_ast(self, node: Node, env: Dict[str, Any]) -> Any:
        if isinstance(node, Program):
            result = None
            for stmt in node.statements:
                result = self._execute_ast(stmt, env)
            return result
        if isinstance(node, Block):
            result = None
            for stmt in node.statements:
                result = self._execute_ast(stmt, env)
            return result
        if isinstance(node, VarDecl):
            value = None if node.initializer is None else self._execute_ast(node.initializer, env)
            env[node.name] = value
            return value
        if isinstance(node, Assign):
            value = self._execute_ast(node.value, env)
            if isinstance(node.target, Identifier):
                env[node.target.name] = value
            elif isinstance(node.target, MemberAccess):
                target_obj = self._execute_ast(node.target.object, env)
                setattr(target_obj, node.target.member, value)
            else:
                raise VMError("Unsupported assignment target")
            return value
        if isinstance(node, FuncDecl):
            def _func(*args, **kwargs):
                local_env = dict(env)
                if node.params:
                    for (name, _), arg in zip(node.params, args):
                        local_env[name] = arg
                local_env["__return__"] = None
                try:
                    result = self._execute_ast(node.body, local_env)
                except ReturnSignal as signal:
                    result = signal.value
                return result
            env[node.name] = _func
            return _func
        if isinstance(node, ClassDecl):
            base = object
            if node.base:
                base = env.get(node.base, object)
            methods = {}
            for stmt in node.body:
                if isinstance(stmt, FuncDecl):
                    if stmt.name == "constructor":
                        methods["__init__"] = self._make_method(stmt, env, node.name, base)
                    else:
                        methods[stmt.name] = self._make_method(stmt, env, node.name, base)
            cls = type(node.name, (base,), methods)
            env[node.name] = cls
            return cls
        if isinstance(node, IfStmt):
            cond = self._execute_ast(node.condition, env)
            if cond:
                return self._execute_ast(node.then_body, env)
            if node.else_body is not None:
                return self._execute_ast(node.else_body, env)
            return None
        if isinstance(node, WhileStmt):
            result = None
            while self._execute_ast(node.condition, env):
                result = self._execute_ast(node.body, env)
            return result
        if isinstance(node, ForStmt):
            iterable = self._execute_ast(node.iterable, env)
            result = None
            for item in iterable:
                local_env = dict(env)
                local_env[node.target] = item
                result = self._execute_ast(node.body, local_env)
            return result
        if isinstance(node, DoWhileStmt):
            result = None
            while True:
                result = self._execute_ast(node.body, env)
                if not self._execute_ast(node.condition, env):
                    break
            return result
        if isinstance(node, ReturnStmt):
            raise ReturnSignal(node.value and self._execute_ast(node.value, env))
        if isinstance(node, BreakStmt):
            raise BreakSignal()
        if isinstance(node, ContinueStmt):
            raise ContinueSignal()
        if isinstance(node, BinaryOp):
            left = self._execute_ast(node.left, env)
            right = self._execute_ast(node.right, env)
            if node.op == "+":
                return left + right
            if node.op == "-":
                return left - right
            if node.op == "*":
                return left * right
            if node.op == "/":
                return left / right
            if node.op == "%":
                return left % right
            if node.op == "**":
                return left ** right
            if node.op == "==":
                return left == right
            if node.op == "!=":
                return left != right
            if node.op == "<":
                return left < right
            if node.op == ">":
                return left > right
            if node.op == "<=":
                return left <= right
            if node.op == ">=":
                return left >= right
            if node.op == "and":
                return bool(left and right)
            if node.op == "or":
                return bool(left or right)
            raise VMError(f"Unsupported operator {node.op}")
        if isinstance(node, UnaryOp):
            operand = self._execute_ast(node.operand, env)
            if node.op == "not":
                return not operand
            if node.op == "-":
                return -operand
            if node.op == "+":
                return +operand
            raise VMError(f"Unsupported unary operator {node.op}")
        if isinstance(node, CallExpr):
            callee = self._execute_ast(node.callee, env)
            args = [self._execute_ast(arg, env) for arg in node.args]
            if isinstance(callee, type) and issubclass(callee, Exception):
                return callee(*args)
            if callable(callee):
                return callee(*args)
            raise VMError("Attempted to call a non-callable value")
        if isinstance(node, NewExpr):
            cls = self._execute_ast(node.callee, env)
            args = [self._execute_ast(arg, env) for arg in node.args]
            return cls(*args)
        if isinstance(node, MemberAccess):
            obj = self._execute_ast(node.object, env)
            if isinstance(obj, dict):
                return obj.get(node.member)
            if hasattr(obj, node.member):
                return getattr(obj, node.member)
            if node.member == "filter" and isinstance(obj, list):
                return lambda func: [item for item in obj if func(item)]
            if node.member == "map" and isinstance(obj, list):
                return lambda func: [func(item) for item in obj]
            if node.member == "reduce" and isinstance(obj, list):
                return lambda func, initial: self._reduce_list(obj, func, initial)
            return None
        if isinstance(node, IndexAccess):
            target = self._execute_ast(node.target, env)
            index = self._execute_ast(node.index, env)
            return target[index]
        if isinstance(node, ImportStmt):
            return self._import_module(node.module, env)
        if isinstance(node, ExportStmt):
            return self._execute_ast(node.value, env)
        if isinstance(node, TryCatch):
            try:
                return self._execute_ast(node.try_body, env)
            except Exception as exc:
                if node.catch_body is not None and node.catch_name is not None:
                    catch_env = dict(env)
                    catch_env[node.catch_name] = exc
                    return self._execute_ast(node.catch_body, catch_env)
                raise
        if isinstance(node, ThrowStmt):
            raise self._execute_ast(node.value, env)
        if isinstance(node, AwaitExpr):
            return self._execute_ast(node.value, env)
        if isinstance(node, ArrayLiteral):
            return [self._execute_ast(item, env) for item in node.elements]
        if isinstance(node, DictLiteral):
            return {self._execute_ast(k, env): self._execute_ast(v, env) for k, v in node.entries}
        if isinstance(node, MatchStmt):
            return self._execute_ast(node.cases[0][1], env) if node.cases else None
        if isinstance(node, StructDecl):
            env[node.name] = type(node.name, (), {})
            return env[node.name]
        if isinstance(node, Identifier):
            if node.name in env:
                return env[node.name]
            if node.name in self.globals:
                return self.globals[node.name]
            if node.name == "self":
                return env.get("self")
            if node.name == "super":
                return SuperMarker()
            raise VMError(f"Unknown identifier {node.name}")
        if isinstance(node, IntLiteral):
            return node.value
        if isinstance(node, FloatLiteral):
            return node.value
        if isinstance(node, StringLiteral):
            return node.value
        if isinstance(node, BoolLiteral):
            return node.value
        if isinstance(node, NullLiteral):
            return None
        if isinstance(node, LambdaExpr):
            def _lambda(*args):
                local_env = dict(env)
                if node.params:
                    for (name, _), arg in zip(node.params, args):
                        local_env[name] = arg
                return self._execute_ast(node.body, local_env)
            return _lambda
        raise VMError("Unsupported AST node")

    def _make_method(self, func_decl: FuncDecl, env: Dict[str, Any], class_name: str, base: type):
        def _method(self_obj, *args):
            local_env = dict(env)
            local_env["self"] = self_obj
            local_env["super"] = SuperMarker(base)
            if func_decl.params:
                for (name, _), arg in zip(func_decl.params, args):
                    local_env[name] = arg
            try:
                return self._execute_ast(func_decl.body, local_env)
            except ReturnSignal as signal:
                return signal.value
        return _method

    def _reduce_list(self, values: List[Any], func, initial: Any) -> Any:
        result = initial
        for item in values:
            result = func(result, item)
        return result

    def _import_module(self, module_name: str, env: Dict[str, Any]) -> Any:
        if module_name in self._module_cache:
            return self._module_cache[module_name]
        module_path = os.path.join(os.getcwd(), "stdlib", f"{module_name}.hk")
        if not os.path.exists(module_path):
            raise VMError(f"Cannot import module {module_name}")
        from compiler import compile_source

        with open(module_path, "r", encoding="utf-8") as handle:
            source = handle.read()
        result = compile_source(source, file_name=module_path)
        module_env = {}
        self._execute_ast(result["ast"], module_env)
        module_obj = type(module_name, (), module_env)
        self._module_cache[module_name] = module_obj
        env[module_name] = module_obj
        self.globals[module_name] = module_obj
        return module_obj

    def _builtin_globals(self) -> Dict[str, Any]:
        return {
            "print": print,
            "input": input,
            "len": len,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,
            "list": list,
            "dict": dict,
            "set": set,
            "open": open,
            "math": type("MathModule", (), {"sqrt": staticmethod(math.sqrt), "floor": staticmethod(math.floor), "ceil": staticmethod(math.ceil), "pow": staticmethod(math.pow), "abs": staticmethod(abs)}),
            "Error": type("Error", (Exception,), {"__init__": lambda self, message="": setattr(self, "message", message)}),
        }


class ReturnSignal(Exception):
    def __init__(self, value: Any):
        super().__init__()
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class SuperMarker:
    def __init__(self, base: type):
        self.base = base

    def __call__(self, *args):
        return self.base(*args)


def run_bytecode(instructions: List[Instruction]) -> Any:
    return VirtualMachine().run(instructions)
