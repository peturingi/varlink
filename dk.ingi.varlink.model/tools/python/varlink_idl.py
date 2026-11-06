"""Varlink IDL parser and formatter, following UAPI.20 Varlink IPC v0.1.

Pure Python 3.15 standard library. Parses the interface definition language
exactly as the spec's PEG grammar defines it, and additionally recognises the
systemd comment conventions that carry method flags and experimental markers:

    # [Supports 'more' flag]      # [Requires 'more' flag]
    # [Supports 'upgrade' flag]   # [Requires 'upgrade' flag]
    # [Experimental]

The AST is a set of frozen dataclasses. `format_interface` renders an AST back
to canonical IDL text; `parse_interface(format_interface(ast)) == ast` holds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

# --------------------------------------------------------------------------- AST


class Primitive(Enum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    OBJECT = "object"
    ANY = "any"


@dataclass(frozen=True, slots=True)
class PrimitiveType:
    kind: Primitive


@dataclass(frozen=True, slots=True)
class NamedTypeRef:
    name: str


@dataclass(frozen=True, slots=True)
class Field:
    name: str
    type: TypeExpr
    doc: tuple[str, ...] = ()
    experimental: bool = False


@dataclass(frozen=True, slots=True)
class EnumValue:
    name: str
    doc: tuple[str, ...] = ()
    experimental: bool = False


@dataclass(frozen=True, slots=True)
class StructType:
    fields: tuple[Field, ...] = ()


@dataclass(frozen=True, slots=True)
class EnumType:
    values: tuple[EnumValue, ...] = ()


@dataclass(frozen=True, slots=True)
class ArrayType:
    element: TypeExpr


@dataclass(frozen=True, slots=True)
class MapType:
    value: TypeExpr


@dataclass(frozen=True, slots=True)
class NullableType:
    inner: TypeExpr  # never itself a NullableType (grammar: "?" element_type | "?" "[]" type | "?" "[string]" type)


type TypeExpr = PrimitiveType | NamedTypeRef | StructType | EnumType | ArrayType | MapType | NullableType


@dataclass(frozen=True, slots=True)
class TypeDef:
    name: str
    type: StructType | EnumType
    doc: tuple[str, ...] = ()
    experimental: bool = False


@dataclass(frozen=True, slots=True)
class Method:
    name: str
    input: StructType
    output: StructType
    doc: tuple[str, ...] = ()
    experimental: bool = False
    supports_more: bool = False
    requires_more: bool = False
    supports_upgrade: bool = False
    requires_upgrade: bool = False


@dataclass(frozen=True, slots=True)
class Error:
    name: str
    parameters: StructType
    doc: tuple[str, ...] = ()
    experimental: bool = False


type Member = TypeDef | Method | Error


@dataclass(frozen=True, slots=True)
class Interface:
    name: str
    members: tuple[Member, ...]
    doc: tuple[str, ...] = ()
    experimental: bool = False


# --------------------------------------------------------------------- lexing

INTERFACE_NAME_RE = re.compile(r"[A-Za-z](?:-*[A-Za-z0-9])*(?:\.[A-Za-z0-9](?:-*[A-Za-z0-9])*)+")
NAME_RE = re.compile(r"[A-Z][A-Za-z0-9]*")
FIELD_NAME_RE = re.compile(r"[A-Za-z](?:_?[A-Za-z0-9])*")

# PEG: whitespace (ECMA-262 WhiteSpace minus \v\f) and eol_r (LineTerminator)
_WS = "[ \t ﻿ ᠎ -   　]"
_EOL = "(?:\r\n|\n|\r| | )"
_TOKEN_RE = re.compile(
    rf"(?P<ws>{_WS}+)"
    rf"|(?P<eol>{_EOL})"
    rf"|(?P<comment>#[^\n\r  ]*)"
    r"|(?P<arrow>->)"
    r"|(?P<dict>\[string\])"
    r"|(?P<array>\[\])"
    r"|(?P<punct>[(),:?])"
    r"|(?P<word>[A-Za-z][A-Za-z0-9_.\-]*)"
)

EXPERIMENTAL_MARKER = "[Experimental]"
FLAG_MARKERS: dict[str, str] = {
    "[Supports 'more' flag]": "supports_more",
    "[Requires 'more' flag]": "requires_more",
    "[Supports 'upgrade' flag]": "supports_upgrade",
    "[Requires 'upgrade' flag]": "requires_upgrade",
}


class VarlinkSyntaxError(ValueError):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{line}:{column}: {message}")
        self.line, self.column = line, column


@dataclass(slots=True)
class _Token:
    kind: str
    text: str
    line: int
    column: int
    at_line_start: bool  # for comments: nothing but whitespace precedes it on its line


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos, line, col = 0, 1, 1
    line_start = True
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise VarlinkSyntaxError(f"unexpected character {text[pos]!r}", line, col)
        kind = m.lastgroup
        assert kind is not None
        s = m.group()
        if kind == "ws":
            pass
        elif kind == "eol":
            tokens.append(_Token("eol", s, line, col, line_start))
            line, col, line_start = line + 1, 1, True
            pos = m.end()
            continue
        else:
            tokens.append(_Token(kind, s, line, col, line_start))
            line_start = False
        col += len(s)
        pos = m.end()
    return tokens


# -------------------------------------------------------------------- parsing


class _Parser:
    def __init__(self, text: str) -> None:
        self.toks = _tokenize(text)
        self.i = 0

    # -- token helpers -----------------------------------------------------
    def _peek(self) -> _Token | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _error(self, msg: str) -> VarlinkSyntaxError:
        t = self._peek()
        if t is None:
            last = self.toks[-1] if self.toks else None
            return VarlinkSyntaxError(msg + " (at end of input)", last.line if last else 1, last.column if last else 1)
        return VarlinkSyntaxError(msg + f", got {t.text!r}", t.line, t.column)

    def _skip_trivia(self) -> tuple[str, ...]:
        """Skip comments and line ends; return the documentation block, i.e. the
        comment lines that are contiguous (no blank line) and immediately precede
        the next token. Comments that start on a line after other tokens are not
        documentation (PEG: a doc comment "starts on a new line")."""
        doc: list[str] = []
        blank_run = 0
        while (t := self._peek()) is not None and t.kind in ("comment", "eol"):
            if t.kind == "eol":
                blank_run += 1
                if blank_run >= 2:
                    doc.clear()  # a blank line separates the comment block from what follows
            else:
                blank_run = 0
                if not t.at_line_start:
                    doc.clear()  # trailing comment on a code line: not documentation
                else:
                    body = t.text[1:]
                    doc.append(body[1:] if body.startswith(" ") else body)  # strip one conventional space
            self.i += 1
        return tuple(doc)

    def _expect(self, kind: str, text: str | None = None) -> _Token:
        t = self._peek()
        if t is None or t.kind != kind or (text is not None and t.text != text):
            raise self._error(f"expected {text or kind}")
        self.i += 1
        return t

    def _accept(self, kind: str, text: str | None = None) -> _Token | None:
        t = self._peek()
        if t is not None and t.kind == kind and (text is None or t.text == text):
            self.i += 1
            return t
        return None

    # -- grammar -----------------------------------------------------------
    def interface(self) -> Interface:
        doc = self._skip_trivia()
        experimental, doc = _split_markers(doc, allow_flags=False)[0], _strip_markers(doc, flags=False)
        self._expect("word", "interface")
        name_tok = self._expect("word")
        if not INTERFACE_NAME_RE.fullmatch(name_tok.text):
            raise VarlinkSyntaxError(f"invalid interface name {name_tok.text!r}", name_tok.line, name_tok.column)
        members: list[Member] = []
        while True:
            mdoc = self._skip_trivia()
            t = self._peek()
            if t is None:
                break
            if t.kind != "word" or t.text not in ("type", "method", "error"):
                raise self._error("expected 'type', 'method' or 'error'")
            is_method = t.text == "method"
            flags, mdoc = _split_markers(mdoc, allow_flags=is_method), _strip_markers(mdoc, flags=is_method)
            self.i += 1
            mname = self._expect("word")
            if not NAME_RE.fullmatch(mname.text):
                raise VarlinkSyntaxError(f"invalid member name {mname.text!r}", mname.line, mname.column)
            if t.text == "type":
                body = self._struct_or_enum()
                members.append(TypeDef(mname.text, body, mdoc, flags[0]))
            elif t.text == "method":
                inp = self._struct()
                self._skip_trivia()
                self._expect("arrow")
                out = self._struct()
                members.append(Method(mname.text, inp, out, mdoc, flags[0], *flags[1:]))
            else:
                params = self._struct()
                members.append(Error(mname.text, params, mdoc, flags[0]))
        return Interface(name_tok.text, tuple(members), doc, experimental)

    def _struct(self) -> StructType:
        body = self._struct_or_enum(struct_only=True)
        assert isinstance(body, StructType)
        return body

    def _struct_or_enum(self, struct_only: bool = False) -> StructType | EnumType:
        self._skip_trivia()
        self._expect("punct", "(")
        fields: list[Field] = []
        values: list[EnumValue] = []
        kind: Literal["struct", "enum"] | None = "struct" if struct_only else None
        while True:
            doc = self._skip_trivia()
            if self._accept("punct", ")"):
                break
            name = self._expect("word")
            if not FIELD_NAME_RE.fullmatch(name.text):
                raise VarlinkSyntaxError(f"invalid field name {name.text!r}", name.line, name.column)
            experimental, doc = _split_markers(doc, allow_flags=False)[0], _strip_markers(doc, flags=False)
            self._skip_trivia()
            if self._accept("punct", ":"):
                if kind == "enum":
                    raise self._error("struct field inside enum")
                kind = "struct"
                fields.append(Field(name.text, self._type(), doc, experimental))
            else:
                if kind == "struct":
                    raise self._error("expected ':' after field name")
                kind = "enum"
                values.append(EnumValue(name.text, doc, experimental))
            self._skip_trivia()
            if self._accept("punct", ","):
                # Look ahead WITHOUT consuming: the comment lines after the comma document the next entry.
                mark = self.i
                self._skip_trivia()
                t = self._peek()
                self.i = mark
                if t is not None and t.kind == "punct" and t.text == ")":
                    # UAPI.20 grammar: struct_fields = struct_field | struct_field "," struct_fields (no trailing
                    # comma). systemd 263's parser rejects it too ("Bad syntax").
                    raise self._error("trailing comma is not allowed by the UAPI.20 grammar")
                continue
            self._skip_trivia()
            self._expect("punct", ")")
            break
        if kind == "enum":
            return EnumType(tuple(values))
        return StructType(tuple(fields))

    def _type(self) -> TypeExpr:
        self._skip_trivia()
        nullable = self._accept("punct", "?") is not None
        self._skip_trivia()
        if self._accept("array"):
            inner: TypeExpr = ArrayType(self._type())
        elif self._accept("dict"):
            inner = MapType(self._type())
        else:
            inner = self._element_type()
        return NullableType(inner) if nullable else inner

    def _element_type(self) -> TypeExpr:
        self._skip_trivia()
        t = self._peek()
        if t is None:
            raise self._error("expected type")
        if t.kind == "punct" and t.text == "(":
            return self._struct_or_enum()
        if t.kind == "word":
            self.i += 1
            try:
                return PrimitiveType(Primitive(t.text))
            except ValueError:
                pass
            if NAME_RE.fullmatch(t.text):
                return NamedTypeRef(t.text)
            raise VarlinkSyntaxError(f"invalid type name {t.text!r}", t.line, t.column)
        raise self._error("expected type")


def _split_markers(doc: tuple[str, ...], allow_flags: bool) -> tuple[bool, bool, bool, bool, bool]:
    """(experimental, supports_more, requires_more, supports_upgrade, requires_upgrade)."""
    experimental = EXPERIMENTAL_MARKER in doc
    flags = {v: False for v in FLAG_MARKERS.values()}
    if allow_flags:
        for line in doc:
            if line in FLAG_MARKERS:
                flags[FLAG_MARKERS[line]] = True
    return (experimental, flags["supports_more"], flags["requires_more"], flags["supports_upgrade"], flags["requires_upgrade"])


def _strip_markers(doc: tuple[str, ...], flags: bool = True) -> tuple[str, ...]:
    """Remove the systemd marker lines that became flags. Flag-marker lines only mean something before
    `method`; elsewhere systemd treats them as ordinary comments, so they stay in the documentation."""
    return tuple(line for line in doc if line != EXPERIMENTAL_MARKER and not (flags and line in FLAG_MARKERS))


def parse_interface(text: str) -> Interface:
    """Parse one interface definition (the content of a .varlink file)."""
    p = _Parser(text)
    iface = p.interface()
    p._skip_trivia()
    if p._peek() is not None:
        raise p._error("unexpected trailing input")
    return iface


def parse_interfaces(text: str) -> list[Interface]:
    """Parse a concatenation of several interface definitions, as `varlinkctl introspect` prints them."""
    chunks: list[list[str]] = []
    pending: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("interface "):
            chunks.append(pending + [line])
            pending = []
        elif chunks and not (line.startswith("#") and pending):
            if line.startswith("#"):
                pending.append(line)  # may belong to the next interface
            elif line.strip() == "" and pending:
                chunks[-1].extend(pending); pending = []; chunks[-1].append(line)
            else:
                chunks[-1].extend(pending); pending = []; chunks[-1].append(line)
        else:
            pending.append(line)
    return [parse_interface("".join(c)) for c in chunks]


# ------------------------------------------------------------------ formatting


def format_type(t: TypeExpr) -> str:
    match t:
        case PrimitiveType(kind):
            return kind.value
        case NamedTypeRef(name):
            return name
        case NullableType(inner):
            return "?" + format_type(inner)
        case ArrayType(elem):
            return "[]" + format_type(elem)
        case MapType(value):
            return "[string]" + format_type(value)
        case StructType(fields):
            return "(" + ", ".join(f"{f.name}: {format_type(f.type)}" for f in fields) + ")"
        case EnumType(values):
            return "(" + ", ".join(v.name for v in values) + ")"
    raise TypeError(t)


def _doc_lines(doc: tuple[str, ...], indent: str = "") -> list[str]:
    return [f"{indent}# {line}" if line else f"{indent}#" for line in doc]


def _format_body(body: StructType | EnumType, indent: str = "\t") -> str:
    """Multi-line rendering of a struct or enum, one entry per line with its docs (systemd style)."""
    items = body.fields if isinstance(body, StructType) else body.values
    if not items:
        return "()"
    lines: list[str] = ["("]
    for n, item in enumerate(items):
        lines += _doc_lines(item.doc, indent)
        if item.experimental:
            lines.append(f"{indent}# {EXPERIMENTAL_MARKER}")
        entry = f"{item.name}: {format_type(item.type)}" if isinstance(item, Field) else item.name
        lines.append(f"{indent}{entry}" + ("," if n < len(items) - 1 else ""))
    lines.append(")")
    return "\n".join(lines)


def format_interface(iface: Interface) -> str:
    out: list[str] = _doc_lines(iface.doc)
    if iface.experimental:
        out.append(f"# {EXPERIMENTAL_MARKER}")
    out.append(f"interface {iface.name}")
    for m in iface.members:
        out.append("")
        out += _doc_lines(m.doc)
        match m:
            case TypeDef():
                if m.experimental:
                    out.append(f"# {EXPERIMENTAL_MARKER}")
                out.append(f"type {m.name}{_format_body(m.type)}")
            case Method():
                for marker, attr in FLAG_MARKERS.items():
                    if getattr(m, attr):
                        out.append(f"# {marker}")
                if m.experimental:
                    out.append(f"# {EXPERIMENTAL_MARKER}")
                out.append(f"method {m.name}{_format_body(m.input)} -> {_format_body(m.output)}")
            case Error():
                if m.experimental:
                    out.append(f"# {EXPERIMENTAL_MARKER}")
                out.append(f"error {m.name}{_format_body(m.parameters)}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------- CLI self-test

if __name__ == "__main__":
    import sys
    from pathlib import Path

    failures = 0
    for path in map(Path, sys.argv[1:]):
        text = path.read_text(encoding="utf-8")
        try:
            iface = parse_interface(text)
            again = parse_interface(format_interface(iface))
            rt = "roundtrip OK" if again == iface else "ROUNDTRIP MISMATCH"
            if again != iface:
                failures += 1
            n_methods = sum(isinstance(m, Method) for m in iface.members)
            n_types = sum(isinstance(m, TypeDef) for m in iface.members)
            n_errors = sum(isinstance(m, Error) for m in iface.members)
            more = sum(isinstance(m, Method) and (m.supports_more or m.requires_more) for m in iface.members)
            print(f"{path.name}: {iface.name}: {n_types} types, {n_methods} methods ({more} with more), {n_errors} errors; {rt}")
        except VarlinkSyntaxError as e:
            failures += 1
            print(f"{path.name}: PARSE ERROR {e}")
    sys.exit(1 if failures else 0)
