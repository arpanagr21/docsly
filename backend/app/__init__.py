from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config
from app.extensions import db, jwt
from app.routes import auth_bp, documents_bp, components_bp, themes_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=["http://localhost:3000"])

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return jsonify({"status": "healthy"})

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(components_bp)
    app.register_blueprint(themes_bp)

    # Create tables
    with app.app_context():
        db.create_all()
        seed_builtin_data()

    return app


def seed_builtin_data():
    """Seed builtin components and themes."""
    from app.models import Component, Theme

    # Check if already seeded
    if Component.query.filter_by(is_builtin=True).first():
        return

    # Builtin components with beautiful, professional styling
    builtin_components = [
        {
            "name": "heading",
            "schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The heading text"},
                    "level": {"type": "integer", "minimum": 1, "maximum": 6, "default": 1, "description": "Heading level (1-6)"},
                    "subtitle": {"type": "string", "description": "Optional subtitle text"}
                },
                "required": ["text"]
            },
            "template": """<div class="heading-component" style="margin: 1.5rem 0;">
    <h{{ level | default(1) }} style="margin: 0; color: var(--primary-color, #1a1a2e); font-weight: 700; line-height: 1.2;">{{ text }}</h{{ level | default(1) }}>
    {% if subtitle %}<p style="margin: 0.5rem 0 0 0; color: #6b7280; font-size: 1.1rem; font-weight: 400;">{{ subtitle }}</p>{% endif %}
</div>"""
        },
        {
            "name": "pricing-table",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Table title"},
                    "items": {
                        "type": "array",
                        "description": "Pricing plans",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Plan name"},
                                "price": {"type": "number", "description": "Price amount"},
                                "period": {"type": "string", "description": "Billing period (e.g., /month)"},
                                "description": {"type": "string", "description": "Plan description"},
                                "features": {"type": "array", "items": {"type": "string"}, "description": "List of features"},
                                "highlighted": {"type": "boolean", "description": "Highlight this plan"}
                            },
                            "required": ["name", "price"]
                        }
                    }
                },
                "required": ["items"]
            },
            "template": """<div class="pricing-table" style="margin: 2rem 0;">
    {% if title %}<h2 style="text-align: center; margin-bottom: 2rem; color: #1a1a2e; font-size: 1.75rem; font-weight: 700;">{{ title }}</h2>{% endif %}
    <div style="display: flex; flex-wrap: wrap; gap: 1.5rem; justify-content: center;">
        {% for item in items %}
        <div style="flex: 1 1 280px; max-width: 320px; background: {{ 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' if item.highlighted else '#ffffff' }}; border-radius: 16px; padding: 2rem; box-shadow: 0 10px 40px rgba(0,0,0,0.1); {{ 'color: white;' if item.highlighted else 'border: 1px solid #e5e7eb;' }}">
            <h3 style="margin: 0 0 0.5rem 0; font-size: 1.25rem; font-weight: 600;">{{ item.name }}</h3>
            {% if item.description %}<p style="margin: 0 0 1rem 0; font-size: 0.875rem; opacity: 0.8;">{{ item.description }}</p>{% endif %}
            <div style="margin: 1.5rem 0;">
                <span style="font-size: 2.5rem; font-weight: 800;">${{ item.price }}</span>
                <span style="font-size: 0.875rem; opacity: 0.7;">{{ item.period | default('/month') }}</span>
            </div>
            {% if item.features %}
            <ul style="list-style: none; padding: 0; margin: 1.5rem 0 0 0;">
                {% for f in item.features %}
                <li style="padding: 0.5rem 0; display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem;">
                    <span style="color: {{ '#ffffff' if item.highlighted else '#10b981' }};">&#10003;</span>
                    {{ f }}
                </li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</div>"""
        },
        {
            "name": "signature-block",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Signer's name"},
                    "title": {"type": "string", "description": "Signer's title/position"},
                    "company": {"type": "string", "description": "Company name"},
                    "date": {"type": "string", "description": "Date of signature"}
                },
                "required": ["name"]
            },
            "template": """<div class="signature-block" style="margin: 3rem 0; padding: 2rem; max-width: 350px;">
    <div style="border-bottom: 2px solid #1a1a2e; margin-bottom: 0.75rem; padding-bottom: 3rem;"></div>
    <div style="font-size: 1.125rem; font-weight: 600; color: #1a1a2e;">{{ name }}</div>
    {% if title %}<div style="font-size: 0.875rem; color: #6b7280; margin-top: 0.25rem;">{{ title }}</div>{% endif %}
    {% if company %}<div style="font-size: 0.875rem; color: #6b7280;">{{ company }}</div>{% endif %}
    {% if date %}<div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.75rem;">Date: {{ date }}</div>{% endif %}
</div>"""
        },
        {
            "name": "callout",
            "schema": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["info", "warning", "success", "error"], "default": "info", "description": "Type of callout"},
                    "title": {"type": "string", "description": "Callout title"},
                    "content": {"type": "string", "description": "Callout content"}
                },
                "required": ["content"]
            },
            "template": """{% set colors = {'info': {'bg': '#eff6ff', 'border': '#3b82f6', 'icon': '#2563eb', 'title': '#1e40af'}, 'warning': {'bg': '#fffbeb', 'border': '#f59e0b', 'icon': '#d97706', 'title': '#b45309'}, 'success': {'bg': '#f0fdf4', 'border': '#22c55e', 'icon': '#16a34a', 'title': '#15803d'}, 'error': {'bg': '#fef2f2', 'border': '#ef4444', 'icon': '#dc2626', 'title': '#b91c1c'}} %}
{% set icons = {'info': '&#9432;', 'warning': '&#9888;', 'success': '&#10004;', 'error': '&#10006;'} %}
{% set t = type | default('info') %}
<div class="callout" style="margin: 1.5rem 0; padding: 1rem 1.25rem; background: {{ colors[t]['bg'] }}; border-left: 4px solid {{ colors[t]['border'] }}; border-radius: 0 8px 8px 0;">
    <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
        <span style="font-size: 1.25rem; color: {{ colors[t]['icon'] }}; flex-shrink: 0;">{{ icons[t] | safe }}</span>
        <div style="flex: 1;">
            {% if title %}<div style="font-weight: 600; color: {{ colors[t]['title'] }}; margin-bottom: 0.25rem;">{{ title }}</div>{% endif %}
            <div style="color: #374151; line-height: 1.5;">{{ content }}</div>
        </div>
    </div>
</div>"""
        },
        {
            "name": "image-block",
            "schema": {
                "type": "object",
                "properties": {
                    "src": {"type": "string", "description": "Image URL"},
                    "alt": {"type": "string", "description": "Alt text for accessibility"},
                    "caption": {"type": "string", "description": "Image caption"},
                    "align": {"type": "string", "enum": ["left", "center", "right"], "default": "center", "description": "Image alignment"},
                    "rounded": {"type": "boolean", "description": "Apply rounded corners", "default": True},
                    "shadow": {"type": "boolean", "description": "Apply shadow effect", "default": True}
                },
                "required": ["src"]
            },
            "template": """<figure style="margin: 2rem 0; text-align: {{ align | default('center') }};">
    <img src="{{ src }}" alt="{{ alt | default('') }}" style="max-width: 100%; height: auto; {{ 'border-radius: 12px;' if rounded | default(true) else '' }} {{ 'box-shadow: 0 10px 30px rgba(0,0,0,0.12);' if shadow | default(true) else '' }}" />
    {% if caption %}<figcaption style="margin-top: 0.75rem; font-size: 0.875rem; color: #6b7280; font-style: italic;">{{ caption }}</figcaption>{% endif %}
</figure>"""
        },
        {
            "name": "feature-grid",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Section title"},
                    "subtitle": {"type": "string", "description": "Section subtitle"},
                    "features": {
                        "type": "array",
                        "description": "List of features",
                        "items": {
                            "type": "object",
                            "properties": {
                                "icon": {"type": "string", "description": "Emoji or icon character"},
                                "title": {"type": "string", "description": "Feature title"},
                                "description": {"type": "string", "description": "Feature description"}
                            },
                            "required": ["title", "description"]
                        }
                    }
                },
                "required": ["features"]
            },
            "template": """<div class="feature-grid" style="margin: 3rem 0;">
    {% if title %}<h2 style="text-align: center; margin: 0 0 0.5rem 0; color: #1a1a2e; font-size: 1.75rem; font-weight: 700;">{{ title }}</h2>{% endif %}
    {% if subtitle %}<p style="text-align: center; margin: 0 0 2.5rem 0; color: #6b7280; font-size: 1.1rem;">{{ subtitle }}</p>{% endif %}
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
        {% for feature in features %}
        <div style="padding: 1.5rem; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; transition: box-shadow 0.2s;">
            {% if feature.icon %}<div style="font-size: 2rem; margin-bottom: 0.75rem;">{{ feature.icon }}</div>{% endif %}
            <h3 style="margin: 0 0 0.5rem 0; font-size: 1.125rem; font-weight: 600; color: #1a1a2e;">{{ feature.title }}</h3>
            <p style="margin: 0; font-size: 0.9rem; color: #6b7280; line-height: 1.5;">{{ feature.description }}</p>
        </div>
        {% endfor %}
    </div>
</div>"""
        },
        {
            "name": "testimonial",
            "schema": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string", "description": "Testimonial quote"},
                    "author": {"type": "string", "description": "Author name"},
                    "role": {"type": "string", "description": "Author's role/title"},
                    "company": {"type": "string", "description": "Company name"},
                    "avatar": {"type": "string", "description": "Avatar image URL"}
                },
                "required": ["quote", "author"]
            },
            "template": """<div class="testimonial" style="margin: 2rem 0; padding: 2rem; background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 16px; position: relative;">
    <div style="font-size: 3rem; color: #cbd5e1; position: absolute; top: 1rem; left: 1.5rem; line-height: 1;">"</div>
    <blockquote style="margin: 0; padding: 1rem 0 1.5rem 2rem; font-size: 1.125rem; color: #374151; line-height: 1.7; font-style: italic;">
        {{ quote }}
    </blockquote>
    <div style="display: flex; align-items: center; gap: 1rem; padding-left: 2rem;">
        {% if avatar %}<img src="{{ avatar }}" alt="{{ author }}" style="width: 48px; height: 48px; border-radius: 50%; object-fit: cover;" />{% else %}
        <div style="width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: 600; font-size: 1.125rem;">{{ author[0] | upper }}</div>{% endif %}
        <div>
            <div style="font-weight: 600; color: #1a1a2e;">{{ author }}</div>
            {% if role or company %}<div style="font-size: 0.875rem; color: #6b7280;">{{ role }}{% if role and company %}, {% endif %}{{ company }}</div>{% endif %}
        </div>
    </div>
</div>"""
        },
        {
            "name": "divider",
            "schema": {
                "type": "object",
                "properties": {
                    "style": {"type": "string", "enum": ["solid", "dashed", "dotted", "gradient"], "default": "solid", "description": "Divider style"},
                    "spacing": {"type": "string", "enum": ["small", "medium", "large"], "default": "medium", "description": "Vertical spacing"}
                }
            },
            "template": """{% set spacings = {'small': '1rem', 'medium': '2rem', 'large': '3rem'} %}
{% set s = spacing | default('medium') %}
{% if style == 'gradient' %}
<div style="margin: {{ spacings[s] }} 0; height: 2px; background: linear-gradient(90deg, transparent, #e5e7eb, transparent);"></div>
{% else %}
<hr style="margin: {{ spacings[s] }} 0; border: none; border-top: 1px {{ style | default('solid') }} #e5e7eb;" />
{% endif %}"""
        },
        {
            "name": "stats-row",
            "schema": {
                "type": "object",
                "properties": {
                    "stats": {
                        "type": "array",
                        "description": "Statistics to display",
                        "items": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Stat value (e.g., '100+', '99%')"},
                                "label": {"type": "string", "description": "Stat label"}
                            },
                            "required": ["value", "label"]
                        }
                    }
                },
                "required": ["stats"]
            },
            "template": """<div class="stats-row" style="margin: 2rem 0; display: flex; flex-wrap: wrap; justify-content: center; gap: 2rem;">
    {% for stat in stats %}
    <div style="text-align: center; padding: 1rem 2rem;">
        <div style="font-size: 2.5rem; font-weight: 800; color: var(--primary-color, #3b82f6); line-height: 1;">{{ stat.value }}</div>
        <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">{{ stat.label }}</div>
    </div>
    {% endfor %}
</div>"""
        }
    ]

    for comp_data in builtin_components:
        component = Component(
            name=comp_data["name"],
            schema=comp_data["schema"],
            template=comp_data["template"],
            is_builtin=True,
            is_active=True
        )
        db.session.add(component)

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

    for theme_data in builtin_themes:
        theme = Theme(
            name=theme_data["name"],
            variables=theme_data["variables"],
            is_builtin=True,
            is_default=theme_data["is_default"]
        )
        db.session.add(theme)

    db.session.commit()
