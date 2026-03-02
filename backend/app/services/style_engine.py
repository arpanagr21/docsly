from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


def deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _safe_component_class(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "-", name).strip("-").lower()
    return safe or "component"


def _dict_to_css(style_map: dict[str, Any]) -> str:
    parts: list[str] = []
    for prop, value in style_map.items():
        if not isinstance(prop, str):
            continue
        if isinstance(value, (str, int, float)):
            parts.append(f"{prop}: {value};")
    return " ".join(parts)


def _select_variant(default_styles: dict[str, Any], variant: str | None) -> dict[str, Any]:
    if not variant:
        return default_styles
    variants = default_styles.get("variants", {})
    if not isinstance(variants, dict):
        return default_styles
    variant_map = variants.get(variant)
    if not isinstance(variant_map, dict):
        return default_styles
    return deep_merge_dict(default_styles, variant_map)


def compose_component_css(
    component_name: str,
    style_contract: dict[str, Any],
    default_styles: dict[str, Any],
    theme_styles: dict[str, Any],
    variant: str | None,
) -> str:
    """
    Compose component CSS from component defaults + theme overrides.
    Supports:
    - base: {prop: value}
    - slots: {slotName: {prop: value}}
    - elements: {selector: {prop: value}} (scoped inside component root)
    """
    merged = deep_merge_dict(default_styles or {}, theme_styles or {})
    selected = _select_variant(merged, variant)
    component_class = _safe_component_class(component_name)
    root_selector = f".cmp-{component_class}"
    css_blocks: list[str] = []

    base = selected.get("base", {})
    if isinstance(base, dict):
        css = _dict_to_css(base)
        if css:
            css_blocks.append(f"{root_selector} {{ {css} }}")

    slots = selected.get("slots", {})
    contract_slots = style_contract.get("slots", []) if isinstance(style_contract, dict) else []
    allowed = set(slot for slot in contract_slots if isinstance(slot, str))

    if isinstance(slots, dict):
        for slot_name, slot_styles in slots.items():
            if not isinstance(slot_name, str) or not isinstance(slot_styles, dict):
                continue
            if allowed and slot_name not in allowed:
                continue
            css = _dict_to_css(slot_styles)
            if not css:
                continue
            selector = (
                f"{root_selector} .cmp-{component_class}__{slot_name}, "
                f'{root_selector} [data-slot="{slot_name}"]'
            )
            css_blocks.append(f"{selector} {{ {css} }}")

    elements = selected.get("elements", {})
    if isinstance(elements, dict):
        for element_selector, element_styles in elements.items():
            if not isinstance(element_selector, str) or not element_selector.strip():
                continue
            if not isinstance(element_styles, dict):
                continue
            css = _dict_to_css(element_styles)
            if not css:
                continue
            css_blocks.append(f"{root_selector} {element_selector.strip()} {{ {css} }}")

    return "\n".join(css_blocks)
