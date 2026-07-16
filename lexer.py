from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


class LexError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"{message} at line {line}, column {column}")
        self.message = message
        self.line = line
        self.column = column


@dataclass
class Token:
    type: str
    value: object
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type!r}, {self.value!r}, line={self.line}, col={self.column})"


class Lexer:
    """Simple lexer for a small subset of the Hanaka language."""

    KEYWORDS = {
        "let",
        "const",
        "if",
        "else",
        "for",
        "while",
        "do",
        "break",
        "continue",
        "return",
        "func",
        "class",
        "new",
        "import",
        "export",
        "async",
        "await",
        "true",
        "false",
        "null",
        "self",
        "super",
        "extends",
        "interface",
        "try",
        "catch",
        "throw",
        "finally",
        "in",
        "is",
        "as",
        "struct",
        "enum",
        "match",
        "type",
        "pub",
        "priv",
        "and",
        "or",
        "not",
    }

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.pos_start = 0
        self.line = 1
        self.column = 1

    def lex(self) -> List[Token]:
        tokens: List[Token] = []
        while not self._at_end():
            ch = self._peek()
            if ch in " \t\r":
                self._advance()
                continue
            if ch == "\n":
                self._advance()
                continue
            if ch == "/" and self._peek_next() == "/":
                self._advance()
                self._advance()
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
                continue
            if ch == "/" and self._peek_next() == "*":
                self._advance()
                self._advance()
                while not self._at_end():
                    if self._peek() == "*" and self._peek_next() == "/":
                        self._advance()
                        self._advance()
                        break
                    self._advance()
                else:
                    raise LexError("Unterminated block comment", self.line, self.column)
                continue
            if ch.isdigit():
                tokens.append(self._read_number())
                continue
            if ch == '"':
                tokens.append(self._read_string())
                continue
            if ch.isalpha() or ch == "_":
                tokens.append(self._read_identifier())
                continue
            token = self._read_symbol()
            if token is None:
                raise LexError(f"Unexpected character {ch!r}", self.line, self.column)
            tokens.append(token)
        tokens.append(Token("EOF", None, self.line, self.column))
        return tokens

    def _read_number(self) -> Token:
        start_line = self.line
        start_col = self.column
        start_pos = self.pos
        has_dot = False
        has_exp = False
        while not self._at_end():
            ch = self._peek()
            if ch.isdigit():
                self._advance()
                continue
            if ch == "." and not has_dot and not has_exp:
                has_dot = True
                self._advance()
                continue
            if ch in "eE" and not has_exp:
                has_exp = True
                self._advance()
                if not self._at_end() and self._peek() in "+-":
                    self._advance()
                while not self._at_end() and self._peek().isdigit():
                    self._advance()
                break
            break
        value = self.text[start_pos:self.pos]
        if has_dot or has_exp:
            return Token("FLOAT", float(value), start_line, start_col)
        return Token("INT", int(value), start_line, start_col)

    def _read_string(self) -> Token:
        start_line = self.line
        start_col = self.column
        start_pos = self.pos
        self._advance()
        chars = []
        while not self._at_end():
            ch = self._peek()
            if ch == '"':
                self._advance()
                return Token("STRING", "".join(chars), start_line, start_col)
            if ch == "\\":
                self._advance()
                if self._at_end():
                    raise LexError("Unterminated string literal", self.line, self.column)
                esc = self._peek()
                self._advance()
                mapping = {
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    '"': '"',
                    "\\": "\\",
                }
                chars.append(mapping.get(esc, esc))
            else:
                chars.append(ch)
                self._advance()
        raise LexError("Unterminated string literal", start_line, start_col)

    def _read_identifier(self) -> Token:
        start_line = self.line
        start_col = self.column
        start_pos = self.pos
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        text = self.text[start_pos:self.pos]
        if text in self.KEYWORDS:
            if text == "true":
                return Token("BOOL", True, start_line, start_col)
            if text == "false":
                return Token("BOOL", False, start_line, start_col)
            if text == "null":
                return Token("KEYWORD", "null", start_line, start_col)
            if text in {"and", "or", "not"}:
                if text == "and":
                    return Token("AND", "and", start_line, start_col)
                if text == "or":
                    return Token("OR", "or", start_line, start_col)
                return Token("NOT", "not", start_line, start_col)
            return Token("KEYWORD", text, start_line, start_col)
        return Token("IDENTIFIER", text, start_line, start_col)

    def _read_symbol(self) -> Optional[Token]:
        start_line = self.line
        start_col = self.column
        start_pos = self.pos
        ch = self._peek()
        if ch in "(){}[],:;.":
            self._advance()
            mapping = {
                "(": ("LPAREN", "("),
                ")": ("RPAREN", ")"),
                "{": ("LBRACE", "{"),
                "}": ("RBRACE", "}"),
                "[": ("LBRACKET", "["),
                "]": ("RBRACKET", "]"),
                ",": ("COMMA", ","),
                ":": ("COLON", ":"),
                ";": ("SEMICOLON", ";"),
                ".": ("DOT", "."),
            }
            return Token(mapping[ch][0], mapping[ch][1], start_line, start_col)
        if ch in "+-*/%":
            self._advance()
            mapping = {
                "+": "PLUS",
                "-": "MINUS",
                "*": "STAR",
                "/": "SLASH",
                "%": "PERCENT",
            }
            return Token(mapping[ch], ch, start_line, start_col)
        if ch == "^":
            self._advance()
            return Token("POWER", "^", start_line, start_col)
        if ch == "=":
            self._advance()
            if self._peek() == "=":
                self._advance()
                return Token("EQ", "==", start_line, start_col)
            if self._peek() == ">":
                self._advance()
                return Token("FAT_ARROW", "=>", start_line, start_col)
            return Token("ASSIGN", "=", start_line, start_col)
        if ch == "!":
            self._advance()
            if self._peek() == "=":
                self._advance()
                return Token("NEQ", "!=", start_line, start_col)
            return Token("NOT", "!", start_line, start_col)
        if ch == "<":
            self._advance()
            if self._peek() == "=":
                self._advance()
                return Token("LEQ", "<=", start_line, start_col)
            if self._peek() == "<":
                self._advance()
                return Token("LSHIFT", "<<", start_line, start_col)
            return Token("LT", "<", start_line, start_col)
        if ch == ">":
            self._advance()
            if self._peek() == "=":
                self._advance()
                return Token("GEQ", ">=", start_line, start_col)
            if self._peek() == ">":
                self._advance()
                return Token("RSHIFT", ">>", start_line, start_col)
            return Token("GT", ">", start_line, start_col)
        if ch == "&":
            self._advance()
            if self._peek() == "&":
                self._advance()
                return Token("AND", "&&", start_line, start_col)
            return Token("AMP", "&", start_line, start_col)
        if ch == "|":
            self._advance()
            if self._peek() == "|":
                self._advance()
                return Token("OR", "||", start_line, start_col)
            return Token("PIPE", "|", start_line, start_col)
        if ch == "+" and self._peek_next() == "+":
            self._advance()
            self._advance()
            return Token("INC", "++", start_line, start_col)
        if ch == "-" and self._peek_next() == "-":
            self._advance()
            self._advance()
            return Token("DEC", "--", start_line, start_col)
        if ch == "+" and self._peek_next() == "=":
            self._advance()
            self._advance()
            return Token("PLUS_ASSIGN", "+=", start_line, start_col)
        if ch == "-" and self._peek_next() == "=":
            self._advance()
            self._advance()
            return Token("MINUS_ASSIGN", "-=", start_line, start_col)
        if ch == "*" and self._peek_next() == "=":
            self._advance()
            self._advance()
            return Token("STAR_ASSIGN", "*=", start_line, start_col)
        if ch == "/" and self._peek_next() == "=":
            self._advance()
            self._advance()
            return Token("SLASH_ASSIGN", "/=", start_line, start_col)
        if ch == "-" and self._peek_next() == ">":
            self._advance()
            self._advance()
            return Token("ARROW", "->", start_line, start_col)
        if ch == "~":
            self._advance()
            return Token("TILDE", "~", start_line, start_col)
        return None

    def _advance(self) -> str:
        self.pos_start = self.pos
        ch = self.text[self.pos] if self.pos < len(self.text) else ""
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def _peek_next(self) -> str:
        return self.text[self.pos + 1] if self.pos + 1 < len(self.text) else ""

    def _at_end(self) -> bool:
        return self.pos >= len(self.text)

    @property
    def pos(self) -> int:
        return self._pos

    @pos.setter
    def pos(self, value: int) -> None:
        self._pos = value
        self.pos_start = value


def lex_text(text: str) -> List[Token]:
    return Lexer(text).lex()
