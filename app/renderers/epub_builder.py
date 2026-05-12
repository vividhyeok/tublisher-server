from __future__ import annotations

import re
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
            css = _load_css()
            sections = _split_markdown_by_h2(markdown, normalized_title)

            book = epub.EpubBook()
            book.set_identifier(meta.video_id)
            book.set_title(normalized_title)
            book.set_language(language)
            book.add_author("Tublisher AI")

            chapters: list[epub.EpubHtml] = []
            toc_items: list[epub.Link] = []
            for index, (section_title, section_markdown) in enumerate(sections, start=1):
                body = markdown_to_html_fragment(section_markdown)
                chapter = epub.EpubHtml(title=section_title, file_name=f"chap_{index:02d}.xhtml", lang=language)
                source_footer = f"<hr><p class=\"source\">Original Video: {source_url}</p>" if index == len(sections) else ""
                chapter.set_content(f"""<html lang="{language}">
<head>
  <meta charset="utf-8">
  <title>{section_title}</title>
  <style>{css}</style>
</head>
<body>
  {body}
  {source_footer}
</body>
</html>""")
                book.add_item(chapter)
                chapters.append(chapter)
                toc_items.append(epub.Link(chapter.file_name, section_title, f"section-{index}"))

            book.toc = tuple(toc_items)
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = ["nav", *chapters]
            epub.write_epub(str(epub_path), book)
        except Exception as exc:
            raise EpubBuildError(str(exc)) from exc
        return epub_path


def _split_markdown_by_h2(markdown: str, fallback_title: str) -> list[tuple[str, str]]:
    normalized = unicodedata.normalize("NFC", markdown).strip()
    if not normalized:
        return [(fallback_title, f"# {fallback_title}\n\n내용이 없습니다.")]

    matches = list(re.finditer(r"(?m)^##\s+(.+)$", normalized))
    if not matches:
        return [(fallback_title, normalized)]

    sections: list[tuple[str, str]] = []
    first_start = matches[0].start()
    preface = normalized[:first_start].strip()
    if preface:
        sections.append(("프롤로그", preface))

    for index, match in enumerate(matches):
        section_title = match.group(1).strip()
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        section_markdown = normalized[start:end].strip()
        sections.append((section_title or f"섹션 {index + 1}", section_markdown))

    return sections


def _load_css() -> str:
    css_path = Path(__file__).parent / "templates" / "style.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""
