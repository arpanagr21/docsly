from __future__ import annotations

import re
from html import escape


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
HR_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
UNORDERED_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
ORDERED_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)\s*([\w-]+)?\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
STRONG_RE = re.compile(r"(\*\*|__)(.+?)\1")
EM_RE = re.compile(r"(\*|_)([^*_]+?)\1")
STRIKE_RE = re.compile(r"~~(.+?)~~")
CODE_SPAN_RE = re.compile(r"`([^`]+)`")
HTML_BLOCK_START_RE = re.compile(r"^\s*<([a-zA-Z][a-zA-Z0-9-]*)(\s|>|/>)")


def _is_table_header(line: str, next_line: str) -> bool:
    return ("|" in line) and bool(TABLE_SEPARATOR_RE.match(next_line.strip()))


def _split_table_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def _render_inline(text: str) -> str:
    text = escape(text)

    code_spans: list[str] = []

    def replace_code_span(match: re.Match[str]) -> str:
        code_spans.append(f"<code>{escape(match.group(1))}</code>")
        return f"__CODE_SPAN_{len(code_spans) - 1}__"

    text = CODE_SPAN_RE.sub(replace_code_span, text)
    text = STRIKE_RE.sub(r"<del>\1</del>", text)
    text = STRONG_RE.sub(r"<strong>\2</strong>", text)
    text = EM_RE.sub(r"<em>\2</em>", text)
    text = LINK_RE.sub(lambda m: f'<a href="{escape(m.group(2), quote=True)}">{m.group(1)}</a>', text)

    for idx, html_code in enumerate(code_spans):
        text = text.replace(f"__CODE_SPAN_{idx}__", html_code)

    return text


def render_markdown(markdown_text: str) -> str:
    """Docsly custom markdown parser (block + inline + table support)."""
    if not markdown_text:
        return ""

    lines = markdown_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    html_parts: list[str] = []
    i = 0

    def consume_paragraph(start_idx: int) -> tuple[str, int]:
        para_lines: list[str] = []
        idx = start_idx
        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()
            if not stripped:
                break
            if (
                HEADING_RE.match(stripped)
                or HR_RE.match(stripped)
                or UNORDERED_RE.match(stripped)
                or ORDERED_RE.match(stripped)
                or BLOCKQUOTE_RE.match(stripped)
                or FENCE_RE.match(stripped)
                or HTML_BLOCK_START_RE.match(stripped)
            ):
                break
            if idx + 1 < len(lines) and _is_table_header(line, lines[idx + 1]):
                break
            para_lines.append(line.strip())
            idx += 1
        paragraph = " ".join(para_lines)
        return f"<p>{_render_inline(paragraph)}</p>", idx

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        fence_match = FENCE_RE.match(stripped)
        if fence_match:
            fence = fence_match.group(1)
            language = (fence_match.group(2) or "").strip()
            i += 1
            code_lines: list[str] = []
            while i < len(lines):
                if re.match(rf"^\s*{re.escape(fence)}\s*$", lines[i].strip()):
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            lang_class = f' class="language-{escape(language, quote=True)}"' if language else ""
            html_parts.append(f"<pre><code{lang_class}>{escape(chr(10).join(code_lines))}</code></pre>")
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            content = _render_inline(heading_match.group(2).strip())
            html_parts.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue

        if HR_RE.match(stripped):
            html_parts.append("<hr />")
            i += 1
            continue

        if i + 1 < len(lines) and _is_table_header(line, lines[i + 1]):
            headers = _split_table_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line or "|" not in row_line:
                    break
                rows.append(_split_table_row(row_line))
                i += 1

            head_html = "".join(f"<th>{_render_inline(h)}</th>" for h in headers)
            body_html = []
            for row in rows:
                cells = "".join(f"<td>{_render_inline(cell)}</td>" for cell in row)
                body_html.append(f"<tr>{cells}</tr>")
            html_parts.append(
                "<table><thead><tr>"
                + head_html
                + "</tr></thead><tbody>"
                + "".join(body_html)
                + "</tbody></table>"
            )
            continue

        if HTML_BLOCK_START_RE.match(stripped):
            html_block_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip():
                html_block_lines.append(lines[i])
                i += 1
            html_parts.append("\n".join(html_block_lines))
            continue

        if BLOCKQUOTE_RE.match(stripped):
            quote_lines: list[str] = []
            while i < len(lines):
                match = BLOCKQUOTE_RE.match(lines[i].strip())
                if not match:
                    break
                quote_lines.append(match.group(1))
                i += 1
            html_parts.append(f"<blockquote>{render_markdown(chr(10).join(quote_lines))}</blockquote>")
            continue

        if UNORDERED_RE.match(stripped) or ORDERED_RE.match(stripped):
            ordered = bool(ORDERED_RE.match(stripped))
            tag = "ol" if ordered else "ul"
            items: list[str] = []
            while i < len(lines):
                current = lines[i].strip()
                match = ORDERED_RE.match(current) if ordered else UNORDERED_RE.match(current)
                if not match:
                    break
                items.append(f"<li>{_render_inline(match.group(1).strip())}</li>")
                i += 1
            html_parts.append(f"<{tag}>{''.join(items)}</{tag}>")
            continue

        paragraph_html, next_i = consume_paragraph(i)
        if next_i == i:
            html_parts.append(f"<p>{_render_inline(stripped)}</p>")
            i += 1
        else:
            html_parts.append(paragraph_html)
            i = next_i

    return "\n".join(html_parts)
