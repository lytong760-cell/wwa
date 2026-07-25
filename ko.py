from __future__ import annotations

import argparse
import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class KoError(Exception):
    pass


@dataclass
class KoFunction:
    name: str
    params: List[str]
    body: str


@dataclass
class KoClass:
    name: str
    methods: Dict[str, KoFunction] = field(default_factory=dict)
    fields: Dict[str, Any] = field(default_factory=dict)

    def instantiate(self, interp: "KoInterpreter") -> "KoInstance":
        return KoInstance(self, interp)


@dataclass
class KoInstance:
    klass: KoClass
    interp: "KoInterpreter"
    values: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.values.update(self.klass.fields)

    def call(self, method: str, args: List[Any]) -> Any:
        if method not in self.klass.methods:
            raise KoError(f"Unknown method {self.klass.name}.{method}")
        return self.interp._call_function(self.klass.methods[method], args, self.values)


class KoInterpreter:
    """Pragmatic interpreter for the .ko 1.3 syntax documented in Hanaka_spec.md."""

    PRIMITIVES = {"int": int, "freal": float, "string": str, "booling": bool, "byte": bytes}

    def __init__(self, input_func: Callable[[str], str] = input, output_func: Callable[..., None] = print):
        self.env: Dict[str, Any] = {"random": random.randint, "True": True, "False": False}
        self.functions: Dict[str, KoFunction] = {}
        self.classes: Dict[str, KoClass] = {}
        self.input = input_func
        self.output = output_func

    def run(self, source: str) -> Any:
        clean = self._strip_comments(source)
        clean = re.sub(r"\\(True|False)\\", r"\1", clean)
        self._load_imports(clean)
        clean = re.sub(r"\*\*Import\*\*\([^\n]+", "", clean)
        clean = self._load_classes(clean)
        clean = self._load_functions(clean)
        mains = self._extract_main_blocks(clean)
        if not mains:
            raise KoError(".ko program requires a main [ ] block")
        result = None
        for main in mains:
            result = self._exec_block(main, self.env)
        return result

    def _strip_comments(self, source: str) -> str:
        return re.sub(r"\|.*?\|", "", source, flags=re.S)

    def _load_imports(self, source: str) -> None:
        for mod, alias in re.findall(r"\*\*Import\*\*\(\$(\w+)\)@also%\*(\w+)!`global`:\w+", source):
            if mod == "Random":
                self.env[alias] = random.randint
            else:
                self.env[alias] = object()

    def _load_functions(self, source: str) -> str:
        pattern = re.compile(r"(^|\n)\s*(\w+)\(([^)]*)\)\s*\[", re.M)
        while True:
            m = pattern.search(source)
            if not m:
                return source
            start = m.start(0) + len(m.group(1))
            body_start = m.end() - 1
            end = self._matching(source, body_start, "[", "]")
            name = m.group(2)
            params = [p.strip().split("*")[-1] for p in m.group(3).split(",") if p.strip()]
            self.functions[name] = KoFunction(name, params, source[body_start + 1:end])
            source = source[:start] + source[end + 1:]

    def _load_classes(self, source: str) -> str:
        pattern = re.compile(r"(\w+)\s+!class\s*\[")
        while True:
            m = pattern.search(source)
            if not m:
                return source
            body_start = m.end() - 1
            end = self._matching(source, body_start, "[", "]")
            body = source[body_start + 1:end]
            klass = KoClass(m.group(1))
            body = re.sub(r"@private\s*\[(.*)\]", lambda x: x.group(1), body, flags=re.S)
            body = self._extract_class_members(body, klass)
            self.classes[klass.name] = klass
            source = source[:m.start()] + source[end + 1:]

    def _extract_class_members(self, body: str, klass: KoClass) -> str:
        kept = []
        for stmt in self._statements(body):
            if re.match(r"^(int|freal|string|booling|byte)\(", stmt.strip()):
                self._load_typed_decls(stmt, klass.fields, remove=True)
            elif re.match(r"^\(.*\)\*\w+$", stmt.strip(), re.S):
                self._load_data_decls(stmt, klass.fields, remove=True)
            else:
                kept.append(stmt)
        body = "\n".join(kept)
        pattern = re.compile(r"(\w+)\(([^)]*)\)\s*\[")
        while True:
            m = pattern.search(body)
            if not m:
                return body
            end = self._matching(body, m.end() - 1, "[", "]")
            params = [p.strip().split("*")[-1] for p in m.group(2).split(",") if p.strip()]
            klass.methods[m.group(1)] = KoFunction(m.group(1), params, body[m.end():end])
            body = body[:m.start()] + body[end + 1:]

    def _extract_main_blocks(self, source: str) -> List[str]:
        blocks = []
        i = 0
        while i < len(source):
            if source[i] == "[":
                end = self._matching(source, i, "[", "]")
                blocks.append(source[i + 1:end])
                i = end
            i += 1
        return blocks

    def _exec_block(self, body: str, env: Dict[str, Any]) -> Any:
        result = None
        stmts = self._statements(body)
        i = 0
        while i < len(stmts):
            stmt = stmts[i].strip()
            if not stmt:
                i += 1; continue
            if re.match(r"^(int|freal|string|booling|byte)\(", stmt):
                self._load_typed_decls(stmt, env); i += 1; continue
            if re.match(r"^\(.*\)\*\w+$", stmt, re.S):
                self._load_data_decls(stmt, env); i += 1; continue
            if stmt.startswith("<if>") or stmt.startswith("<if<else>>"):
                chain = [stmt]
                i += 1
                while i < len(stmts) and stmts[i].strip().startswith(("<elif>", "<else>")):
                    chain.append(stmts[i].strip()); i += 1
                result = self._exec_if_chain(chain, env)
                continue
            result = self._exec_stmt(stmt, env)
            i += 1
        return result

    def _exec_stmt(self, stmt: str, env: Dict[str, Any]) -> Any:
        if stmt.startswith("<printf>") or stmt.startswith("<print>"):
            val = self._between(stmt, "^(", ")")
            return self.output(self._format(self._eval(val, env), env))
        m = re.match(r"<input>\((.*?)\)(?:&=(.+))?$", stmt, re.S)
        if m:
            prompt = self._eval(m.group(1), env)
            value = self.input(str(prompt))
            target = m.group(2)
            if target:
                if "*" in target:
                    name = target.split("*")[-1]
                else:
                    name = target.strip()
                env[name] = value
            elif m.group(1).strip() in env:
                env[m.group(1).strip()] = value
            return value
        m = re.match(r"<now>\((.*)\)>(\w+)$", stmt, re.S)
        if m:
            env[m.group(2)] = self._eval(m.group(1), env); return env[m.group(2)]
        m = re.match(r"\*(\w+)\*(\w+)$", stmt)
        if m and m.group(1) in self.classes:
            env[m.group(2)] = self.classes[m.group(1)].instantiate(self); return env[m.group(2)]
        m = re.match(r"\*(\w+)\((.*)\)$", stmt, re.S)
        if m:
            return self._call_function(self.functions[m.group(1)], self._args(m.group(2), env), env)
        m = re.match(r"\$(\w+)\*(\w+)\((.*)\)$", stmt, re.S)
        if m:
            return env[m.group(1)].call(m.group(2), self._args(m.group(3), env))
        return None

    def _call_function(self, func: KoFunction, args: List[Any], base_env: Dict[str, Any]) -> Any:
        local = dict(self.env); local.update(base_env)
        for n, v in zip(func.params, args): local[n] = v
        result = self._exec_block(func.body, local)
        base_env.update({k: v for k, v in local.items() if k in base_env})
        return result

    def _exec_control(self, body: str, env: Dict[str, Any]) -> Any:
        last = None
        stmts = self._statements(body)
        i = 0
        while i < len(stmts):
            s = stmts[i].strip()
            if s.startswith("<if>") or s.startswith("<if<else>>"):
                chain = [s]
                i += 1
                while i < len(stmts) and stmts[i].strip().startswith(("<elif>", "<else>")):
                    chain.append(stmts[i].strip()); i += 1
                last = self._exec_if_chain(chain, env)
                continue
            last = self._exec_stmt(s, env)
            i += 1
        return last

    def _exec_if_chain(self, chain: List[str], env: Dict[str, Any]) -> Any:
        for branch in chain:
            m = re.match(r"<(if|elif|if<else>)>\((.*?)\)\s*\[(.*)\]$", branch, re.S)
            if m and self._eval(m.group(2), env):
                return self._exec_control(m.group(3), env)
            m = re.match(r"<else>\s*\[(.*)\]$", branch, re.S)
            if m:
                return self._exec_control(m.group(1), env)
        return None

    def _load_typed_decls(self, body: str, env: Dict[str, Any], remove: bool = False) -> str:
        def repl(m):
            typ, raw, name = m.groups(); val = self._literal(raw.strip(), typ, env); env[name] = val; return "" if remove else m.group(0)
        return re.sub(r"\b(int|freal|string|booling|byte)\((.*?)\)\*(\w+)", repl, body, flags=re.S)

    def _load_data_decls(self, body: str, env: Dict[str, Any], remove: bool = False) -> str:
        def repl(m):
            env[m.group(2)] = self._eval(m.group(1), env)
            return "" if remove else m.group(0)
        return re.sub(r"(?<!\w)(\([^\n]+?\))\*(\w+)", repl, body, flags=re.S)

    def _literal(self, raw: str, typ: str, env: Dict[str, Any]) -> Any:
        val = self._eval(raw, env)
        return bytes(str(val), "utf-8") if typ == "byte" else self.PRIMITIVES[typ](val)

    def _eval(self, expr: str, env: Dict[str, Any]) -> Any:
        expr = expr.strip()
        if len(expr) >= 2 and expr[0] == expr[-1] and expr[0] in "\"'":
            return expr[1:-1]
        expr = re.sub(r"<\$(\w+)>\((.*?)\)", lambda m: f"{m.group(1)}({m.group(2)})", expr)
        expr = re.sub(r"<\{(\w+)\}>", r"[\1]", expr)
        expr = re.sub(r"(\w+)<(\w+)>", r"\1[\2]", expr)
        try:
            return eval(expr, {"__builtins__": {}}, env)
        except Exception:
            return expr.strip('"\'')

    def _format(self, value: Any, env: Dict[str, Any]) -> str:
        text = re.sub(
            r"\{(\w+)<\{(\w+)\}>\}",
            lambda m: str(env.get(m.group(1), [])[env.get(m.group(2), 0)]),
            str(value),
        )
        def repl(m):
            expression = m.group(1)
            evaluated = self._eval(expression, env)
            return str(evaluated) if evaluated != expression else str(env.get(expression, "{" + expression + "}"))
        return re.sub(r"\{([^{}]+)\}", repl, text)

    def _args(self, text: str, env: Dict[str, Any]) -> List[Any]:
        return [] if not text.strip() else [self._eval(x, env) for x in text.split(",")]

    def _statements(self, body: str) -> List[str]:
        statements: List[str] = []
        start = 0
        depth = 0
        for i, ch in enumerate(body):
            if ch in "[({":
                depth += 1
            elif ch in "])}" and depth:
                depth -= 1
            elif ch == "\n" and depth == 0:
                part = body[start:i].strip()
                if part:
                    statements.append(part)
                start = i + 1
        tail = body[start:].strip()
        if tail:
            statements.append(tail)
        return statements

    def _between(self, text: str, start: str, end: str) -> str:
        i = text.find(start); j = text.rfind(end); return text[i + len(start):j]

    def _matching(self, text: str, start: int, op: str, cl: str) -> int:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == op: depth += 1
            elif text[i] == cl:
                depth -= 1
                if depth == 0: return i
        raise KoError(f"Unclosed {op}")


def run_file(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return KoInterpreter().run(f.read())


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run .ko 1.3 programs")
    ap.add_argument("source")
    ns = ap.parse_args(argv)
    run_file(ns.source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
