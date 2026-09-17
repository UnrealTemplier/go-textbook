"""
builder/converter.py
Преобразование Markdown-статей в чистый семантический HTML5.
Обработка Callouts, Mermaid диаграмм, Prism.js подсветки, Wikilinks и TOC.
"""

import re
import html
from typing import Tuple, Dict, Any, List, Optional
import markdown
from builder.scanner import slugify, Article, KnowledgeBaseScanner

CALLOUT_CONFIG = {
    "tip": {
        "title": "Совет / Собеседование",
        "icon": "💡",
        "class": "callout-tip",
        "color": "var(--accent-emerald)"
    },
    "interview": {
        "title": "Вопрос с собеседования",
        "icon": "🎯",
        "class": "callout-interview",
        "color": "var(--accent-cyan)"
    },
    "info": {
        "title": "Под капотом (Mechanical Sympathy)",
        "icon": "⚙️",
        "class": "callout-info",
        "color": "var(--accent-indigo)"
    },
    "warning": {
        "title": "Подводные камни / Gotcha",
        "icon": "⚠️",
        "class": "callout-warning",
        "color": "var(--accent-amber)"
    },
    "note": {
        "title": "Заметка",
        "icon": "📝",
        "class": "callout-note",
        "color": "var(--accent-cyan)"
    },
    "important": {
        "title": "Важно",
        "icon": "⚡",
        "class": "callout-important",
        "color": "var(--accent-indigo)"
    },
    "caution": {
        "title": "Предостережение",
        "icon": "🛑",
        "class": "callout-caution",
        "color": "var(--accent-rose)"
    },
    "danger": {
        "title": "Опасно",
        "icon": "🚨",
        "class": "callout-danger",
        "color": "var(--accent-rose)"
    }
}

class MarkdownConverter:
    def __init__(self, scanner: KnowledgeBaseScanner):
        self.scanner = scanner
        self.md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "sane_lists",
                "nl2br"
            ]
        )

    def convert_article(self, article: Article) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Полный цикл конвертации статьи из файла .md в HTML.
        Возвращает (html_body, table_of_contents).
        """
        with open(article.source_path, "r", encoding="utf-8", errors="ignore") as fp:
            raw_text = fp.read()

        # 1. Очистка от нейросетевых клише и шаблонных фраз в начале
        cleaned_text = self._clean_cliches(raw_text)

        # 2. Выделение и экранирование блоков Mermaid (чтобы markdown парсер не исказил их)
        mermaid_placeholders: Dict[str, str] = {}
        processed_text = self._extract_mermaid(cleaned_text, mermaid_placeholders)

        # 3. Обработка Obsidian Callouts
        processed_text = self._transform_callouts(processed_text)

        # 4. Преобразование Wikilinks [[...]]
        processed_text = self._transform_wikilinks(processed_text, article)

        # 5. Парсинг заголовков и простановка id-анкоров
        processed_text, toc = self._process_headings(processed_text)

        # 6. Основная конвертация через Python-Markdown
        self.md.reset()
        html_content = self.md.convert(processed_text)

        # 7. Возврат Mermaid блоков на свои места с красивой оберткой
        for ph, m_code in mermaid_placeholders.items():
            html_content = html_content.replace(ph, m_code)

        # 8. Оборачивание таблиц в адаптивный контейнер
        html_content = self._wrap_tables(html_content)

        # 9. Оборачивание блоков кода с кнопкой «Скопировать»
        html_content = self._enhance_code_blocks(html_content)

        return html_content, toc

    def _clean_cliches(self, text: str) -> str:
        """Устранение канцеляризмов и шаблонов в стиле Кернигана."""
        patterns = [
            (r"В современном (?:мире|быстро меняющемся мире)[^,.]*,\s*", ""),
            (r"Важно (?:понимать|помнить|отметить), что\s+", ""),
            (r"Как известно,\s+", ""),
            (r"Не секрет, что\s+", ""),
            (r"Давайте (?:рассмотрим|разберем|погрузимся в)[^.\n]*:\s*", "")
        ]
        for pat, repl in patterns:
            text = re.sub(pat, repl, text, flags=re.IGNORECASE)
        return text

    def _extract_mermaid(self, text: str, placeholders: Dict[str, str]) -> str:
        """Извлечение диаграмм Mermaid и валидация их синтаксиса."""
        pattern = re.compile(r"```mermaid(.*?)```", re.DOTALL | re.IGNORECASE)

        idx = 0
        def repl(match):
            nonlocal idx
            raw_code = match.group(1).strip()
            # Очистка строк от лидирующих цитатных символов '> '
            lines = []
            for l in raw_code.splitlines():
                l = l.strip()
                if l.startswith(">"):
                    l = l.lstrip(">").strip()
                lines.append(l)
            
            clean_code = "\n".join(lines).strip()

            # Валидация и исправление узлов с незакавыченными скобками: A[Text (Info)] -> A["Text (Info)"]
            clean_code = self._sanitize_mermaid(clean_code)

            placeholder = f"<!--MERMAID_PLACEHOLDER_{idx}-->"
            idx += 1

            wrapped_html = f"""
