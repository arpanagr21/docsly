from app.routes.auth import auth_bp
from app.routes.documents import documents_bp
from app.routes.components import components_bp
from app.routes.themes import themes_bp
from app.routes.oauth_clients import oauth_clients_bp

__all__ = ["auth_bp", "documents_bp", "components_bp", "themes_bp", "oauth_clients_bp"]
