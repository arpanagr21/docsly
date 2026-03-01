from datetime import datetime
from app.extensions import db


class Theme(db.Model):
    __tablename__ = "themes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    variables = db.Column(db.JSON, nullable=False, default=dict)
    is_default = db.Column(db.Boolean, default=False)
    is_builtin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "variables": self.variables,
            "is_default": self.is_default,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat(),
        }
