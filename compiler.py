from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List

from lexer import Lexer, LexError
from parser import Parser, ParseError
from semantic import SemanticAnalyzer, SemanticError
from codegen import CodeGen
from vm import VirtualMachine, VMError


class CompilerError(Exception):
    def __init__(self, message: str, file_name: str = "<unknown>", line: int = 0, column: int = 0):
        super().__init__(f"{file_name}:{line}:{column}: {message}")
        self.message = message
        self.file_name = file_name
        self.line = line
        self.column = column


def compile_source(source: str, file_name: str = "<stdin>") -> Dict[str, Any]:
    try:
        tokens = Lexer(source).lex()
    except LexError as exc:
        raise CompilerError(exc.message, file_name, exc.line, exc.column) from exc

    try:
        ast = Parser(tokens).parse()
    except ParseError as exc:
        raise CompilerError(exc.message, file_name, exc.line, exc.column) from exc

    try:
        analyzed = SemanticAnalyzer().analyze(ast)
    except SemanticError as exc:
        raise CompilerError(exc.message, file_name, exc.line, exc.column) from exc

    bytecode = CodeGen().generate(analyzed)
    return {"tokens": tokens, "ast": analyzed, "bytecode": bytecode, "globals": {}}


def run_file(path: str, verbose: bool = False, dump_ast: bool = False, dump_tokens: bool = False, dump_bytecode: bool = False) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()
    result = compile_source(source, file_name=path)
    if verbose:
        print("[tokens]")
        for token in result["tokens"]:
            print(token)
    if dump_tokens:
        print("[tokens]")
        for token in result["tokens"]:
            print(token)
    if dump_ast:
        print("[ast]")
        print(result["ast"])
    if dump_bytecode:
        print("[bytecode]")
        for instr in result["bytecode"]:
            print(instr)
    vm = VirtualMachine()
    return vm.run(result["bytecode"], ast=result["ast"])


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hanaka compiler")
    parser.add_argument("source", nargs="?", help="Path to a .hk source file")
    parser.add_argument("--run", action="store_true", help="Compile and execute")
    parser.add_argument("--verbose", action="store_true", help="Print intermediate stages")
    parser.add_argument("--dump-ast", action="store_true")
    parser.add_argument("--dump-tokens", action="store_true")
    parser.add_argument("--dump-bytecode", action="store_true")
    args = parser.parse_args(argv)
    if not args.source:
        parser.print_help()
        return 1
    try:
        result = run_file(args.source, verbose=args.verbose, dump_ast=args.dump_ast, dump_tokens=args.dump_tokens, dump_bytecode=args.dump_bytecode)
        if args.run or args.verbose or args.dump_ast or args.dump_tokens or args.dump_bytecode:
            return 0
        return 0
    except (CompilerError, LexError, ParseError, SemanticError, VMError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
