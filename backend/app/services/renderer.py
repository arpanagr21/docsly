from typing import Any, Optional
import json
import re
import shlex
from html import escape

from jinja2 import BaseLoader, select_autoescape, sandbox

from app.models import Component, Theme
from app.extensions import db
from app.services.component_registry import get_registered_component
from app.services.markdown_engine import analyze_markdown, render_markdown
from app.services.style_engine import compose_component_css

ENCLOSED_SHORTCODE_RE = re.compile(
    r"\{\{<\s*([a-zA-Z][\w-]*)\s*([^>]*)>\}\}(.*?)\{\{<\s*/\1\s*>\}\}",
    re.DOTALL,
)
SELF_SHORTCODE_RE = re.compile(r"\{\{<\s*([a-zA-Z][\w-]*)\s*([^>]*)/?>\}\}")
PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
HTML_TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)\b")
RESERVED_THEME_STYLES_KEY = "__element_styles"
RESERVED_THEME_COMPONENT_STYLES_KEY = "__component_styles"
COMPONENT_FENCE_START_RE = re.compile(r"^\s*:::\s*([a-zA-Z][\w-]*)\s*(.*)$")
SLOT_WRAPPER_RE = re.compile(
    r'<div\s+data-docsly-slot="([a-zA-Z][\w-]*)"\s*>(.*?)</div>',
    re.DOTALL,
)
MAX_COMPONENT_NESTING_DEPTH = 8
CORE_LAYOUT_COMPONENTS = {"row", "column", "table"}
jinja_env = sandbox.SandboxedEnvironment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html", "xml"]),
)
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
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]

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


