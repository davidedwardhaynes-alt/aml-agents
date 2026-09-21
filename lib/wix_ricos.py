"""Markdown to Wix Ricos rich content, for TrustSphere blog drafts.

A faithful port of `.trustsphere-ricos-builder.js` v2, which was itself
verified by reading back a live draft on 3 September 2026. Two quirks in
that file are load-bearing and are preserved here exactly:

  * Each bullet is its own single-item BULLETED_LIST node with a spacer
    paragraph between. Grouping bullets into one multi-item list renders
    wrong.
  * Node-level `style.paddingTop` / `paddingBottom` are rejected by Wix
    Blog. Never emit them.

Deliberately not supported, because the JS builder does not support them
and inventing node shapes that have not been verified against a live
draft is how you get silently mangled posts: inline links, bold body
text, block quotes, tables, code blocks and ordered lists. Run the
output through `apac_evening.validate_blog_markdown` before calling this
and those cases are caught in advance.
"""

from __future__ import annotations

import random
import string
from typing import Any

_ID_ALPHABET = string.ascii_lowercase + string.digits


class RicosError(ValueError):
    """Raised when the markdown cannot be represented in Ricos."""


def _make_id_factory():
    """Node IDs in the shape the JS builder produced: 'n' + counter + noise."""
    counter = {"n": 0}

    def nid() -> str:
        counter["n"] += 1
        noise = "".join(random.choice(_ID_ALPHABET) for _ in range(7))
        return f"n{counter['n']}{noise}"

    return nid


def _text_node(text: str, decorations: list[dict] | None = None) -> dict:
    return {
        "type": "TEXT",
        "id": "",
        "nodes": [],
        "textData": {"text": text, "decorations": decorations or []},
    }


def _paragraph(nid, children: list[dict] | None = None) -> dict:
    return {
        "type": "PARAGRAPH",
        "id": nid(),
        "nodes": children or [],
        "paragraphData": {
            "textStyle": {"textAlignment": "AUTO", "lineHeight": "1.9"}
        },
    }


def _heading(nid, text: str, level: int) -> dict:
    return {
        "type": "HEADING",
        "id": nid(),
        "nodes": [_text_node(text, [{"type": "BOLD", "fontWeightValue": 700}])],
        "headingData": {
            "level": level,
            "textStyle": {"textAlignment": "AUTO", "lineHeight": "1.5"},
        },
    }


def _bullet(nid, text: str) -> dict:
    return {
        "type": "BULLETED_LIST",
        "id": nid(),
        "nodes": [{
            "type": "LIST_ITEM",
            "id": nid(),
            "nodes": [_paragraph(nid, [_text_node(text)])],
        }],
    }


def _parse_blocks(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Split markdown into (title, [(kind, text), ...])."""
    title = ""
    blocks: list[tuple[str, str]] = []

    for raw in markdown.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
        elif line.startswith("- "):
            blocks.append(("li", line[2:].strip()))
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            blocks.append(("i", line[1:-1].strip()))
        else:
            blocks.append(("p", line))

    return title, blocks


def _excerpt(title: str, blocks: list[tuple[str, str]]) -> str:
    """First body paragraph, trimmed to 150 chars on a word boundary."""
    body = next((t for k, t in blocks if k == "p"), title)
    if len(body) > 150:
        body = body[:150].rsplit(" ", 1)[0]
    return body.rstrip(".,;:") + "..."


def build_draft(
    markdown: str,
    *,
    publish: bool = False,
    member_id: str | None = None,
) -> dict[str, Any]:
    """Build the POST body for /blog/v3/draft-posts from markdown.

    Defaults to `publish=False`. Publishing a post to a live public site
    is the author's call, not this function's — the daily run drafts and
    stops.
    """
    title, blocks = _parse_blocks(markdown)
    if not title:
        raise RicosError("no '# ' title line found in the markdown")
    if not blocks:
        raise RicosError("markdown has a title but no body")

    nid = _make_id_factory()
    nodes: list[dict] = []

    for i, (kind, text) in enumerate(blocks):
        # Two spacers before a heading, as the JS builder emits — but not
        # when the heading is the very first block.
        if kind in ("h2", "h3") and nodes:
            nodes.append(_paragraph(nid))
            nodes.append(_paragraph(nid))

        if kind == "h2":
            nodes.append(_heading(nid, text, 2))
        elif kind == "h3":
            nodes.append(_heading(nid, text, 3))
        elif kind == "i":
            nodes.append(_paragraph(
                nid, [_text_node(text, [{"type": "ITALIC", "italicData": True}])]
            ))
        elif kind == "li":
            nodes.append(_bullet(nid, text))
        else:
            nodes.append(_paragraph(nid, [_text_node(text)]))

        if i < len(blocks) - 1:
            nodes.append(_paragraph(nid))

    draft: dict[str, Any] = {
        "title": title,
        "excerpt": _excerpt(title, blocks),
        "richContent": {"nodes": nodes},
    }
    if member_id:
        draft["memberId"] = member_id

    return {"draftPost": draft, "publish": publish}
