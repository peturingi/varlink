"""Serialise a parsed Varlink interface (varlink_idl AST) as an XMI instance of the
dk.ingi.varlink Ecore metamodel (root package https://ingi.dk/varlink).

Independent of the synthesizer's converter: this emitter is driven by varlink_idl.py,
so agreement between the two converters on the whole corpus cross-checks both parsers.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works under python -I too

from varlink_idl import (ArrayType, EnumType, EnumValue, Error, Field, Interface, MapType, Method,
                         NamedTypeRef, NullableType, PrimitiveType, StructType, TypeDef, TypeExpr,
                         parse_interface)

NS = "https://ingi.dk/varlink"


def _attrs(**kw: object) -> str:
    def lit(v: object) -> str:
        return "true" if v is True else str(v)  # EMF's canonical boolean literal
    return "".join(f" {k}={quoteattr(lit(v))}" for k, v in kw.items() if v is not None and v is not False)


def _docs(doc: tuple[str, ...], ind: str) -> list[str]:
    return [f"{ind}<documentation>{escape(line)}</documentation>" for line in doc]


def _type(tag: str, t: TypeExpr, ind: str, nullable: bool = False) -> list[str]:
    if isinstance(t, NullableType):
        return _type(tag, t.inner, ind, nullable=True)
    n = {"nullable": "true"} if nullable else {}
    match t:
        case PrimitiveType(kind):
            return [f"{ind}<{tag}{_attrs(**{'xsi:type': 'varlink:BuiltinType', 'kind': kind.value}, **n)}/>"]
        case NamedTypeRef(name):
            fragment = "//@members[name='" + name + "']"  # name-keyed URI fragment (Interface.members has eKeys=name)
            return [f"{ind}<{tag}{_attrs(**{'xsi:type': 'varlink:NamedTypeReference', 'typeName': name, 'definition': fragment}, **n)}/>"]
        case ArrayType(elem):
            return [f"{ind}<{tag}{_attrs(**{'xsi:type': 'varlink:ArrayType'}, **n)}>", *_type("elementType", elem, ind + "  "), f"{ind}</{tag}>"]
        case MapType(value):
            return [f"{ind}<{tag}{_attrs(**{'xsi:type': 'varlink:MapType'}, **n)}>", *_type("valueType", value, ind + "  "), f"{ind}</{tag}>"]
        case StructType(fields):
            if not fields:
                return [f"{ind}<{tag}{_attrs(**{'xsi:type': 'varlink:StructType'}, **n)}/>"]
            return [f"{ind}<{tag}{_attrs(**{'xsi:type': 'varlink:StructType'}, **n)}>", *_fields(fields, ind + "  "), f"{ind}</{tag}>"]
        case EnumType(values):
            return [f"{ind}<{tag}{_attrs(**{'xsi:type': 'varlink:EnumType'}, **n)}>", *_values(values, ind + "  "), f"{ind}</{tag}>"]
    raise TypeError(t)


def _fields(fields: tuple[Field, ...], ind: str) -> list[str]:
    out: list[str] = []
    for f in fields:
        out.append(f"{ind}<fields{_attrs(name=f.name, experimental=f.experimental)}>")
        out += _docs(f.doc, ind + "  ")
        out += _type("type", f.type, ind + "  ")
        out.append(f"{ind}</fields>")
    return out


def _values(values: tuple[EnumValue, ...], ind: str) -> list[str]:
    out: list[str] = []
    for v in values:
        if v.doc:
            out.append(f"{ind}<values{_attrs(name=v.name, experimental=v.experimental)}>")
            out += _docs(v.doc, ind + "  ")
            out.append(f"{ind}</values>")
        else:
            out.append(f"{ind}<values{_attrs(name=v.name, experimental=v.experimental)}/>")
    return out


def _struct(tag: str, s: StructType, ind: str) -> list[str]:
    if not s.fields:
        return [f"{ind}<{tag}/>"]
    return [f"{ind}<{tag}>", *_fields(s.fields, ind + "  "), f"{ind}</{tag}>"]


def _support(supports: bool, requires: bool) -> str | None:
    return "required" if requires else "supported" if supports else None


def to_xmi(iface: Interface) -> str:
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           f'<varlink:Interface xmi:version="2.0" xmlns:xmi="http://www.omg.org/XMI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
           f' xmlns:varlink="{NS}"{_attrs(name=iface.name, experimental=iface.experimental)}>']
    out += _docs(iface.doc, "  ")
    for m in iface.members:
        ind = "  "
        match m:
            case TypeDef(name, body):
                kind = "StructDefinition" if isinstance(body, StructType) else "EnumDefinition"
                out.append(f'{ind}<members{_attrs(**{"xsi:type": f"varlink:{kind}"}, name=name, experimental=m.experimental)}>')
                out += _docs(m.doc, ind + "  ")
                if isinstance(body, StructType):
                    out += _struct("body", body, ind + "  ")
                else:
                    out.append(f"{ind}  <body>")
                    out += _values(body.values, ind + "    ")
                    out.append(f"{ind}  </body>")
            case Method():
                out.append(f'{ind}<members{_attrs(**{"xsi:type": "varlink:Method"}, name=m.name, experimental=m.experimental, moreSupport=_support(m.supports_more, m.requires_more), upgradeSupport=_support(m.supports_upgrade, m.requires_upgrade))}>')
                out += _docs(m.doc, ind + "  ")
                out += _struct("input", m.input, ind + "  ")
                out += _struct("output", m.output, ind + "  ")
            case Error():
                out.append(f'{ind}<members{_attrs(**{"xsi:type": "varlink:ErrorDefinition"}, name=m.name, experimental=m.experimental)}>')
                out += _docs(m.doc, ind + "  ")
                out += _struct("parameters", m.parameters, ind + "  ")
        out.append(f"{ind}</members>")
    out.append("</varlink:Interface>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.write_text(to_xmi(parse_interface(src.read_text(encoding="utf-8"))), encoding="utf-8")
