# Docsly

Docsly is a markdown-first composable document builder with:

- Custom components (`:::component-name ... :::`)
- Built-in layout blocks (`row`, `column`, `table`)
- Theme-driven centralized styling
- Live preview powered by a markdown parser + component renderer
- MCP HTTP server for programmatic automation

## Project Structure

- `backend/`: Flask API, renderer, component registry, MCP server
- `frontend/`: Next.js editor, component designer, theme editor
- `docker-compose.yml`: local stack
- `Makefile`: common commands

## Quick Start

```bash
docker-compose up --build
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5000`
- MCP server: `http://localhost:5001`

## Database Reset

Re-seed built-in themes/components:

```bash
make reset-db
```

This runs:

```bash
docker-compose exec backend sh -lc "PYTHONPATH=/app python scripts/reset_db.py"
```

## Markdown + Components

Document content is stored as markdown:

```json
{
  "version": "2.0",
  "theme_id": 1,
  "markdown": "# Proposal\n\n:::proposal-cover v=1\nclient_name=\"Acme\"\n:::"
}
```

Custom component fence format:

```md
:::component_name v=1
key=value
key2=["a","b"]
:::
```

## MCP Docs

See full MCP integration docs here:

- [backend/MCP.md](/Users/arpan-zethic/OSS/Docsly/backend/MCP.md)

Backend API notes:

- [backend/API.md](/Users/arpan-zethic/OSS/Docsly/backend/API.md)