def _parse_version(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise ValueError(f"Invalid component version: {value}")


def _parse_component_fence_props(lines: list[str]) -> tuple[dict[str, Any], str]:
    props: dict[str, Any] = {}
    content_lines: list[str] = []
    props_phase = True

    for raw_line in lines:
        line = raw_line.strip()
        if props_phase and not line:
            continue
        if props_phase and "=" in line and not line.startswith(":::"):
            key, value = line.split("=", 1)
            props[key.strip()] = _coerce_attr_value(value.strip())
            continue

        props_phase = False
        if not line:
            content_lines.append(raw_line)
            continue
        if line.startswith(":::"):
            content_lines.append(raw_line)
            continue
        content_lines.append(raw_line)

    return props, "\n".join(content_lines).strip()


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


def _render_component_from_template(component: Component, props: dict[str, Any], inner_markdown: str) -> str:
    """Component renderer contract: pure function from props+theme to HTML."""
    merged_props = dict(props or {})
    if inner_markdown.strip():
        slots: dict[str, str] = {}
        cleaned_markdown = inner_markdown
        for match in SLOT_WRAPPER_RE.finditer(inner_markdown):
            slot_name = match.group(1)
            slot_body = match.group(2) or ""
            slots[slot_name] = slots.get(slot_name, "") + slot_body
        cleaned_markdown = SLOT_WRAPPER_RE.sub("", cleaned_markdown).strip()

        if cleaned_markdown:
            slot_html = render_markdown(cleaned_markdown)
            merged_props.setdefault("content", slot_html)
            merged_props.setdefault("slot_html", slot_html)
            merged_props.setdefault("slot_markdown", cleaned_markdown)
            slots.setdefault("root", slot_html)

        for slot_name, slot_html in slots.items():
            merged_props.setdefault(f"slot_{slot_name}", slot_html)
        merged_props.setdefault("slots", slots)

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
    if any(marker in component.template for marker in ("{{", "{%", "{#")):
        jinja_template = jinja_env.from_string(component.template)
        interpolated = jinja_template.render(**merged_props)
    return render_markdown(interpolated)


def _render_component_with_styles(
    component_name: str,
    html_body: str,
    style_contract: dict[str, Any],
    default_styles: dict[str, Any],
    theme: dict[str, Any],
    variant: Optional[str],
) -> str:
    theme_component_styles = {}
    if isinstance(theme, dict):
        raw = theme.get(RESERVED_THEME_COMPONENT_STYLES_KEY, {})
        if isinstance(raw, dict):
            candidate = raw.get(component_name, {})
            if isinstance(candidate, dict):
                theme_component_styles = candidate

    css = compose_component_css(
        component_name=component_name,
        style_contract=style_contract or {},
        default_styles=default_styles or {},
        theme_styles=theme_component_styles,
        variant=variant,
    )
    safe_component_name = escape(component_name, quote=True)
    safe_variant = escape(variant or "", quote=True)
    wrapper_class = f'cmp cmp-{re.sub(r"[^a-zA-Z0-9_-]", "-", component_name).lower()}'
    style_tag = f"<style>{css}</style>" if css.strip() else ""
    return (
        f'{style_tag}<section class="{wrapper_class}" '
        f'data-component="{safe_component_name}" data-variant="{safe_variant}">{html_body}</section>'
    )


def render_component_template_preview(
    template: str,
    props: dict[str, Any],
    component_name: str = "preview-component",
    style_contract: Optional[dict[str, Any]] = None,
    default_styles: Optional[dict[str, Any]] = None,
    theme: Optional[dict[str, Any]] = None,
) -> str:
    """Render a component template preview without saving a component."""
    merged_props = dict(props or {})
    variant = merged_props.get("variant")
    if not isinstance(variant, str):
        variant = None
    rendered_markdown = _render_template_to_markdown(template or "", merged_props)
    html_body = render_markdown(rendered_markdown)
    return _render_component_with_styles(
        component_name=component_name,
        html_body=html_body,
        style_contract=style_contract or {},
        default_styles=default_styles or {},
        theme=theme or {},
        variant=variant,
    )


def _render_template_to_markdown(template: str, props: dict[str, Any]) -> str:
    interpolated = _interpolate_template(template or "", props or {})
    if any(marker in (template or "") for marker in ("{{", "{%", "{#")):
        jinja_template = jinja_env.from_string(template or "")
        return jinja_template.render(**(props or {}))
    return interpolated


def _extract_rendered_tags(html: str) -> list[str]:
    tags = {match.group(1).lower() for match in HTML_TAG_RE.finditer(html or "")}
    tags.discard("style")
    tags.discard("section")
    return sorted(tags)


def _collect_placeholder_insights(template: str, props: dict[str, Any]) -> dict[str, Any]:
    placeholders = sorted({match.group(1) for match in PLACEHOLDER_RE.finditer(template or "")})
    unresolved = []
    for key in placeholders:
        if _resolve_path(props, key) == "":
            unresolved.append(key)
    return {
        "placeholders": placeholders,
        "unresolved_placeholders": unresolved,
    }


def _collect_style_insights(style_contract: dict[str, Any], default_styles: dict[str, Any]) -> dict[str, Any]:
    contract_slots = style_contract.get("slots", []) if isinstance(style_contract, dict) else []
    contract_variants = style_contract.get("variants", []) if isinstance(style_contract, dict) else []
    declared_slots = list((default_styles.get("slots", {}) or {}).keys()) if isinstance(default_styles, dict) else []
    declared_variants = list((default_styles.get("variants", {}) or {}).keys()) if isinstance(default_styles, dict) else []

    contract_slot_set = {slot for slot in contract_slots if isinstance(slot, str)}
    contract_variant_set = {variant for variant in contract_variants if isinstance(variant, str)}
    declared_slot_set = {slot for slot in declared_slots if isinstance(slot, str)}
    declared_variant_set = {variant for variant in declared_variants if isinstance(variant, str)}

    return {
        "contract_slots": sorted(contract_slot_set),
        "declared_slots": sorted(declared_slot_set),
        "undeclared_slots": sorted(contract_slot_set - declared_slot_set),
        "extra_slots": sorted(declared_slot_set - contract_slot_set),
        "contract_variants": sorted(contract_variant_set),
        "declared_variants": sorted(declared_variant_set),
        "undeclared_variants": sorted(contract_variant_set - declared_variant_set),
        "extra_variants": sorted(declared_variant_set - contract_variant_set),
    }


def _collect_element_style_insights(default_styles: dict[str, Any], rendered_tags: list[str]) -> dict[str, Any]:
    elements = default_styles.get("elements", {}) if isinstance(default_styles, dict) else {}
    selectors = [selector for selector in elements.keys() if isinstance(selector, str)]
    selector_map: dict[str, set[str]] = {}
    for selector in selectors:
        for part in selector.split(","):
            target = part.strip().lower()
            if not target:
                continue
            selector_map.setdefault(target, set()).add(selector)

    styled_rendered_tags: list[str] = []
    unstyled_rendered_tags: list[str] = []
    for tag in rendered_tags:
        if tag in selector_map:
            styled_rendered_tags.append(tag)
        else:
            unstyled_rendered_tags.append(tag)

    return {
        "element_selectors": sorted(selectors),
        "styled_rendered_tags": sorted(styled_rendered_tags),
        "unstyled_rendered_tags": sorted(unstyled_rendered_tags),
    }


def render_component_template_preview_details(
    template: str,
    props: dict[str, Any],
    component_name: str = "preview-component",
    style_contract: Optional[dict[str, Any]] = None,
    default_styles: Optional[dict[str, Any]] = None,
    theme: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    rendered_markdown = _render_template_to_markdown(template or "", props or {})
    rendered = render_component_template_preview(
        template=template,
        props=props,
        component_name=component_name,
        style_contract=style_contract,
        default_styles=default_styles,
        theme=theme,
    )
    markdown_meta = analyze_markdown(rendered_markdown)
    placeholder_meta = _collect_placeholder_insights(template or "", props or {})
    style_meta = _collect_style_insights(style_contract or {}, default_styles or {})
    rendered_tags = _extract_rendered_tags(rendered)
    element_meta = _collect_element_style_insights(default_styles or {}, rendered_tags)
    return {
        "html": rendered,
        "meta": {
            "interpolated_markdown": rendered_markdown,
            "rendered_tags": rendered_tags,
            "markdown_outline": markdown_meta.get("block_outline", []),
            "token_types": markdown_meta.get("token_types", []),
            "inline_tags": markdown_meta.get("inline_tags", []),
            **placeholder_meta,
            **style_meta,
            **element_meta,
        },
    }


def render_component(
    name: str,
    props: dict,
    user_id: Optional[int] = None,
    inner_markdown: str = "",
    version: Optional[int] = None,
    theme: Optional[dict[str, Any]] = None,
    _render_depth: int = 0,
    _render_stack: Optional[tuple[str, ...]] = None,
) -> str:
    """Render a custom component by registry lookup (name, version)."""
    render_stack = _render_stack or tuple()
    component_key = (name or "").lower()
    if _render_depth > MAX_COMPONENT_NESTING_DEPTH:
        return (
            '<div class="error">'
            f'Component nesting exceeded max depth ({MAX_COMPONENT_NESTING_DEPTH}) while rendering "{escape(name)}"'
            "</div>"
        )
    if component_key and component_key not in CORE_LAYOUT_COMPONENTS and component_key in render_stack:
        cycle = " -> ".join([*render_stack, component_key])
        return (
            '<div class="error">'
            f'Circular component reference detected: {escape(cycle)}'
            "</div>"
        )

    try:
        registry_entry = get_registered_component(
            name=name,
            version=version,
            user_id=user_id,
            renderer_factory=lambda component: (
                lambda comp_props, comp_theme: _render_component_from_template(
                    component,
                    {
                        **(comp_props or {}),
                        "theme": comp_theme or {},
                    },
                    inner_markdown,
                )
            ),
        )
        merged_props = props or {}
        variant = merged_props.get("variant")
        if not isinstance(variant, str):
            variant = None
        html_body = registry_entry.renderer(merged_props, theme or {})
        return _render_component_with_styles(
            component_name=registry_entry.name,
            html_body=html_body,
            style_contract=registry_entry.style_contract,
            default_styles=registry_entry.default_styles,
            theme=theme or {},
            variant=variant,
        )
    except Exception as e:
        return (
            '<div class="error">'
            f'Error rendering component "{escape(name)}"'
            f'{f" v={version}" if version is not None else ""}: {escape(str(e))}'
            "</div>"
        )


def _render_shortcode(
    name: str,
    attrs: dict[str, Any],
    inner_markdown: str,
    user_id: Optional[int] = None,
    theme: Optional[dict[str, Any]] = None,
    render_depth: int = 0,
    render_stack: Optional[tuple[str, ...]] = None,
) -> str:
    short_name = name.lower()
    if short_name == "row":
        return _render_row_shortcode(attrs, inner_markdown)
    if short_name == "column":
        return _render_column_shortcode(attrs, inner_markdown)
    if short_name == "table":
        return _render_table_shortcode(attrs, inner_markdown)
    version = _parse_version(attrs.pop("v", None))
    return render_component(
        name,
        attrs,
        user_id,
        inner_markdown,
        version=version,
        theme=theme,
        _render_depth=render_depth + 1,
        _render_stack=render_stack,
    )


def _expand_shortcodes(
    markdown_source: str,
    user_id: Optional[int] = None,
    theme: Optional[dict[str, Any]] = None,
    render_depth: int = 0,
    render_stack: Optional[tuple[str, ...]] = None,
) -> str:
    text = markdown_source

    while True:
        replaced = False

        def replace_enclosed(match: re.Match[str]) -> str:
            nonlocal replaced
            replaced = True
            name = match.group(1)
            short_name = name.lower()
            if short_name not in CORE_LAYOUT_COMPONENTS:
                return match.group(0)
            raw_attrs = match.group(2) or ""
            inner = match.group(3) or ""
            attrs = _parse_shortcode_attrs(raw_attrs)
            expanded_inner = _expand_shortcodes(
                inner,
                user_id,
                theme,
                render_depth=render_depth + 1,
                render_stack=render_stack,
            )
            return _render_shortcode(
                name,
                attrs,
                expanded_inner,
                user_id,
                theme,
                render_depth=render_depth,
                render_stack=render_stack,
            )

        text = ENCLOSED_SHORTCODE_RE.sub(replace_enclosed, text)
        if not replaced:
            break

    def replace_self(match: re.Match[str]) -> str:
        name = match.group(1)
        short_name = name.lower()
        if short_name not in CORE_LAYOUT_COMPONENTS:
            return match.group(0)
        attrs = _parse_shortcode_attrs(match.group(2) or "")
        return _render_shortcode(
            name,
            attrs,
            "",
            user_id,
            theme,
            render_depth=render_depth,
            render_stack=render_stack,
        )

    return SELF_SHORTCODE_RE.sub(replace_self, text)


def _expand_component_fences(
    markdown_source: str,
    user_id: Optional[int] = None,
    theme: Optional[dict[str, Any]] = None,
    render_depth: int = 0,
    render_stack: Optional[tuple[str, ...]] = None,
) -> str:
    stack = render_stack or tuple()
    if render_depth > MAX_COMPONENT_NESTING_DEPTH:
        return (
            '<div class="error">'
            f"Component nesting exceeded max depth ({MAX_COMPONENT_NESTING_DEPTH})"
            "</div>"
        )

    lines = markdown_source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        start_match = COMPONENT_FENCE_START_RE.match(line)
        if not start_match:
            output.append(line)
            idx += 1
            continue

        name = start_match.group(1)
        name_key = name.lower()
        header = start_match.group(2) or ""
        header_attrs = _parse_shortcode_attrs(header)
        version = _parse_version(header_attrs.pop("v", None))
        slot_name = header_attrs.pop("slot", None)
        if not isinstance(slot_name, str):
            slot_name = None

        cycle_error = None
        if name_key not in CORE_LAYOUT_COMPONENTS and name_key in stack:
            cycle = " -> ".join([*stack, name_key])
            cycle_error = (
                '<div class="error">'
                f'Circular component reference detected: {escape(cycle)}'
                "</div>"
            )

        idx += 1
        body_lines: list[str] = []
        found_end = False
        depth = 1
        while idx < len(lines):
            current = lines[idx]
            if COMPONENT_FENCE_START_RE.match(current):
                depth += 1
                body_lines.append(current)
                idx += 1
                continue
            if current.strip() == ":::":
                depth -= 1
                if depth == 0:
                    found_end = True
                    idx += 1
                    break
                body_lines.append(current)
                idx += 1
                continue

            body_lines.append(current)
            idx += 1

        if not found_end:
            output.append(
                '<div class="error">'
                f'Unclosed component block for "{escape(name)}"'
                "</div>"
            )
            break

        if name_key not in CORE_LAYOUT_COMPONENTS:
            output.append("\n".join([line, *body_lines, ":::"]))
            continue

        if cycle_error:
            output.append(cycle_error)
            continue

        body_props, body_content = _parse_component_fence_props(body_lines)
        next_stack = stack if name_key in CORE_LAYOUT_COMPONENTS else (*stack, name_key)
        expanded_body = _expand_component_fences(
            body_content,
            user_id,
            theme,
            render_depth=render_depth + 1,
            render_stack=next_stack,
        )
        expanded_body = _expand_shortcodes(
            expanded_body,
            user_id,
            theme,
            render_depth=render_depth + 1,
            render_stack=next_stack,
        )
        props = {**header_attrs, **body_props}
        try:
            if name_key in CORE_LAYOUT_COMPONENTS:
                if version is not None:
                    props["v"] = version
                rendered = _render_shortcode(
                    name=name,
                    attrs=props,
                    inner_markdown=expanded_body,
                    user_id=user_id,
                    theme=theme,
                    render_depth=render_depth,
                    render_stack=next_stack,
                )
            else:
                rendered = render_component(
                    name=name,
                    props=props,
                    user_id=user_id,
                    inner_markdown=expanded_body,
                    version=version,
                    theme=theme,
                    _render_depth=render_depth + 1,
                    _render_stack=next_stack,
                )
        except Exception as e:
            rendered = (
                '<div class="error">'
                f'Error rendering component block "{escape(name)}": {escape(str(e))}'
                "</div>"
            )
        if slot_name:
            safe_slot = escape(slot_name, quote=True)
            rendered = f'<div data-docsly-slot="{safe_slot}">{rendered}</div>'
        output.append(rendered)

    return "\n".join(output)


def _format_component_header(name: str, version: Optional[int] = None, slot: Optional[str] = None) -> str:
    header = f":::{name}"
    if version is not None:
        header += f" v={version}"
    if slot:
        safe_slot = slot if re.fullmatch(r"[a-zA-Z][\w-]*", slot) else json.dumps(slot)
        header += f" slot={safe_slot}"
    return header


def _block_to_markdown(block: dict) -> str:
    block_type = block.get("type")
    if block_type == "markdown":
        return str(block.get("content", ""))

    name = block.get("name", "")
    if block_type == "component" and name:
        version = _parse_version(block.get("version"))
        slot_value = block.get("slot") if isinstance(block.get("slot"), str) else None
        props = block.get("props", {}) or {}
        inner_markdown = block.get("inner_markdown", "")
        if not isinstance(inner_markdown, str):
            inner_markdown = ""
        children = block.get("children", [])
        child_markdown = ""
        if isinstance(children, list):
            child_parts = [_block_to_markdown(child) for child in children if isinstance(child, dict)]
            child_markdown = "\n\n".join(part for part in child_parts if part.strip())
        header = _format_component_header(name, version, slot_value)
        if isinstance(props, dict) and props:
            lines = []
            for key, value in props.items():
                if isinstance(key, str) and key.startswith("__"):
                    continue
                if isinstance(value, str):
                    escaped = value.replace('"', '\\"')
                    lines.append(f'{key}="{escaped}"')
                else:
                    lines.append(f"{key}={json.dumps(value, ensure_ascii=False)}")
            body_parts = [chr(10).join(lines)]
            if inner_markdown.strip():
                body_parts.append(inner_markdown.strip())
            if child_markdown.strip():
                body_parts.append(child_markdown.strip())
            body = "\n".join(part for part in body_parts if part.strip())
            return f"{header}\n{body}\n:::"
        body_parts = []
        if inner_markdown.strip():
            body_parts.append(inner_markdown.strip())
        if child_markdown.strip():
            body_parts.append(child_markdown.strip())
        if body_parts:
            return f"{header}\n{chr(10).join(body_parts)}\n:::"
        return f"{header}\n:::"

    # When block_type is the component name directly (e.g., "heading", "callout")
    if isinstance(block_type, str) and block_type:
        version = _parse_version(block.get("version"))
        slot_value = block.get("slot") if isinstance(block.get("slot"), str) else None
        props = block.get("props", {}) or {}
        header = _format_component_header(block_type, version, slot_value)
        if isinstance(props, dict) and props:
            lines = []
            for key, value in props.items():
                if isinstance(key, str) and key.startswith("__"):
                    continue
                if isinstance(value, str):
                    escaped = value.replace('"', '\\"')
                    lines.append(f'{key}="{escaped}"')
                else:
                    lines.append(f"{key}={json.dumps(value, ensure_ascii=False)}")
            return f"{header}\n{chr(10).join(lines)}\n:::"
        return f"{header}\n:::"
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
    if not isinstance(block, dict):
        return ""

    # Reuse the same markdown expansion pipeline as full-document rendering
    # so block preview matches document preview for nested children/slots.
    markdown_source = _block_to_markdown(block)
    expanded_components = _expand_component_fences(
        markdown_source,
        user_id,
        theme=None,
        render_depth=0,
        render_stack=tuple(),
    )
    expanded_markdown = _expand_shortcodes(
        expanded_components,
        user_id,
        theme=None,
        render_depth=0,
        render_stack=tuple(),
    )
    return render_markdown(expanded_markdown)


def get_theme_css(theme_id: Optional[int], user_id: Optional[int] = None) -> str:
    """Backward-compatible wrapper for theme CSS generation."""
    return _build_theme_css(theme_id, user_id)


def render_document(content: dict, user_id: Optional[int] = None) -> str:
    """Render full markdown document to HTML (with shortcode support)."""
    markdown_source, theme_id = _normalize_document_content(content or {})
    theme_css = _build_theme_css(theme_id, user_id)
    theme = Theme.query.filter(
        Theme.id == theme_id,
        db.or_(Theme.user_id == user_id, Theme.is_builtin == True)
    ).first() if theme_id else None
    theme_dict = (theme.variables or {}) if theme else {}

    expanded_components = _expand_component_fences(
        markdown_source,
        user_id,
        theme_dict,
        render_depth=0,
        render_stack=tuple(),
    )
    expanded_markdown = _expand_shortcodes(
        expanded_components,
        user_id,
        theme_dict,
        render_depth=0,
        render_stack=tuple(),
    )
    rendered_html = render_markdown(expanded_markdown)

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
        .docsly-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        .docsly-content th,
        .docsly-content td {{
            border: 1px solid #e5e7eb;
            padding: 0.5rem 0.75rem;
            text-align: left;
        }}
        .docsly-content th {{
            background: #f8fafc;
            font-weight: 600;
        }}
        .docsly-content pre {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 1rem 1.25rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            margin: 1rem 0;
            font-size: 0.875rem;
            line-height: 1.7;
        }}
        .docsly-content code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.875em;
        }}
        .docsly-content :not(pre) > code {{
            background: #f1f5f9;
            color: #dc2626;
            padding: 0.125rem 0.375rem;
            border-radius: 0.25rem;
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
