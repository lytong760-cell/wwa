from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from typing import List, Optional


class KoCompileError(Exception):
    def __init__(self, message: str, line: int = 0, column: int = 0):
        super().__init__(f"{message} at line {line}, column {column}")
        self.message = message
        self.line = line
        self.column = column


def _split_args(text: str) -> List[str]:
    """Split comma-separated .ko arguments while respecting strings and nesting."""
    parts: List[str] = []
    current: List[str] = []
    stack: List[str] = []
    quote = ""
    escape = False
    pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
    for char in text:
        if quote:
            current.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == quote:
                quote = ""
            continue
        if char in ('"', "'"):
            quote = char
            current.append(char)
            continue
        if char in pairs:
            stack.append(pairs[char])
            current.append(char)
            continue
        if stack and char == stack[-1]:
            stack.pop()
            current.append(char)
            continue
        if char == "," and not stack:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _translate_data_literal(expr: str) -> str:
    expr = expr.strip()
    if not (expr.startswith("(") and expr.endswith(")")):
        return expr
    inner = expr[1:-1].strip()
    dict_match = re.fullmatch(r"(.+?)\s*\{(.+)\}", inner)
    if dict_match:
        return "{" + f"{_translate_expression(dict_match.group(1))}: {_translate_expression(dict_match.group(2))}" + "}"
    parts = _split_args(inner)
    if len(parts) == 1:
        nested = re.fullmatch(r"(.+?)\s*\((.*)\)", parts[0])
        if nested:
            return f"({_translate_expression(nested.group(1))}, {_translate_data_literal('(' + nested.group(2) + ')')})"
    return "(" + ", ".join(_translate_expression(part) for part in parts) + ("," if len(parts) == 1 else "") + ")"


def _translate_index_access(expr: str) -> str:
    pattern = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)<([^<>]+)(?:<([^<>]+)>)?>")
    while True:
        def replace_index(match: re.Match[str]) -> str:
            first = _translate_expression(match.group(2)).strip()
            second = _translate_expression(match.group(3)).strip() if match.group(3) is not None else None
            if first.startswith("{") and first.endswith("}"):
                first = first[1:-1].strip()
            if second is not None and second.startswith("{") and second.endswith("}"):
                second = second[1:-1].strip()
            if second is None:
                return f"{match.group(1)}[{first}]"
            return f"{match.group(1)}[{first}][{second}]"

        replaced = pattern.sub(replace_index, expr)
        if replaced == expr:
            return expr
        expr = replaced


def _translate_expression(expr: str) -> str:
    expr = expr.strip()
    expr = expr.replace("\\True\\", "True").replace("\\False\\", "False")

    def replace_random(match: re.Match[str]) -> str:
        module_name = match.group(1)
        if module_name.lower() != "random":
            return match.group(0)
        args = [arg.strip() for arg in _split_args(match.group(2)) if arg.strip()]
        if len(args) >= 2:
            return f"random.randint({_translate_expression(args[0])}, {_translate_expression(args[1])})"
        if len(args) == 1:
            return f"random.randint(0, {_translate_expression(args[0])})"
        return "random.randint(0, 1)"

    expr = re.sub(r"<\$([A-Za-z_][A-Za-z0-9_]*)>\(([^()]*)\)", replace_random, expr)
    expr = re.sub(r"<\$([A-Za-z_][A-Za-z0-9_]*)>\^\(([^()]*)\)", replace_random, expr)
    expr = _translate_index_access(expr)
    return expr


def _translate_format_string(expr: str) -> str:
    return _translate_index_access(expr)


