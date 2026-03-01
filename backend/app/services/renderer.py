from typing import Any, Optional
import json
import re
import shlex
from html import escape

from jinja2 import BaseLoader, select_autoescape, sandbox

from app.models import Component, Theme
from app.extensions import db
from app.services.markdown_engine import render_markdown

ENCLOSED_SHORTCODE_RE = re.compile(
    r"\{\{<\s*([a-zA-Z][\w-]*)\s*([^>]*)>\}\}(.*?)\{\{<\s*/\1\s*>\}\}",
    re.DOTALL,
)
SELF_SHORTCODE_RE = re.compile(r"\{\{<\s*([a-zA-Z][\w-]*)\s*([^>]*)/?>\}\}")
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
RESERVED_THEME_STYLES_KEY = "__element_styles"
jinja_env = sandbox.SandboxedEnvironment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html", "xml"]),
)
def _load_component(name: str, user_id: Optional[int] = None) -> Optional[Component]:
    component = Component.query.filter(
        Component.name == name,
        Component.is_active == True,
        db.or_(
            Component.user_id == user_id,
            Component.is_builtin == True
        )
    ).first()

    return component


def _resolve_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        return ""
    return current


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _interpolate_template(template: str, props: dict[str, Any]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        value = _resolve_path(props, key)
        return _stringify_value(value)

    return PLACEHOLDER_RE.sub(repl, template)


def _coerce_attr_value(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    if re.fullmatch(r"-?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            pass
    if value.startswith("{") or value.startswith("["):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _parse_shortcode_attrs(raw: str) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    raw = raw.strip()
    if not raw:
        return attrs

    try:
        tokens = shlex.split(raw)
    except ValueError:
        return attrs

    for token in tokens:
        if "=" not in token:
            attrs[token] = True
            continue
        key, value = token.split("=", 1)
        attrs[key] = _coerce_attr_value(value)

    return attrs


def _render_table_shortcode(attrs: dict[str, Any], inner_markdown: str) -> str:
    headers = attrs.get("headers")
    rows = attrs.get("rows")
    css_class = str(attrs.get("class", "")).strip()
    style = str(attrs.get("style", "")).strip()

    if isinstance(headers, str):
        headers = [h.strip() for h in headers.split("|") if h.strip()]
    if isinstance(rows, str):
        parsed_rows: list[list[str]] = []
        for row in rows.split(";"):
            cells = [cell.strip() for cell in row.split("|")]
            if any(cells):
                parsed_rows.append(cells)
        rows = parsed_rows

    if isinstance(headers, list) and isinstance(rows, list):
        head_html = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
        body_items = []
        for row in rows:
            if not isinstance(row, list):
                continue
            row_cells = "".join(f"<td>{escape(str(c))}</td>" for c in row)
            body_items.append(f"<tr>{row_cells}</tr>")
        body_html = "".join(body_items)

        class_attr = f' class="dsl-table {css_class}"' if css_class else ' class="dsl-table"'
        style_attr = f' style="{style}"' if style else ""
        return (
            f'<div class="dsl-table-wrapper"><table{class_attr}{style_attr}>'
            f"<thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>"
        )

    return f'<div class="dsl-table-wrapper">{render_markdown(inner_markdown)}</div>'


def _render_row_shortcode(attrs: dict[str, Any], inner_markdown: str) -> str:
    css_class = str(attrs.get("class", "")).strip()
    style = str(attrs.get("style", "")).strip()
    columns = attrs.get("columns")
    gap = attrs.get("gap")

    dynamic_style_parts = []
    if isinstance(columns, int) and columns > 0:
        dynamic_style_parts.append(f"grid-template-columns: repeat({columns}, minmax(0, 1fr));")
    if isinstance(gap, (int, float, str)) and str(gap).strip():
        dynamic_style_parts.append(f"gap: {gap};")
    if style:
        dynamic_style_parts.append(style)
    style_attr = f' style="{" ".join(dynamic_style_parts)}"' if dynamic_style_parts else ""

    class_name = "dsl-row"
    if css_class:
        class_name += f" {css_class}"

    return f'<div class="{class_name}"{style_attr}>{render_markdown(inner_markdown)}</div>'


def _render_column_shortcode(attrs: dict[str, Any], inner_markdown: str) -> str:
    css_class = str(attrs.get("class", "")).strip()
    style = str(attrs.get("style", "")).strip()
    span = attrs.get("span")

    dynamic_style_parts = []
    if isinstance(span, int) and span > 0:
        dynamic_style_parts.append(f"grid-column: span {span} / span {span};")
    if style:
        dynamic_style_parts.append(style)
    style_attr = f' style="{" ".join(dynamic_style_parts)}"' if dynamic_style_parts else ""

    class_name = "dsl-column"
    if css_class:
        class_name += f" {css_class}"

    return f'<div class="{class_name}"{style_attr}>{render_markdown(inner_markdown)}</div>'


def render_component(name: str, props: dict, user_id: Optional[int] = None, inner_markdown: str = "") -> str:
    """Render a custom component from markdown template + props."""
    component = _load_component(name, user_id)
    if not component:
        return f'<div class="error">Component "{escape(name)}" not found</div>'

    try:
        merged_props = dict(props or {})
        if inner_markdown.strip():
            merged_props.setdefault("content", render_markdown(inner_markdown))
            merged_props.setdefault("slot_html", render_markdown(inner_markdown))
            merged_props.setdefault("slot_markdown", inner_markdown)

        props_json = merged_props.pop("props_json", None) or merged_props.pop("props", None)
        if isinstance(props_json, str):
            try:
                parsed = json.loads(props_json)
                if isinstance(parsed, dict):
                    merged_props.update(parsed)
            except json.JSONDecodeError:
                pass
        elif isinstance(props_json, dict):
            merged_props.update(props_json)

        interpolated = _interpolate_template(component.template, merged_props)
        if "{%" in component.template or "{#" in component.template:
            jinja_template = jinja_env.from_string(component.template)
            interpolated = jinja_template.render(**merged_props)
        return render_markdown(interpolated)
    except Exception as e:
        return f'<div class="error">Error rendering component: {escape(str(e))}</div>'


def _render_shortcode(name: str, attrs: dict[str, Any], inner_markdown: str, user_id: Optional[int] = None) -> str:
    short_name = name.lower()
    if short_name == "row":
        return _render_row_shortcode(attrs, inner_markdown)
    if short_name == "column":
        return _render_column_shortcode(attrs, inner_markdown)
    if short_name == "table":
        return _render_table_shortcode(attrs, inner_markdown)
    return render_component(name, attrs, user_id, inner_markdown)


def _expand_shortcodes(markdown_source: str, user_id: Optional[int] = None) -> str:
    text = markdown_source

    while True:
        replaced = False

        def replace_enclosed(match: re.Match[str]) -> str:
            nonlocal replaced
            replaced = True
            name = match.group(1)
            raw_attrs = match.group(2) or ""
            inner = match.group(3) or ""
            attrs = _parse_shortcode_attrs(raw_attrs)
            expanded_inner = _expand_shortcodes(inner, user_id)
            return _render_shortcode(name, attrs, expanded_inner, user_id)

        text = ENCLOSED_SHORTCODE_RE.sub(replace_enclosed, text)
        if not replaced:
            break

    def replace_self(match: re.Match[str]) -> str:
        name = match.group(1)
        attrs = _parse_shortcode_attrs(match.group(2) or "")
        return _render_shortcode(name, attrs, "", user_id)

    return SELF_SHORTCODE_RE.sub(replace_self, text)


def _block_to_markdown(block: dict) -> str:
    block_type = block.get("type")
    if block_type == "markdown":
        return str(block.get("content", ""))

    name = block.get("name", "")
    if block_type == "component" and name:
        props = block.get("props", {}) or {}
        if isinstance(props, dict) and props:
            props_json = json.dumps(props, ensure_ascii=False).replace("'", "\\'")
            return f"{{{{< {name} props_json='{props_json}' >}}}}"
        return f"{{{{< {name} >}}}}"

    if isinstance(block_type, str) and block_type:
        return f"{{{{< {block_type} >}}}}"
    return ""


def _normalize_document_content(content: dict) -> tuple[str, Optional[int]]:
    if not isinstance(content, dict):
        return "", None

    theme_id = content.get("theme_id")
    markdown_source = content.get("markdown")
    if isinstance(markdown_source, str):
        return markdown_source, theme_id

    blocks = content.get("blocks", [])
    if not isinstance(blocks, list):
        return "", theme_id
    converted = [_block_to_markdown(block) for block in blocks if isinstance(block, dict)]
    return "\n\n".join(part for part in converted if part.strip()), theme_id


def _build_theme_css(theme_id: Optional[int], user_id: Optional[int] = None) -> str:
    if not theme_id:
        return ""

    theme = Theme.query.filter(
        Theme.id == theme_id,
        db.or_(
            Theme.user_id == user_id,
            Theme.is_builtin == True
        )
    ).first()

    if not theme:
        return ""

    variables = theme.variables or {}
    element_styles = variables.get(RESERVED_THEME_STYLES_KEY, {})

    css_vars = []
    for key, value in variables.items():
        if key == RESERVED_THEME_STYLES_KEY:
            continue
        if isinstance(value, (dict, list)):
            continue
        css_vars.append(f"  --{key}: {value};")

    style_blocks = []
    if isinstance(element_styles, dict):
        for selector, declarations in element_styles.items():
            if not isinstance(selector, str) or not selector.strip():
                continue
            if isinstance(declarations, dict):
                css_decl = " ".join(
                    f"{prop}: {value};"
                    for prop, value in declarations.items()
                    if isinstance(prop, str)
                )
            elif isinstance(declarations, str):
                css_decl = declarations.strip()
            else:
                continue
            if not css_decl:
                continue
            scoped_selector = selector.strip()
            if not scoped_selector.startswith(".docsly-content"):
                scoped_selector = f".docsly-content {scoped_selector}"
            style_blocks.append(f"{scoped_selector} {{ {css_decl} }}")

    vars_css = f":root {{\n{chr(10).join(css_vars)}\n}}" if css_vars else ""
    styles_css = "\n".join(style_blocks)
    return f"{vars_css}\n{styles_css}".strip()


def render_block(block: dict, user_id: Optional[int] = None) -> str:
    """Render a single document block."""
    block_type = block.get("type")

    if block_type == "markdown":
        return render_markdown(block.get("content", ""))

    if block_type == "component":
        name = block.get("name", "")
        props = block.get("props", {})
        return render_component(name, props, user_id)

    # Try to render block_type as a component name directly
    # This allows using {"type": "heading", "props": {...}} instead of
    # {"type": "component", "name": "heading", "props": {...}}
    props = block.get("props", {})
    result = render_component(block_type, props, user_id)
    if 'not found' not in result:
        return result

    return f'<div class="error">Unknown block type: {block_type}</div>'


def get_theme_css(theme_id: Optional[int], user_id: Optional[int] = None) -> str:
    """Backward-compatible wrapper for theme CSS generation."""
    return _build_theme_css(theme_id, user_id)


def render_document(content: dict, user_id: Optional[int] = None) -> str:
    """Render full markdown document to HTML (with shortcode support)."""
    markdown_source, theme_id = _normalize_document_content(content or {})
    expanded_markdown = _expand_shortcodes(markdown_source, user_id)
    rendered_html = render_markdown(expanded_markdown)
    theme_css = _build_theme_css(theme_id, user_id)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        {theme_css}
        body {{
            font-family: var(--font-family, system-ui, sans-serif);
            line-height: var(--line-height, 1.6);
            color: var(--text-color, #1a1a1a);
            background: var(--background-color, #ffffff);
            max-width: var(--max-width, 800px);
            margin: 0 auto;
            padding: 2rem;
        }}
        .error {{
            color: #dc2626;
            background: #fee2e2;
            padding: 1rem;
            border-radius: 0.25rem;
        }}
        .docsly-content .dsl-row {{
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: var(--dsl-row-gap, 1rem);
            margin: 1rem 0;
        }}
        .docsly-content .dsl-column {{
            grid-column: span 12 / span 12;
        }}
        .docsly-content .dsl-table-wrapper {{
            overflow-x: auto;
            margin: 1rem 0;
        }}
        .docsly-content .dsl-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .docsly-content .dsl-table th,
        .docsly-content .dsl-table td {{
            border: 1px solid #e5e7eb;
            padding: 0.5rem 0.75rem;
            text-align: left;
        }}
        .docsly-content .dsl-table th {{
            background: #f8fafc;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <main class="docsly-content">
        {rendered_html}
    </main>
</body>
</html>"""

    return html
