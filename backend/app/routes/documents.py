from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError

from app.extensions import db
from app.models import Document
from app.schemas import DocumentCreate, DocumentUpdate
from app.services.renderer import render_document
from app.services.pdf_engine import render_pdf_from_html

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


def get_current_user_id() -> int:
    return int(get_jwt_identity())


@documents_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    user_id = get_current_user_id()
    documents = Document.query.filter_by(user_id=user_id).order_by(Document.updated_at.desc()).all()
    return jsonify({"documents": [doc.to_dict() for doc in documents]})


@documents_bp.route("", methods=["POST"])
@jwt_required()
def create_document():
    try:
        data = DocumentCreate(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    user_id = get_current_user_id()

    default_content = {
        "version": "2.0",
        "theme_id": None,
        "markdown": "",
    }

    document = Document(
        user_id=user_id,
        title=data.title,
        content=data.content or default_content,
        doc_metadata=data.metadata or {},
    )
    db.session.add(document)
    db.session.commit()

    return jsonify({"document": document.to_dict()}), 201


@documents_bp.route("/<int:doc_id>", methods=["GET"])
@jwt_required()
def get_document(doc_id: int):
    user_id = get_current_user_id()
    document = Document.query.filter_by(id=doc_id, user_id=user_id).first()

    if not document:
        return jsonify({"error": "Document not found"}), 404

    return jsonify({"document": document.to_dict()})


@documents_bp.route("/<int:doc_id>", methods=["PUT"])
@jwt_required()
def update_document(doc_id: int):
    try:
        data = DocumentUpdate(**request.json)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    user_id = get_current_user_id()
    document = Document.query.filter_by(id=doc_id, user_id=user_id).first()

    if not document:
        return jsonify({"error": "Document not found"}), 404

    if data.title is not None:
        document.title = data.title
    if data.content is not None:
        document.content = data.content
    if data.metadata is not None:
        document.doc_metadata = data.metadata

    db.session.commit()
    return jsonify({"document": document.to_dict()})


@documents_bp.route("/<int:doc_id>", methods=["DELETE"])
@jwt_required()
def delete_document(doc_id: int):
    user_id = get_current_user_id()
    document = Document.query.filter_by(id=doc_id, user_id=user_id).first()

    if not document:
        return jsonify({"error": "Document not found"}), 404

    db.session.delete(document)
    db.session.commit()
    return jsonify({"message": "Document deleted"})


@documents_bp.route("/<int:doc_id>/render", methods=["GET"])
@jwt_required()
def render_document_html(doc_id: int):
    user_id = get_current_user_id()
    document = Document.query.filter_by(id=doc_id, user_id=user_id).first()

    if not document:
        return jsonify({"error": "Document not found"}), 404

    html = render_document(document.content, user_id)
    return jsonify({"html": html})


@documents_bp.route("/<int:doc_id>/pdf", methods=["GET"])
@jwt_required()
def render_document_pdf(doc_id: int):
    user_id = get_current_user_id()
    document = Document.query.filter_by(id=doc_id, user_id=user_id).first()

    if not document:
        return jsonify({"error": "Document not found"}), 404

    try:
        html = render_document(document.content, user_id)
        pdf_bytes = render_pdf_from_html(html)
        filename = f'{document.title or "document"}.pdf'.replace("/", "-")

        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.headers["Content-Length"] = str(len(pdf_bytes))
        return response
    except Exception as e:
        return jsonify({"error": f"PDF render failed: {str(e)}"}), 500


@documents_bp.route("/preview", methods=["POST"])
@jwt_required()
def preview_document_html():
    """Render unsaved document content to HTML for live preview."""
    user_id = get_current_user_id()
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")

    if not isinstance(content, dict):
        return jsonify({"error": "content object is required"}), 400

    try:
        html = render_document(content, user_id)
        return jsonify({"html": html})
    except Exception as e:
        return jsonify({"error": f"Preview render failed: {str(e)}"}), 500


@documents_bp.route("/preview-pdf", methods=["POST"])
@jwt_required()
def preview_document_pdf():
    """Render unsaved document content to PDF for download."""
    user_id = get_current_user_id()
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    title = payload.get("title", "document")

    if not isinstance(content, dict):
        return jsonify({"error": "content object is required"}), 400

    try:
        html = render_document(content, user_id)
        pdf_bytes = render_pdf_from_html(html)
        safe_title = str(title or "document").replace("/", "-")
        filename = f"{safe_title}.pdf"

        response = make_response(pdf_bytes)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.headers["Content-Length"] = str(len(pdf_bytes))
        return response
    except Exception as e:
        return jsonify({"error": f"Preview PDF render failed: {str(e)}"}), 500
