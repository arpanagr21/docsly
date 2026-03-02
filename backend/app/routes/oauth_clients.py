from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import OAuthClient

oauth_clients_bp = Blueprint("oauth_clients", __name__, url_prefix="/api/oauth-clients")


@oauth_clients_bp.route("", methods=["GET"])
@jwt_required()
def list_oauth_clients():
    """List all OAuth clients for the current user."""
    user_id = int(get_jwt_identity())
    clients = OAuthClient.query.filter_by(user_id=user_id).order_by(OAuthClient.created_at.desc()).all()
    return jsonify({"clients": [c.to_dict() for c in clients]})


@oauth_clients_bp.route("", methods=["POST"])
@jwt_required()
def create_oauth_client():
    """Create a new OAuth client for the current user."""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400

    # Generate credentials
    client_id = OAuthClient.generate_client_id()
    client_secret = OAuthClient.generate_client_secret()
    client_secret_hash = OAuthClient.hash_secret(client_secret)

    client = OAuthClient(
        user_id=user_id,
        name=name,
        client_id=client_id,
        client_secret_hash=client_secret_hash,
        scopes=data.get("scopes", "mcp:tools"),
    )
    db.session.add(client)
    db.session.commit()

    # Return the client with the secret (only shown once)
    response = client.to_dict()
    response["client_secret"] = client_secret
    response["_notice"] = "Save the client_secret now. It will not be shown again."

    return jsonify({"client": response}), 201


@oauth_clients_bp.route("/<int:client_id>", methods=["GET"])
@jwt_required()
def get_oauth_client(client_id: int):
    """Get a specific OAuth client."""
    user_id = int(get_jwt_identity())
    client = OAuthClient.query.filter_by(id=client_id, user_id=user_id).first()
    if not client:
        return jsonify({"error": "OAuth client not found"}), 404
    return jsonify({"client": client.to_dict()})


@oauth_clients_bp.route("/<int:client_id>", methods=["PATCH"])
@jwt_required()
def update_oauth_client(client_id: int):
    """Update an OAuth client (name or active status)."""
    user_id = int(get_jwt_identity())
    client = OAuthClient.query.filter_by(id=client_id, user_id=user_id).first()
    if not client:
        return jsonify({"error": "OAuth client not found"}), 404

    data = request.get_json() or {}

    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"error": "Name cannot be empty"}), 400
        client.name = name

    if "is_active" in data:
        client.is_active = bool(data["is_active"])

    db.session.commit()
    return jsonify({"client": client.to_dict()})


@oauth_clients_bp.route("/<int:client_id>", methods=["DELETE"])
@jwt_required()
def delete_oauth_client(client_id: int):
    """Delete an OAuth client."""
    user_id = int(get_jwt_identity())
    client = OAuthClient.query.filter_by(id=client_id, user_id=user_id).first()
    if not client:
        return jsonify({"error": "OAuth client not found"}), 404

    db.session.delete(client)
    db.session.commit()
    return jsonify({"success": True, "deleted_id": client_id})


@oauth_clients_bp.route("/<int:client_id>/regenerate-secret", methods=["POST"])
@jwt_required()
def regenerate_oauth_client_secret(client_id: int):
    """Regenerate the client secret for an OAuth client."""
    user_id = int(get_jwt_identity())
    client = OAuthClient.query.filter_by(id=client_id, user_id=user_id).first()
    if not client:
        return jsonify({"error": "OAuth client not found"}), 404

    # Generate new secret
    client_secret = OAuthClient.generate_client_secret()
    client.client_secret_hash = OAuthClient.hash_secret(client_secret)
    db.session.commit()

    response = client.to_dict()
    response["client_secret"] = client_secret
    response["_notice"] = "Save the new client_secret now. It will not be shown again."

    return jsonify({"client": response})