<div class="mermaid-wrapper">
  <div class="mermaid-header">
    <div class="mermaid-title">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
      <span>Архитектурная схема</span>
    </div>
    <button class="btn-mermaid-fullscreen" onclick="toggleMermaidModal(this)" title="Развернуть на весь экран">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
      <span>На весь экран</span>
    </button>
  </div>
  <pre class="mermaid">
{html.escape(clean_code)}
  </pre>
</div>
"""
            placeholders[placeholder] = wrapped_html
            return f"\n\n{placeholder}\n\n"

        return pattern.sub(repl, text)

    def _sanitize_mermaid(self, code: str) -> str:
        """Исправление типичных опечаток в Mermaid."""
        # 1. Если первая строка '>', убираем
        lines = code.splitlines()
        if lines and lines[0].strip() == ">":
            lines = lines[1:]
        
        sanitized_lines = []
        for line in lines:
            # Оборачиваем скобки внутри узлов: id[Text (with parens)] -> id["Text (with parens)"]
            # Ищем квадратные скобки без кавычек внутри, содержащие круглые скобки
            m = re.search(r"(\w+)\s*\[([^\"\]]*\([^\"\]]*\)[^\"\]]*)\]", line)
            if m:
                node_id = m.group(1)
                label = m.group(2)
                line = line.replace(f"{node_id}[{label}]", f'{node_id}["{label}"]')

            # Оборачиваем форму БД: DB[(Database Text)] -> DB[("Database Text")]
            m_db = re.search(r"(\w+)\s*\[\(([^\"\]\)]+)\)\]", line)
            if m_db:
                node_id = m_db.group(1)
                label = m_db.group(2)
                line = line.replace(f"{node_id}[({label})]", f'{node_id}[("{label}")]')

            sanitized_lines.append(line)

        return "\n".join(sanitized_lines)

    def _transform_callouts(self, text: str) -> str:
        """
        Преобразование Obsidian Callouts вида:
        > [!tip] Заголовок
        > Содержимое...
        в HTML контейнеры.
        """
        lines = text.splitlines()
        result_lines = []
        in_callout = False
        callout_type = "note"
        callout_title = ""
        callout_body: List[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]
            # Начало callout
            m_start = re.match(r"^>\s*\[!([a-zA-Z0-9_-]+)\]\s*(.*)$", line)
            if m_start:
                if in_callout:
                    # Закрываем предыдущий callout
                    result_lines.append(self._render_callout_block(callout_type, callout_title, callout_body))
                    callout_body = []

                in_callout = True
                callout_type = m_start.group(1).lower()
                callout_title = m_start.group(2).strip()
                i += 1
                continue

            if in_callout:
                if line.startswith(">"):
                    # Продолжение цитаты callout
                    content = line[1:]
                    if content.startswith(" "):
                        content = content[1:]
                    callout_body.append(content)
                    i += 1
                    continue
                elif line.strip() == "":
                    # Пустая строка может быть внутри или концом callout
                    # Смотрим на следующую строку
                    if i + 1 < len(lines) and lines[i + 1].startswith(">"):
                        callout_body.append("")
                        i += 1
                        continue
                    else:
                        # Завершение callout
                        result_lines.append(self._render_callout_block(callout_type, callout_title, callout_body))
                        result_lines.append("")
                        in_callout = False
                        callout_body = []
                        i += 1
                        continue
                else:
                    # Выход из callout
                    result_lines.append(self._render_callout_block(callout_type, callout_title, callout_body))
                    in_callout = False
                    callout_body = []
                    result_lines.append(line)
                    i += 1
                    continue

            result_lines.append(line)
            i += 1

        if in_callout:
            result_lines.append(self._render_callout_block(callout_type, callout_title, callout_body))

        return "\n".join(result_lines)

    def _render_callout_block(self, callout_type: str, custom_title: str, body_lines: List[str]) -> str:
        """Генерация HTML для отдельного блока Callout."""
        cfg = CALLOUT_CONFIG.get(callout_type, CALLOUT_CONFIG["note"])
        title = custom_title if custom_title else cfg["title"]

        # Если в заголовке или теле есть слова собеседование/интервью, стилизуем под interview
        if "собеседован" in title.lower() or "интервью" in title.lower() or "interview" in title.lower():
            cfg = CALLOUT_CONFIG["interview"]
            if not custom_title:
                title = cfg["title"]

        # Парсим внутренний markdown
        inner_md = "\n".join(body_lines)
        inner_html = self.md.convert(inner_md)
        self.md.reset()

        return f"""