def compile_ko_source(source: str, file_name: str = "<stdin>", enforce_main: bool = False) -> str:
    lines = source.replace("\r\n", "\n").split("\n")
    output: List[str] = []
    indent_level = 0
    pending_indent = 0
    block_stack: List[str] = []
    class_attrs_stack: List[List[str]] = []
    main_defined = False
    pending_loop_condition: Optional[str] = None
    module_aliases = {
        "random": "random",
        "Random": "random",
        "math": "math",
        "Math": "math",
        "sys": "sys",
        "Sys": "sys",
        "os": "os",
        "Os": "os",
        "json": "json",
        "Json": "json",
        "re": "re",
        "Re": "re",
        "datetime": "datetime",
        "Datetime": "datetime",
    }

    def flush_line(line: str) -> None:
        nonlocal indent_level, pending_indent
        output.append(" " * indent_level + line)

    def is_executable_scope() -> bool:
        return any(scope in ("main", "function", "method") for scope in block_stack)

    def parse_params(raw_params: str) -> List[str]:
        params: List[str] = []
        for part in raw_params.split(","):
            fragment = part.strip()
            if not fragment:
                continue
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\*([A-Za-z_][A-Za-z0-9_]*)$", fragment)
            if match:
                params.append(match.group(2))
            else:
                params.append(fragment)
        return params

    current_function_params_stack: List[List[str]] = []
    current_function_globals_stack: List[List[str]] = []

    def current_params() -> List[str]:
        return current_function_params_stack[-1] if current_function_params_stack else []

    def current_globals() -> List[str]:
        return current_function_globals_stack[-1] if current_function_globals_stack else []

    def add_function_global(name: str) -> None:
        if not current_function_globals_stack:
            return
        globals_list = current_function_globals_stack[-1]
        if name not in globals_list:
            globals_list.append(name)
            flush_line(f"global {name}")

    def open_block(header: str, scope: str = "block") -> None:
        nonlocal indent_level, pending_indent
        flush_line(header)
        block_stack.append(scope)
        indent_level += 4
        pending_indent = indent_level

    def parse_loop_header(loop_expr: str) -> List[str]:
        expression = _translate_expression(loop_expr.strip())
        assignment_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", expression)
        if assignment_match:
            name, value = assignment_match.groups()
            return [f"{name} = {value}", "while True:"]

        step_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*([+-])\s*(.+)", expression)
        if step_match:
            name, operator, value = step_match.groups()
            return [f"{name} = globals().get('{name}', 0)", "while True:", f"{name} = {name} {operator} ({value})"]

        return ["while True:"]

    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            output.append("")
            continue
        if line == "[":
            if not block_stack:
                block_stack.append("main")
            else:
                block_stack.append("anon")
            continue
        if line.startswith("|") and line.endswith("|"):
            continue
        if line == "]":
            if block_stack:
                popped = block_stack.pop()
                if popped == "class" and class_attrs_stack:
                    class_attrs_stack.pop()
                if popped in ("function", "method"):
                    if current_function_params_stack:
                        current_function_params_stack.pop()
                    if current_function_globals_stack:
                        current_function_globals_stack.pop()
            if indent_level >= 4:
                indent_level -= 4
            continue
        if re.match(r"^@private\s*\[$", line):
            flush_line("pass")
            continue
        if re.match(r"^if\s*\((.*)\)\s*\[$", line):
            condition = re.match(r"^if\s*\((.*)\)\s*\[$", line).group(1)
            open_block(f"if {_translate_expression(condition)}:")
            continue
        if re.match(r"^elif\s*\((.*)\)\s*\[$", line):
            condition = re.match(r"^elif\s*\((.*)\)\s*\[$", line).group(1)
            open_block(f"elif {_translate_expression(condition)}:")
            continue
        if re.match(r"^else\s*\[$", line):
            open_block("else:")
            continue
        if re.match(r"^<if>\((.*)\)\s*\[$", line):
            condition = re.match(r"^<if>\((.*)\)\s*\[$", line).group(1)
            open_block(f"if {_translate_expression(condition)}:")
            continue
        if re.match(r"^<elif>\((.*)\)\s*\[$", line):
            condition = re.match(r"^<elif>\((.*)\)\s*\[$", line).group(1)
            open_block(f"elif {_translate_expression(condition)}:")
            continue
        if re.match(r"^<else>\s*\[$", line):
            open_block("else:")
            continue
        if re.match(r"^<if<else>>\((.*)\)\s*\[$", line):
            condition = re.match(r"^<if<else>>\((.*)\)\s*\[$", line).group(1)
            open_block(f"if {_translate_expression(condition)}:")
            continue
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*!class\s*\[$", line):
            class_name = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*!class\s*\[$", line).group(1)
            flush_line(f"class {class_name}:")
            indent_level += 4
            pending_indent = indent_level
            block_stack.append("class")
            class_attrs_stack.append([])
            continue
        if re.match(r"^@loop\((.*)\)$", line, re.IGNORECASE):
            pending_loop_condition = re.match(r"^@loop\((.*)\)$", line, re.IGNORECASE).group(1)
            continue
        if re.match(r"^\*\*Loop\*\*\s*<for\.f\.whle>@also\s*\[$", line, re.IGNORECASE):
            condition = pending_loop_condition or "True"
            pending_loop_condition = None
            open_block(f"while {_translate_expression(condition)}:")
            continue
        if re.match(r"^\*\*Loop\*\*\s*<for>\(\*(.+)\)\s*\[$", line, re.IGNORECASE):
            loop_expr = re.match(r"^\*\*Loop\*\*\s*<for>\(\*(.+)\)\s*\[$", line, re.IGNORECASE).group(1)
            loop_lines = parse_loop_header(loop_expr)
            body_lines = []
            if "while True:" in loop_lines:
                header_index = loop_lines.index("while True:")
                for loop_line in loop_lines[:header_index]:
                    flush_line(loop_line)
                flush_line("while True:")
                body_lines = loop_lines[header_index + 1:]
            else:
                flush_line(loop_lines[-1])
            block_stack.append("block")
            indent_level += 4
            for loop_line in body_lines:
                flush_line(loop_line)
            pending_indent = indent_level
            continue
        if re.match(r"^loop\s*\((.*)\)\s*\[$", line, re.IGNORECASE):
            condition = re.match(r"^loop\s*\((.*)\)\s*\[$", line, re.IGNORECASE).group(1)
            open_block(f"while {_translate_expression(condition)}:")
            continue
        if re.match(r"^while\s*\((.*)\)\s*\[$", line, re.IGNORECASE):
            condition = re.match(r"^while\s*\((.*)\)\s*\[$", line, re.IGNORECASE).group(1)
            open_block(f"while {_translate_expression(condition)}:")
            continue
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*\[$", line):
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*\[$", line)
            fn_name = match.group(1)
            raw_params = match.group(2)
            params = parse_params(raw_params)
            current_function_params_stack.append(params)
            current_function_globals_stack.append([])
            in_class = any(scope == "class" for scope in block_stack)
            if in_class:
                signature = ["self", *params]
                flush_line(f"def {fn_name}({', '.join(signature)}):")
                block_stack.append("method")
            else:
                if fn_name == "main":
                    main_defined = True
                flush_line(f"def {fn_name}({', '.join(params)}):" if params else f"def {fn_name}():")
                block_stack.append("function")
            indent_level += 4
            if in_class and class_attrs_stack:
                for attr in class_attrs_stack[-1]:
                    flush_line(f"{attr} = self.{attr}")
            pending_indent = indent_level
            continue
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\[$", line):
            fn_name = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\[$", line).group(1)
            current_function_params_stack.append([])
            current_function_globals_stack.append([])
            in_class = any(scope == "class" for scope in block_stack)
            if in_class:
                flush_line(f"def {fn_name}(self):")
                block_stack.append("method")
            else:
                if fn_name == "main":
                    main_defined = True
                flush_line(f"def {fn_name}():")
                block_stack.append("function")
            indent_level += 4
            if in_class and class_attrs_stack:
                for attr in class_attrs_stack[-1]:
                    flush_line(f"{attr} = self.{attr}")
            pending_indent = indent_level
            continue
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\[$", line):
            name = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\[$", line).group(1)
            current_function_params_stack.append([])
            current_function_globals_stack.append([])
            in_class = any(scope == "class" for scope in block_stack)
            if in_class:
                flush_line(f"def {name}(self):")
                block_stack.append("method")
            else:
                if name == "main":
                    main_defined = True
                flush_line(f"def {name}():")
                block_stack.append("function")
            indent_level += 4
            if in_class and class_attrs_stack:
                for attr in class_attrs_stack[-1]:
                    flush_line(f"{attr} = self.{attr}")
            pending_indent = indent_level
            continue
        if re.match(r"^\*([A-Za-z_][A-Za-z0-9_]*)\*([A-Za-z_][A-Za-z0-9_]*)\s*$", line):
            class_name, var_name = re.match(r"^\*([A-Za-z_][A-Za-z0-9_]*)\*([A-Za-z_][A-Za-z0-9_]*)\s*$", line).groups()
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"{var_name} = {class_name}()")
            continue
        if re.match(r"^\*\*Import\*\*\(\$([A-Za-z_][A-Za-z0-9_]*)\)@also%\*([A-Za-z_][A-Za-z0-9_]*)(!`[^`]+`)?:(.+)$", line):
            match = re.match(r"^\*\*Import\*\*\(\$([A-Za-z_][A-Za-z0-9_]*)\)@also%\*([A-Za-z_][A-Za-z0-9_]*)(!`[^`]+`)?:(.+)$", line)
            module_name = match.group(1)
            alias = match.group(2)
            python_module = module_aliases.get(module_name, module_name.lower())
            flush_line(f"import {python_module} as {alias}")
            continue
        if re.match(r"^\*\*Import\*\*\(\$([A-Za-z_][A-Za-z0-9_]*)\)\s*\[$", line):
            module_name = re.match(r"^\*\*Import\*\*\(\$([A-Za-z_][A-Za-z0-9_]*)\)\s*\[$", line).group(1)
            python_module = module_aliases.get(module_name, module_name.lower())
            flush_line(f"import {python_module}")
            continue
        if re.match(r"^<([A-Za-z_][A-Za-z0-9_]*)>\^\((.*)\)\*([A-Za-z_][A-Za-z0-9_]*)$", line):
            module_name, args, target = re.match(r"^<([A-Za-z_][A-Za-z0-9_]*)>\^\((.*)\)\*([A-Za-z_][A-Za-z0-9_]*)$", line).groups()
            if module_name.lower() == "random":
                translated = _translate_expression(f"<$random>^({args})")
                flush_line(f"{target} = {translated}")
                continue
        if re.match(r"^\*([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s*$", line):
            fn_name = re.match(r"^\*([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s*$", line).group(1)
            args = re.match(r"^\*([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s*$", line).group(2)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"{fn_name}({args})")
            continue
        if re.match(r"^\*([A-Za-z_][A-Za-z0-9_]*)\(\)\s*$", line):
            fn_name = re.match(r"^\*([A-Za-z_][A-Za-z0-9_]*)\(\)\s*$", line).group(1)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"{fn_name}()")
            continue
        if re.match(r"^\$([A-Za-z_][A-Za-z0-9_]*)\*([A-Za-z_][A-Za-z0-9_]*)\s*$", line):
            obj, method = re.match(r"^\$([A-Za-z_][A-Za-z0-9_]*)\*([A-Za-z_][A-Za-z0-9_]*)\s*$", line).groups()
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"{obj}.{method}()")
            continue
        if re.match(r"^\$([A-Za-z_][A-Za-z0-9_]*)\*([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s*$", line):
            obj, method, args = re.match(r"^\$([A-Za-z_][A-Za-z0-9_]*)\*([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s*$", line).groups()
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"{obj}.{method}({args})")
            continue
        if re.match(r"^(int|freal|string|booling|byte)\((.*)\)\*([A-Za-z_][A-Za-z0-9_]*)$", line):
            type_name, initializer, var_name = re.match(r"^(int|freal|string|booling|byte)\((.*)\)\*([A-Za-z_][A-Za-z0-9_]*)$", line).groups()
            py_type = {"int": "int", "freal": "float", "string": "str", "booling": "bool", "byte": "bytes"}.get(type_name, type_name)
            initializer = _translate_expression(initializer)
            if class_attrs_stack and any(scope == "class" for scope in block_stack) and not any(scope in ("function", "method") for scope in block_stack):
                class_attrs_stack[-1].append(var_name)
            if type_name == "byte":
                flush_line(f"{var_name} = bytes({initializer}, 'utf-8') if isinstance({initializer}, str) else bytes({initializer})")
            else:
                flush_line(f"{var_name} = {py_type}({initializer})")
            continue
        if re.match(r"^\((.*)\)\*([A-Za-z_][A-Za-z0-9_]*)$", line):
            initializer, var_name = re.match(r"^\((.*)\)\*([A-Za-z_][A-Za-z0-9_]*)$", line).groups()
            if class_attrs_stack and any(scope == "class" for scope in block_stack) and not any(scope in ("function", "method") for scope in block_stack):
                class_attrs_stack[-1].append(var_name)
            flush_line(f"{var_name} = {_translate_data_literal('(' + initializer + ')')}")
            continue
        if re.match(r"^<print>.+\^\((.*)\)$", line):
            expr = re.match(r"^<print>.+\^\((.*)\)$", line).group(1)
            expr = _translate_expression(expr)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"print({expr})")
            continue
        if re.match(r"^<printf>\^\((.*)\)$", line):
            expr = re.match(r"^<printf>\^\((.*)\)$", line).group(1)
            expr = _translate_expression(expr)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            if "{" in expr and "}" in expr:
                expr = _translate_format_string(expr)
                flush_line(f"print(f{expr})")
            else:
                flush_line(f"print({expr})")
            continue
        if re.match(r"^<input>\((.*)\)&=(?:(?:string)\(.*\)\*)?([A-Za-z_][A-Za-z0-9_]*)$", line):
            prompt, target = re.match(r"^<input>\((.*)\)&=(?:(?:string)\(.*\)\*)?([A-Za-z_][A-Za-z0-9_]*)$", line).groups()
            prompt = _translate_expression(prompt)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"{target} = input({prompt})")
            if "method" in block_stack and class_attrs_stack and target in class_attrs_stack[-1]:
                flush_line(f"self.{target} = {target}")
            continue
        if re.match(r"^<input>\((.*)\)$", line):
            target_or_prompt = _translate_expression(re.match(r"^<input>\((.*)\)$", line).group(1))
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", target_or_prompt):
                flush_line(f"{target_or_prompt} = input()")
            else:
                flush_line(f"input({target_or_prompt})")
            continue
        if re.match(r"^<memory>\^([A-Za-z_][A-Za-z0-9_]*)$", line):
            name = re.match(r"^<memory>\^([A-Za-z_][A-Za-z0-9_]*)$", line).group(1)
            flush_line(f"memoryview(bytes(str({name}), 'utf-8'))")
            continue
        if re.match(r"^<now>\((.*)\)>([A-Za-z_][A-Za-z0-9_]*)$", line):
            expr, target = re.match(r"^<now>\((.*)\)>([A-Za-z_][A-Za-z0-9_]*)$", line).groups()
            expr = _translate_expression(expr)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            if current_function_params_stack and target not in current_params():
                add_function_global(target)
            flush_line(f"{target} = {expr}")
            if "method" in block_stack and class_attrs_stack and target in class_attrs_stack[-1]:
                flush_line(f"self.{target} = {target}")
            continue
        flush_line(line)
    if enforce_main and not main_defined:
        if "main" not in block_stack and not any(line.strip() == "[" for line in lines):
            raise KoCompileError("A .ko program must define a main block [ ]", line=0, column=0)
    if main_defined and enforce_main:
        output.append("\nmain()")
    return "\n".join(output)


def compile_ko_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    code = compile_ko_source(source, file_name=path, enforce_main=True)
    try:
        ast.parse(code, filename=path)
    except SyntaxError as exc:
        raise KoCompileError(
            f"Generated Python is invalid: {exc.msg}",
            line=exc.lineno or 0,
            column=exc.offset or 0,
        ) from exc
    return code


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compile and run .ko source")
    parser.add_argument("source", help="Path to a .ko file")
    parser.add_argument("--show-code", action="store_true", help="Print the generated Python instead of executing it")
    args = parser.parse_args(argv)
    if not args.source:
        parser.print_help()
        return 1
    if not os.path.exists(args.source):
        print(f"File not found: {args.source}", file=sys.stderr)
        return 1
    try:
        code = compile_ko_file(args.source)
    except KoCompileError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.show_code:
        print(code)
        return 0

    namespace = {}
    exec(code, namespace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
