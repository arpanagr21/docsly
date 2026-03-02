from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

from app.extensions import db
from app.models import Component
from app.schemas import ComponentCreate, ComponentUpdate
from app.services.validator import validate_component_schema
from app.services.renderer import render_block, render_component_template_preview_details
from app.services.component_registry import rebuild_component_registry

components_bp = Blueprint("components", __name__, url_prefix="/api/components")


def get_current_user_id() -> int:
    return int(get_jwt_identity())


@components_bp.route("", methods=["GET"])
@jwt_required()
def list_components():
    user_id = get_current_user_id()

    # Get user's components and builtin components
    components = Component.query.filter(
        db.or_(
            Component.user_id == user_id,
            Component.is_builtin == True
        ),
        Component.is_active == True
    ).order_by(Component.name).all()

    return jsonify({"components": [c.to_dict() for c in components]})


@components_bp.route("", methods=["POST"])
@jwt_required()
def create_component():
    try:
        data = ComponentCreate(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    # Validate schema structure
    validation_error = validate_component_schema(data.component_schema)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    user_id = get_current_user_id()

    # Check if component with same name exists
    existing = Component.query.filter_by(
        user_id=user_id,
        name=data.name,
        is_active=True
    ).first()

    version = 1
    if existing:
        version = existing.version + 1
        existing.is_active = False
        db.session.add(existing)

    component = Component(
        user_id=user_id,
        name=data.name,
        version=version,
        schema=data.component_schema,
        template=data.template,
        style_contract=data.style_contract or {},
        default_styles=data.default_styles or {},
    )
    db.session.add(component)
    db.session.commit()
    rebuild_component_registry()

    return jsonify({"component": component.to_dict()}), 201


@components_bp.route("/<int:comp_id>", methods=["GET"])
@jwt_required()
def get_component(comp_id: int):
    user_id = get_current_user_id()
    component = Component.query.filter(
        Component.id == comp_id,
        db.or_(Component.user_id == user_id, Component.is_builtin == True)
    ).first()

    if not component:
        return jsonify({"error": "Component not found"}), 404

    return jsonify({"component": component.to_dict()})


@components_bp.route("/name/<string:name>", methods=["GET"])
@jwt_required()
def get_component_by_name(name: str):
    user_id = get_current_user_id()
    component = Component.query.filter(
        Component.name == name,
        Component.is_active == True,
        db.or_(Component.user_id == user_id, Component.is_builtin == True)
    ).first()

    if not component:
        return jsonify({"error": "Component not found"}), 404

    return jsonify({"component": component.to_dict()})


@components_bp.route("/<int:comp_id>", methods=["PUT"])
@jwt_required()
def update_component(comp_id: int):
    try:
        data = ComponentUpdate(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    user_id = get_current_user_id()
    component = Component.query.filter_by(id=comp_id, user_id=user_id).first()

    if not component:
        return jsonify({"error": "Component not found"}), 404

    if component.is_builtin:
        return jsonify({"error": "Cannot modify builtin components"}), 403

    # Validate schema if provided
    if data.component_schema:
        validation_error = validate_component_schema(data.component_schema)
        if validation_error:
            return jsonify({"error": validation_error}), 400

    # Create new version
    component.is_active = False

    new_component = Component(
        user_id=user_id,
        name=component.name,
        version=component.version + 1,
        schema=data.component_schema or component.schema,
        template=data.template or component.template,
        style_contract=data.style_contract if data.style_contract is not None else component.style_contract,
        default_styles=data.default_styles if data.default_styles is not None else component.default_styles,
    )
    db.session.add(new_component)
    db.session.commit()
    rebuild_component_registry()

    return jsonify({"component": new_component.to_dict()})


@components_bp.route("/<int:comp_id>", methods=["DELETE"])
@jwt_required()
def delete_component(comp_id: int):
    user_id = get_current_user_id()
    component = Component.query.filter_by(id=comp_id, user_id=user_id).first()

    if not component:
        return jsonify({"error": "Component not found"}), 404

    if component.is_builtin:
        return jsonify({"error": "Cannot delete builtin components"}), 403

    component.is_active = False
    db.session.commit()
    rebuild_component_registry()
    return jsonify({"message": "Component deactivated"})


@components_bp.route("/preview", methods=["POST"])
@jwt_required()
def preview_block():
    """Render a single block for live preview."""
    user_id = get_current_user_id()
    block = request.json

    if not block:
        return jsonify({"error": "Block data required"}), 400

    try:
        html = render_block(block, user_id)
        return jsonify({"html": html})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@components_bp.route("/preview-template", methods=["POST"])
@jwt_required()
def preview_template():
    payload = request.get_json(silent=True) or {}
    template = payload.get("template", "")
    props = payload.get("props", {})
    component_name = payload.get("name", "preview-component")
    style_contract = payload.get("style_contract", {})
    default_styles = payload.get("default_styles", {})
    theme = payload.get("theme", {})

    if not isinstance(template, str):
        return jsonify({"error": "template must be a string"}), 400
    if not isinstance(props, dict):
        return jsonify({"error": "props must be an object"}), 400
    if not isinstance(component_name, str):
        return jsonify({"error": "name must be a string"}), 400
    if not isinstance(style_contract, dict):
        return jsonify({"error": "style_contract must be an object"}), 400
    if not isinstance(default_styles, dict):
        return jsonify({"error": "default_styles must be an object"}), 400
    if not isinstance(theme, dict):
        return jsonify({"error": "theme must be an object"}), 400

    try:
        preview = render_component_template_preview_details(
            template=template,
            props=props,
            component_name=component_name,
            style_contract=style_contract,
            default_styles=default_styles,
            theme=theme,
        )
        return jsonify(preview)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
