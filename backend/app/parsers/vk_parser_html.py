from __future__ import annotations

import codecs
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser


__all__ = ["_Element", "_classes", "_element_text", "_elements", "_parse_document"]


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    children: list[_Element | str] = field(default_factory=list)


class _DocumentParser(HTMLParser):
    _VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = _Element(
            tag,
            {key: value or "" for key, value in attrs},
        )
        self.stack[-1].children.append(element)
        if tag not in self._VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.stack[-1].children.append(
            _Element(tag, {key: value or "" for key, value in attrs})
        )

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self.stack[-1].tag not in {"script", "style"}:
            self.stack[-1].children.append(data)


def _elements(root: _Element) -> Iterator[_Element]:
    pending = [root]
    while pending:
        element = pending.pop()
        yield element
        pending.extend(
            child
            for child in reversed(element.children)
            if isinstance(child, _Element)
        )


def _classes(element: _Element) -> set[str]:
    return set(element.attrs.get("class", "").split())


def _element_text(
    element: _Element,
    *,
    excluded_classes: set[str] | None = None,
) -> str:
    excluded = excluded_classes or set()
    pieces: list[str] = []
    pending: list[_Element | str] = [element]
    while pending:
        child = pending.pop()
        if isinstance(child, str):
            pieces.append(child)
            continue
        if _classes(child) & excluded:
            continue
        if child.tag == "br":
            pieces.append("\n")
        else:
            pending.extend(reversed(child.children))

    lines = [
        re.sub(r"[^\S\n]+", " ", line).strip()
        for line in "".join(pieces).replace("\r", "\n").split("\n")
    ]
    return "\n".join(line for line in lines if line)


def _decode_html(raw_html: bytes) -> str:
    declaration = re.search(
        rb"<meta\b[^>]*\bcharset\s*=\s*[\"']?\s*([A-Za-z0-9._-]+)",
        raw_html[:8192],
        re.IGNORECASE,
    )
    encoding = declaration.group(1).decode("ascii") if declaration else "utf-8"
    try:
        codec = codecs.lookup(encoding).name
    except LookupError as exc:
        raise ValueError("VK export declares an unsupported HTML encoding.") from exc
    return raw_html.decode(codec, errors="replace")


def _parse_document(raw_html: bytes) -> _Element:
    parser = _DocumentParser()
    parser.feed(_decode_html(raw_html))
    parser.close()
    return parser.root
