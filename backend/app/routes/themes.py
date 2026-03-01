from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

from app.extensions import db
from app.models import Theme
from app.schemas import ThemeCreate, ThemeUpdate

themes_bp = Blueprint("themes", __name__, url_prefix="/api/themes")


def get_current_user_id() -> int:
    return int(get_jwt_identity())


@themes_bp.route("", methods=["GET"])
@jwt_required()
def list_themes():
    user_id = get_current_user_id()

    themes = Theme.query.filter(
        db.or_(
            Theme.user_id == user_id,
            Theme.is_builtin == True
        )
    ).order_by(Theme.name).all()

    return jsonify({"themes": [t.to_dict() for t in themes]})


@themes_bp.route("", methods=["POST"])
@jwt_required()
def create_theme():
    try:
        data = ThemeCreate(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    user_id = get_current_user_id()

    # If setting as default, unset other defaults
    if data.is_default:
        Theme.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})

    theme = Theme(
        user_id=user_id,
        name=data.name,
        variables=data.variables,
        is_default=data.is_default,
    )
    db.session.add(theme)
    db.session.commit()

    return jsonify({"theme": theme.to_dict()}), 201


@themes_bp.route("/<int:theme_id>", methods=["GET"])
@jwt_required()
def get_theme(theme_id: int):
    user_id = get_current_user_id()
    theme = Theme.query.filter(
        Theme.id == theme_id,
        db.or_(Theme.user_id == user_id, Theme.is_builtin == True)
    ).first()

    if not theme:
        return jsonify({"error": "Theme not found"}), 404

    return jsonify({"theme": theme.to_dict()})


@themes_bp.route("/<int:theme_id>", methods=["PUT"])
@jwt_required()
def update_theme(theme_id: int):
    try:
        data = ThemeUpdate(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    user_id = get_current_user_id()
    theme = Theme.query.filter_by(id=theme_id, user_id=user_id).first()

    if not theme:
        return jsonify({"error": "Theme not found"}), 404

    if theme.is_builtin:
        return jsonify({"error": "Cannot modify builtin themes"}), 403

    if data.name is not None:
        theme.name = data.name
    if data.variables is not None:
        theme.variables = data.variables
    if data.is_default is not None:
        if data.is_default:
            Theme.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})
        theme.is_default = data.is_default

    db.session.commit()
    return jsonify({"theme": theme.to_dict()})


@themes_bp.route("/<int:theme_id>", methods=["DELETE"])
@jwt_required()
def delete_theme(theme_id: int):
    user_id = get_current_user_id()
    theme = Theme.query.filter_by(id=theme_id, user_id=user_id).first()

    if not theme:
        return jsonify({"error": "Theme not found"}), 404

    if theme.is_builtin:
        return jsonify({"error": "Cannot delete builtin themes"}), 403

    db.session.delete(theme)
    db.session.commit()
    return jsonify({"message": "Theme deleted"})
