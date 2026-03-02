from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy import inspect, text

from app.config import Config
from app.extensions import db, jwt
from app.routes import auth_bp, documents_bp, components_bp, themes_bp, oauth_clients_bp
from app.services.component_registry import rebuild_component_registry
# Import OAuth models so db.create_all() creates their tables
from app.models.oauth import OAuthClient, OAuthAuthCode, OAuthAccessToken, OAuthRefreshToken  # noqa: F401


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    
    # Configure CORS from environment
    import os
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3005").split(",")
    cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
    CORS(app, origins=cors_origins, supports_credentials=True)

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return jsonify({"status": "healthy"})

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(components_bp)
    app.register_blueprint(themes_bp)
    app.register_blueprint(oauth_clients_bp)

    # Create tables
    with app.app_context():
        db.create_all()
        ensure_runtime_schema()
        seed_builtin_data()
        rebuild_component_registry()

    return app


def ensure_runtime_schema():
    """Lightweight runtime schema patching for SQLite deployments without migrations."""
    inspector = inspect(db.engine)
    if "components" not in inspector.get_table_names():
        return

    existing_cols = {col["name"] for col in inspector.get_columns("components")}
    statements = []

    if "style_contract" not in existing_cols:
        statements.append("ALTER TABLE components ADD COLUMN style_contract JSON NOT NULL DEFAULT '{}'")
    if "default_styles" not in existing_cols:
        statements.append("ALTER TABLE components ADD COLUMN default_styles JSON NOT NULL DEFAULT '{}'")

    if not statements:
        return

    with db.engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def seed_builtin_data():
    """Seed or sync builtin components and themes."""
    from app.models import Component, Theme

    # Keep builtin component catalog empty by default.
    # Core layout primitives are exposed via markdown syntax/shortcodes:
    # :::row ... :::, :::column ... :::, :::table ... :::
    builtin_components = []

    component_style_presets = {}

    default_contract = {
        "slots": ["root"],
        "variants": ["default", "compact", "emphasis"],
    }
    default_styles = {
        "base": {
            "display": "block",
            "margin": "0.95rem 0",
            "font-size": "16px",
            "line-height": "1.65",
        },
        "slots": {"root": {}},
        "elements": {
            "h1": {"font-size": "2rem", "line-height": "1.2", "margin": "0 0 0.7rem", "font-weight": "700"},
            "h2": {"font-size": "1.5rem", "line-height": "1.25", "margin": "0 0 0.6rem", "font-weight": "700"},
            "h3": {"font-size": "1.2rem", "line-height": "1.3", "margin": "0.7rem 0 0.45rem", "font-weight": "700"},
            "p": {"margin": "0.45rem 0", "font-size": "1rem"},
            "li": {"margin": "0.25rem 0", "font-size": "0.98rem"},
            "table": {"width": "100%", "border-collapse": "collapse", "margin": "0.7rem 0"},
            "th, td": {"padding": "0.45rem 0.6rem", "border": "1px solid #e5e7eb"},
            "th": {"background": "#f8fafc", "font-weight": "600"},
            "blockquote": {"margin": "0.6rem 0", "padding": "0.55rem 0.8rem", "border-left": "4px solid #93c5fd", "background": "#eff6ff"},
        },
        "variants": {
            "compact": {"base": {"margin": "0.55rem 0"}},
            "emphasis": {"base": {"padding": "0.75rem 0.9rem", "background": "#f8fafc", "border-radius": "0.5rem"}},
        },
    }

    for comp in builtin_components:
        comp.setdefault("style_contract", default_contract)
        preset = component_style_presets.get(comp["name"], {})
        merged = dict(default_styles)
        if preset:
            merged = {
                "base": {**default_styles.get("base", {}), **preset.get("base", {})},
                "slots": {**default_styles.get("slots", {}), **preset.get("slots", {})},
                "variants": {**default_styles.get("variants", {}), **preset.get("variants", {})},
            }
        comp.setdefault("default_styles", merged)

    # Builtin themes
    builtin_themes = [
        {
            "name": "Default",
            "variables": {
                "font-family": "system-ui, -apple-system, sans-serif",
                "line-height": "1.6",
                "text-color": "#1a1a1a",
                "background-color": "#ffffff",
                "primary-color": "#3b82f6",
                "max-width": "800px",
                "__element_styles": {
                    "h1": {"font-size": "2rem", "font-weight": "700", "margin-bottom": "0.75rem"},
                    "h2": {"font-size": "1.5rem", "font-weight": "700", "margin-bottom": "0.6rem"},
                    "p": {"margin-bottom": "0.75rem"},
                    "table": {"width": "100%", "border-collapse": "collapse"},
                    "table th, table td": {"border": "1px solid #e5e7eb", "padding": "0.5rem 0.75rem"},
                    "table th": {"background": "#f8fafc", "font-weight": "600"},
                    ".dsl-row": {"gap": "1rem", "margin": "1rem 0"}
                }
            },
            "is_default": True
        },
        {
            "name": "Professional",
            "variables": {
                "font-family": "Georgia, serif",
                "line-height": "1.8",
                "text-color": "#1f2937",
                "background-color": "#fafafa",
                "primary-color": "#1e40af",
                "max-width": "700px",
                "__element_styles": {
                    "h1, h2, h3": {"font-family": "Georgia, serif"},
                    "table th": {"background": "#f3f4f6"}
                }
            },
            "is_default": False
        },
        {
            "name": "Modern",
            "variables": {
                "font-family": "Inter, system-ui, sans-serif",
                "line-height": "1.5",
                "text-color": "#0f172a",
                "background-color": "#ffffff",
                "primary-color": "#7c3aed",
                "max-width": "900px",
                "__element_styles": {
                    "h1, h2, h3": {"letter-spacing": "-0.02em"},
                    "table th": {"background": "#f5f3ff"}
                }
            },
            "is_default": False
        }
    ]

    builtin_component_names = {comp.get("name") for comp in builtin_components if isinstance(comp.get("name"), str)}
    stale_builtins = Component.query.filter(
        Component.is_builtin == True,
        Component.is_active == True,
    ).all()
    for stale in stale_builtins:
        if stale.name not in builtin_component_names:
            stale.is_active = False
            db.session.add(stale)

    for comp_data in builtin_components:
        latest = Component.query.filter_by(
            name=comp_data["name"],
            is_builtin=True,
            is_active=True,
        ).order_by(Component.version.desc()).first()

        if latest and latest.schema == comp_data["schema"] and latest.template == comp_data["template"]:
            if latest.style_contract != (comp_data.get("style_contract") or {}) or latest.default_styles != (comp_data.get("default_styles") or {}):
                latest.is_active = False
                db.session.add(latest)
                component = Component(
                    name=comp_data["name"],
                    schema=comp_data["schema"],
                    template=comp_data["template"],
                    style_contract=comp_data.get("style_contract") or {},
                    default_styles=comp_data.get("default_styles") or {},
                    version=latest.version + 1,
                    is_builtin=True,
                    is_active=True,
                )
                db.session.add(component)
            continue

        if latest:
            latest.is_active = False
            db.session.add(latest)
            next_version = latest.version + 1
        else:
            next_version = 1

        component = Component(
            name=comp_data["name"],
            schema=comp_data["schema"],
            template=comp_data["template"],
            style_contract=comp_data.get("style_contract") or {},
            default_styles=comp_data.get("default_styles") or {},
            version=next_version,
            is_builtin=True,
            is_active=True,
        )
        db.session.add(component)

    for theme_data in builtin_themes:
        theme = Theme.query.filter_by(name=theme_data["name"], is_builtin=True).first()
        if theme:
            theme.variables = theme_data["variables"]
            theme.is_default = theme_data["is_default"]
            db.session.add(theme)
            continue
        db.session.add(
            Theme(
                name=theme_data["name"],
                variables=theme_data["variables"],
                is_builtin=True,
                is_default=theme_data["is_default"],
            )
        )

    db.session.commit()
