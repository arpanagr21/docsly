from datetime import datetime
import secrets
from app.extensions import db


class OAuthClient(db.Model):
    """OAuth clients created by users for MCP access."""
    __tablename__ = "oauth_clients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    client_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    client_secret_hash = db.Column(db.String(255), nullable=False)
    scopes = db.Column(db.String(512), default="mcp:tools")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("oauth_clients", lazy="dynamic"))

    @staticmethod
    def generate_client_id() -> str:
        """Generate a unique client ID."""
        return f"docsly_{secrets.token_urlsafe(24)}"

    @staticmethod
    def generate_client_secret() -> str:
        """Generate a secure client secret."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_secret(secret: str) -> str:
        """Hash a client secret for storage."""
        import hashlib
        return hashlib.sha256(secret.encode()).hexdigest()

    def verify_secret(self, secret: str) -> bool:
        """Verify a client secret against the stored hash."""
        return self.client_secret_hash == self.hash_secret(secret)

    def to_dict(self, include_secret: bool = False) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "client_id": self.client_id,
            "scopes": self.scopes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class OAuthAuthCode(db.Model):
    """OAuth authorization codes (short-lived, one-time use)."""
    __tablename__ = "oauth_auth_codes"

    code = db.Column(db.String(64), primary_key=True)
    client_id = db.Column(db.String(255), nullable=False)
    redirect_uri = db.Column(db.String(2048), nullable=False)
    scope = db.Column(db.String(255), nullable=False)
    code_challenge = db.Column(db.String(128), nullable=True)
    code_challenge_method = db.Column(db.String(16), nullable=True)
    expires_at = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "code_challenge": self.code_challenge,
            "code_challenge_method": self.code_challenge_method,
            "expires_at": self.expires_at,
        }


class OAuthAccessToken(db.Model):
    """OAuth access tokens (longer-lived)."""
    __tablename__ = "oauth_access_tokens"

    token = db.Column(db.String(64), primary_key=True)
    client_id = db.Column(db.String(255), nullable=False)
    scope = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.Integer, nullable=False, index=True)
    refresh_token = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "scope": self.scope,
            "expires_at": self.expires_at,
        }


class OAuthRefreshToken(db.Model):
    """OAuth refresh tokens (very long-lived, used to get new access tokens)."""
    __tablename__ = "oauth_refresh_tokens"

    token = db.Column(db.String(64), primary_key=True)
    client_id = db.Column(db.String(255), nullable=False)
    scope = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "scope": self.scope,
            "expires_at": self.expires_at,
        }
