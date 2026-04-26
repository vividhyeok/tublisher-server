from __future__ import annotations

import unicodedata
from pathlib import Path

from ebooklib import epub

from app.core.errors import EpubBuildError
from app.core.models import VideoMeta
from app.renderers.html_renderer import markdown_to_html_fragment


class EpubBuilder:
    def build(
        self,
        epub_path: Path,
        title: str,
        markdown: str,
        meta: VideoMeta,
        source_url: str,
        language: str = "ko",
    ) -> Path:
        try:
            epub_path.parent.mkdir(parents=True, exist_ok=True)
            normalized_title = unicodedata.normalize("NFC", title)
            body = markdown_to_html_fragment(markdown)
            css = _load_css()

            book = epub.EpubBook()
            book.set_identifier(meta.video_id)
            book.set_title(normalized_title)
            book.set_language(language)
            book.add_author("Tublisher AI")

            chapter = epub.EpubHtml(title=normalized_title, file_name="chap_01.xhtml", lang=language)
            chapter.set_content(f"""<html lang="{language}">
<head>
  <meta charset="utf-8">
  <title>{normalized_title}</title>
  <style>{css}</style>
</head>
<body>
  {body}
  <hr>
  <p class="source">Original Video: {source_url}</p>
</body>
</html>""")

            book.add_item(chapter)
            book.toc = (epub.Link("chap_01.xhtml", normalized_title, "intro"),)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = ["nav", chapter]
            epub.write_epub(str(epub_path), book)
        except Exception as exc:
            raise EpubBuildError(str(exc)) from exc
        return epub_path


def _load_css() -> str:
    css_path = Path(__file__).parent / "templates" / "style.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""
