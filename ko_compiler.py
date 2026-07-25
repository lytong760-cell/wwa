from __future__ import annotations

import argparse
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


def _translate_expression(expr: str) -> str:
    expr = expr.strip()

    def replace_random(match: re.Match[str]) -> str:
        module_name = match.group(1)
        if module_name.lower() != "random":
            return match.group(0)
        args = [arg.strip() for arg in match.group(2).split(",") if arg.strip()]
        if len(args) >= 2:
            return f"random.randint({args[0]}, {args[1]})"
        if len(args) == 1:
            return f"random.randint(0, {args[0]})"
        return "random.randint(0, 1)"

    expr = re.sub(r"<\$([A-Za-z_][A-Za-z0-9_]*)>\(([^()]*)\)", replace_random, expr)
    expr = re.sub(r"<\$([A-Za-z_][A-Za-z0-9_]*)>\^\(([^()]*)\)", replace_random, expr)
    return expr


def compile_ko_source(source: str, file_name: str = "<stdin>", enforce_main: bool = False) -> str:
    lines = source.replace("\r\n", "\n").split("\n")
    output: List[str] = []
    indent_level = 0
    pending_indent = 0
    block_stack: List[str] = []
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
        if line == "]":
            if block_stack:
                popped = block_stack.pop()
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
            flush_line(f"if {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^elif\s*\((.*)\)\s*\[$", line):
            condition = re.match(r"^elif\s*\((.*)\)\s*\[$", line).group(1)
            flush_line(f"elif {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^else\s*\[$", line):
            flush_line("else:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^<if>\((.*)\)\s*\[$", line):
            condition = re.match(r"^<if>\((.*)\)\s*\[$", line).group(1)
            flush_line(f"if {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^<elif>\((.*)\)\s*\[$", line):
            condition = re.match(r"^<elif>\((.*)\)\s*\[$", line).group(1)
            flush_line(f"elif {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^<else>\s*\[$", line):
            flush_line("else:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^<if<else>>\((.*)\)\s*\[$", line):
            condition = re.match(r"^<if<else>>\((.*)\)\s*\[$", line).group(1)
            flush_line(f"if {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*!class\s*\[$", line):
            class_name = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*!class\s*\[$", line).group(1)
            flush_line(f"class {class_name}:")
            indent_level += 4
            pending_indent = indent_level
            block_stack.append("class")
            continue
        if re.match(r"^@loop\((.*)\)$", line, re.IGNORECASE):
            pending_loop_condition = re.match(r"^@loop\((.*)\)$", line, re.IGNORECASE).group(1)
            continue
        if re.match(r"^\*\*Loop\*\*\s*<for\.f\.whle>@also\s*\[$", line, re.IGNORECASE):
            condition = pending_loop_condition or "True"
            pending_loop_condition = None
            flush_line(f"while {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^\*\*Loop\*\*\s*<for>\(\*([A-Za-z_][A-Za-z0-9_]*=.*)\)\s*\[$", line, re.IGNORECASE):
            init_expr = re.match(r"^\*\*Loop\*\*\s*<for>\(\*([A-Za-z_][A-Za-z0-9_]*=.*)\)\s*\[$", line, re.IGNORECASE).group(1)
            flush_line(init_expr)
            flush_line("while True:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^loop\s*\((.*)\)\s*\[$", line, re.IGNORECASE):
            condition = re.match(r"^loop\s*\((.*)\)\s*\[$", line, re.IGNORECASE).group(1)
            flush_line(f"while {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
            continue
        if re.match(r"^while\s*\((.*)\)\s*\[$", line, re.IGNORECASE):
            condition = re.match(r"^while\s*\((.*)\)\s*\[$", line, re.IGNORECASE).group(1)
            flush_line(f"while {condition}:")
            block_stack.append("block")
            indent_level += 4
            pending_indent = indent_level
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
            py_type = {"int": "int", "freal": "float", "string": "str", "booling": "bool", "byte": "int"}.get(type_name, type_name)
            initializer = _translate_expression(initializer)
            flush_line(f"{var_name} = {py_type}({initializer})")
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
                flush_line(f"print(f{expr})")
            else:
                flush_line(f"print({expr})")
            continue
        if re.match(r"^<input>\((.*)\)&=([A-Za-z_][A-Za-z0-9_]*)$", line):
            prompt, target = re.match(r"^<input>\((.*)\)&=([A-Za-z_][A-Za-z0-9_]*)$", line).groups()
            prompt = _translate_expression(prompt)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            flush_line(f"{target} = input({prompt})")
            continue
        if re.match(r"^<now>\((.*)\)>([A-Za-z_][A-Za-z0-9_]*)$", line):
            expr, target = re.match(r"^<now>\((.*)\)>([A-Za-z_][A-Za-z0-9_]*)$", line).groups()
            expr = _translate_expression(expr)
            if enforce_main and not is_executable_scope():
                raise KoCompileError("Executable statements must be inside main or a function", line=lineno)
            if current_function_params_stack and target not in current_params():
                add_function_global(target)
            flush_line(f"{target} = {expr}")
            continue
        flush_line(line)
    if main_defined and enforce_main:
        output.append("\nmain()")
    return "\n".join(output)


def compile_ko_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    return compile_ko_source(source, file_name=path, enforce_main=True)


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
