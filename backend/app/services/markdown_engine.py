from __future__ import annotations

from markdown_it import MarkdownIt
from mdit_py_plugins.container import container_plugin
import re


def _build_parser() -> MarkdownIt:
    # html=True is required so component-rendered HTML blocks pass through.
    md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
    md.enable("table")
    md.enable("strikethrough")

    # Enable ::: containers. Custom component fence expansion happens in renderer,
    # but this plugin keeps parser behavior robust for generic container syntax.
    md.use(container_plugin, "component")
    return md


_PARSER = _build_parser()


def render_markdown(markdown_text: str) -> str:
    if not markdown_text:
        return ""
    return _PARSER.render(markdown_text)


def analyze_markdown(markdown_text: str) -> dict:
    """Return parser-level metadata to help users understand rendered structure."""
    if not markdown_text:
        return {
            "block_outline": [],
            "token_types": [],
            "inline_tags": [],
        }

    tokens = _PARSER.parse(markdown_text)
    block_outline = []
    token_types = []
    inline_tags = set()

    for token in tokens:
        token_types.append(token.type)
        if token.type.endswith("_open"):
            level = token.level
            block_outline.append({
                "type": token.type.replace("_open", ""),
                "tag": token.tag,
                "level": level,
            })
        if token.type == "inline" and token.content:
            # Quick inline signal for link/code/strong emphasis symbols from raw text.
            if "[" in token.content and "](" in token.content:
                inline_tags.add("a")
            if "`" in token.content:
                inline_tags.add("code")
            if re.search(r"(\*\*|__)", token.content):
                inline_tags.add("strong")
            if re.search(r"(\*|_)", token.content):
                inline_tags.add("em")

    return {
        "block_outline": block_outline,
        "token_types": token_types,
        "inline_tags": sorted(inline_tags),
    }