<div class="callout {cfg['class']}">
  <div class="callout-header">
    <span class="callout-icon">{cfg['icon']}</span>
    <span class="callout-title">{html.escape(title)}</span>
  </div>
  <div class="callout-body">
    {inner_html}
  </div>
</div>
"""

    def _transform_wikilinks(self, text: str, current_article: Article) -> str:
        """Преобразование [[Target|Display]] в <a href="..." class="wikilink">."""
        pattern = re.compile(r"\[\[(.*?)\]\]")

        def repl(match):
            raw_link = match.group(1).strip()
            href, display_text = self.scanner.resolve_wikilink(raw_link, current_article.rel_output_path)
            if href:
                return f'<a href="{href}" class="wikilink">{html.escape(display_text)}</a>'
            else:
                return f'<span class="wikilink-unresolved" title="Заметка в разработке">{html.escape(display_text)}</span>'

        return pattern.sub(repl, text)

    def _process_headings(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Добавление id в заголовки H2..H4 и формирование оглавления (TOC)."""
        lines = text.splitlines()
        toc = []
        out_lines = []

        for line in lines:
            m = re.match(r"^(#{2,4})\s+(.+)$", line)
            if m:
                level = len(m.group(1))
                raw_title = m.group(2).strip()
                clean_title = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", raw_title)
                clean_title = re.sub(r"[`*_]", "", clean_title)
                h_slug = slugify(clean_title, 80)
                
                toc.append({
                    "level": level,
                    "title": clean_title,
                    "anchor": h_slug
                })

                # Вставляем явный HTML заголовок с id
                out_lines.append(f'<h{level} id="{h_slug}">{raw_title}</h{level}>')
            else:
                out_lines.append(line)

        return "\n".join(out_lines), toc

    def _wrap_tables(self, html_text: str) -> str:
        """Оборачивание <table> в адаптивный контейнер с горизонтальным скроллом."""
        return re.sub(r"(<table>.*?</table>)", r'<div class="table-container">\1</div>', html_text, flags=re.DOTALL)

    def _enhance_code_blocks(self, html_text: str) -> str:
        """
        Улучшение блоков кода: добавление шапки с языком и кнопкой копирования.
        Поддерживает как блоки с явным языком, так и блоки без языка (text/diagram).
        """
        pattern = re.compile(r'<pre><code(?:\s+class="language-([a-zA-Z0-9_-]+)")?>(.*?)</code></pre>', re.DOTALL)

        def repl(match):
            lang_match = match.group(1)
            code_body = match.group(2)
            
            if lang_match:
                lang = lang_match.lower()
                display_lang = {
                    "go": "Go",
                    "c": "C",
                    "cpp": "C++",
                    "bash": "Bash",
                    "sh": "Shell",
                    "python": "Python",
                    "sql": "SQL",
                    "yaml": "YAML",
                    "json": "JSON",
                    "nasm": "Assembly (x86)",
                    "asm": "Assembly",
                    "text": "Text",
                    "txt": "Text",
                    "ascii": "ASCII Diagram"
                }.get(lang, lang.upper())
            else:
                # Если язык не указан, проверяем наличие символов псевдографики
                ascii_chars = set("┌┐└┘├┤┬┴┼─│═║╔╗╚╝╠╣╦╩╬►◄▲▼")
                if any(c in code_body for c in ascii_chars):
                    lang = "ascii"
                    display_lang = "DIAGRAM"
                else:
                    lang = "text"
                    display_lang = "TEXT"

            return f"""
<div class="code-block" data-lang="{lang}">
  <div class="code-header">
    <span class="code-lang-tag">{display_lang}</span>
    <button class="btn-code-copy" onclick="copyCodeBlock(this)" title="Скопировать">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
      <span>Копировать</span>
    </button>
  </div>
  <pre class="language-{lang}"><code class="language-{lang}">{code_body}</code></pre>
</div>
"""

        return pattern.sub(repl, html_text)
