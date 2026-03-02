from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable, Optional

from app.models import Component


@dataclass(frozen=True)
class RegisteredComponent:
    user_id: Optional[int]
    name: str
    version: int
    schema: dict
    style_contract: dict
    default_styles: dict
    renderer: Callable[[dict, dict], str]


_lock = RLock()
_by_exact: dict[tuple[Optional[int], str, int], Component] = {}
_latest: dict[tuple[Optional[int], str], int] = {}


def rebuild_component_registry() -> None:
    """Rebuild in-memory component registry from active DB components."""
    components = Component.query.filter(Component.is_active == True).all()

    by_exact: dict[tuple[Optional[int], str, int], Component] = {}
    latest: dict[tuple[Optional[int], str], int] = {}

    for comp in components:
        exact_key = (comp.user_id, comp.name, comp.version)
        latest_key = (comp.user_id, comp.name)
        by_exact[exact_key] = comp
        latest[latest_key] = max(comp.version, latest.get(latest_key, 0))

    with _lock:
        _by_exact.clear()
        _by_exact.update(by_exact)
        _latest.clear()
        _latest.update(latest)


def _lookup_component(name: str, version: Optional[int], user_id: Optional[int]) -> Optional[Component]:
    name = name.strip()
    candidates = [user_id, None] if user_id is not None else [None]

    with _lock:
        for candidate_user in candidates:
            if version is not None:
                comp = _by_exact.get((candidate_user, name, version))
                if comp:
                    return comp
                continue

            latest_version = _latest.get((candidate_user, name))
            if latest_version is None:
                continue
            comp = _by_exact.get((candidate_user, name, latest_version))
            if comp:
                return comp

    return None


def get_registered_component(
    name: str,
    version: Optional[int],
    user_id: Optional[int],
    renderer_factory: Callable[[Component], Callable[[dict, dict], str]],
) -> RegisteredComponent:
    """Resolve component by (name, version) with user scope fallback to builtin."""
    component = _lookup_component(name, version, user_id)
    # If requested version does not exist (common after version bumps),
    # gracefully fall back to latest active version of same name.
    if not component and version is not None:
        component = _lookup_component(name, None, user_id)
    if not component:
        version_label = f" v={version}" if version is not None else ""
        raise LookupError(f'Component "{name}"{version_label} not found in registry')

    return RegisteredComponent(
        user_id=component.user_id,
        name=component.name,
        version=component.version,
        schema=component.schema or {},
        style_contract=component.style_contract or {},
        default_styles=component.default_styles or {},
        renderer=renderer_factory(component),
    )
