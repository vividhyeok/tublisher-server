from __future__ import annotations

import html
import unicodedata
from pathlib import Path

import markdown as markdown_lib

from app.core.models import VideoMeta


def markdown_to_html_fragment(markdown_text: str) -> str:
    return markdown_lib.markdown(
        unicodedata.normalize("NFC", markdown_text),
        extensions=["extra", "sane_lists", "toc"],
        output_format="xhtml",
    )


def markdown_to_html_document(markdown_text: str, title: str, meta: VideoMeta) -> str:
    css = _load_css()
    body = markdown_to_html_fragment(markdown_text)
    escaped_title = html.escape(unicodedata.normalize("NFC", title))
    escaped_url = html.escape(meta.webpage_url)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>{css}</style>
</head>
<body>
  <main>
    {body}
    <hr>
    <p class="source">Original Video: <a href="{escaped_url}">{escaped_url}</a></p>
  </main>
</body>
</html>
"""


def _load_css() -> str:
    css_path = Path(__file__).parent / "templates" / "style.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""

