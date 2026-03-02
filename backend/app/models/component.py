from datetime import datetime
from app.extensions import db


class Component(db.Model):
    __tablename__ = "components"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    schema = db.Column(db.JSON, nullable=False, default=dict)
    template = db.Column(db.Text, nullable=False)
    style_contract = db.Column(db.JSON, nullable=False, default=dict)
    default_styles = db.Column(db.JSON, nullable=False, default=dict)
    is_active = db.Column(db.Boolean, default=True)
    is_builtin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", "version", name="unique_component_version"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "version": self.version,
            "schema": self.schema,
            "template": self.template,
            "style_contract": self.style_contract,
            "default_styles": self.default_styles,
            "is_active": self.is_active,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat(),
        }
