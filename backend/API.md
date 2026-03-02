# Backend API Notes

This file documents key endpoints used by the frontend editor/designer.

## Auth

Most `/api/*` routes require JWT auth (`Authorization: Bearer <token>`).

## Components

Base route: `/api/components`

- `GET /api/components`
- `GET /api/components/<id>`
- `GET /api/components/name/<name>`
- `POST /api/components`
- `PUT /api/components/<id>`
- `DELETE /api/components/<id>`
- `POST /api/components/preview`
- `POST /api/components/preview-template`

### `POST /api/components/preview-template`

Request:

```json
{
  "name": "scope-table",
  "template": "## {{ title }}",
  "props": { "title": "Scope of Work" },
  "style_contract": { "slots": ["root"], "variants": ["default"] },
  "default_styles": {
    "base": {},
    "slots": { "root": {} },
    "elements": { "h2": { "font-size": "1.5rem" } },
    "variants": {}
  },
  "theme": {}
}
```

Response:

```json
{
  "html": "<section ...>...</section>",
  "meta": {
    "interpolated_markdown": "## Scope of Work",
    "rendered_tags": ["h2"],
    "markdown_outline": [{ "type": "heading", "tag": "h2", "level": 0 }],
    "token_types": ["heading_open", "inline", "heading_close"],
    "inline_tags": [],
    "placeholders": ["title"],
    "unresolved_placeholders": [],
    "contract_slots": ["root"],
    "declared_slots": ["root"],
    "undeclared_slots": [],
    "extra_slots": [],
    "contract_variants": ["default"],
    "declared_variants": [],
    "undeclared_variants": ["default"],
    "extra_variants": [],
    "element_selectors": ["h2"],
    "styled_rendered_tags": ["h2"],
    "unstyled_rendered_tags": []
  }
}
```

Purpose:

- UI accuracy for component designer
- clear mapping between markdown, rendered HTML tags, and element styles
- contract mismatch visibility (slots/variants)

## Documents

Base route: `/api/documents`

Document content format:

```json
{
  "version": "2.0",
  "theme_id": 1,
  "markdown": "# Title\n\n:::proposal-cover\nclient_name=\"Acme\"\n:::"
}
```

The renderer supports:

- standard markdown
- custom component fences (`:::name ... :::`)
- shortcode syntax for built-ins (`row`, `column`, `table`)

### PDF Export

- `GET /api/documents/<id>/pdf`
  - Auth: JWT required
  - Response: `application/pdf` attachment
- `POST /api/documents/preview-pdf`
  - Auth: JWT required
  - Body:

```json
{
  "title": "Proposal",
  "content": { "version": "2.0", "theme_id": null, "markdown": "# Title" }
}
```

  - Response: `application/pdf` attachment
