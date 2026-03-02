from __future__ import annotations


def render_pdf_from_html(html: str) -> bytes:
    """Render HTML into PDF bytes using WeasyPrint."""
    if not isinstance(html, str) or not html.strip():
        return b""

    try:
        from weasyprint import HTML  # Lazy import so app can boot even if runtime libs are missing
    except Exception as exc:
        raise RuntimeError(
            "WeasyPrint is not available in runtime. Install required system libraries "
            "(including libpangoft2-1.0-0) and rebuild backend/mcp images."
        ) from exc

    return HTML(string=html).write_pdf()
