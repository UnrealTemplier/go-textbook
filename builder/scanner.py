"""
builder/scanner.py
Сканирование исходников ./sources, построение иерархической модели,
формирование путей и резолвер внутренних ссылок (wikilinks).
"""

import os
import re
from typing import Dict, List, Optional, Tuple, Any

CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
    'я': 'ya'
}

def natural_sort_key(s: str) -> List[Any]:
    """Сортировка строк с учетом чисел (1, 2, 10 вместо 1, 10, 2)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]

def slugify(text: str, max_length: int = 60) -> str:
    """Генерация чистого URL-friendly slug из кириллицы/латиницы."""
    text = text.lower().strip()
    result = []
    for ch in text:
        if ch in CYRILLIC_TO_LATIN:
            result.append(CYRILLIC_TO_LATIN[ch])
        elif ch.isalnum():
            result.append(ch)
        elif ch in [' ', '-', '_', '.']:
            result.append('-')
    slug = "".join(result)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "item"
    return slug[:max_length].rstrip("-")

def normalize_key(text: str) -> str:
    """Нормализация строки для нечеткого сопоставления ссылок."""
    text = text.lower().strip()
    if text.endswith(".md"):
        text = text[:-3]
    text = re.sub(r"[^\w\sа-яёa-z0-9]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def extract_headings(content: str) -> List[Tuple[int, str, str]]:
    """Извлечение всех заголовков H2, H3, H4 и их slug-анкоров."""
    headings = []
    for line in content.splitlines():
        line = line.strip()
        m = re.match(r"^(#{2,4})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            raw_title = m.group(2).strip()
            clean_title = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", raw_title)
            clean_title = re.sub(r"[`*_]", "", clean_title)
            anchor = slugify(clean_title, max_length=80)
            headings.append((level, raw_title, anchor))
    return headings

class Article:
    def __init__(
        self,
        title: str,
        source_path: str,
        rel_output_path: str,
        module_num: int,
        module_name: str,
        subsection_name: str = "",
        global_order: int = 0
    ):
        self.title = title
        self.source_path = source_path
        self.rel_output_path = rel_output_path
        self.module_num = module_num
        self.module_name = module_name
        self.subsection_name = subsection_name
        self.global_order = global_order
        
        self.headings: List[Tuple[int, str, str]] = []
        self.prev_article: Optional['Article'] = None
        self.next_article: Optional['Article'] = None
        self.size_bytes: int = 0
        self.mermaid_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "rel_output_path": self.rel_output_path,
            "module_num": self.module_num,
            "module_name": self.module_name,
            "subsection_name": self.subsection_name,
            "global_order": self.global_order,
            "size_bytes": self.size_bytes,
            "mermaid_count": self.mermaid_count,
            "headings": [{"level": h[0], "title": h[1], "anchor": h[2]} for h in self.headings]
        }

class KnowledgeBaseScanner:
    def __init__(self, sources_dir: str):
        self.sources_dir = os.path.abspath(sources_dir)
        self.articles: List[Article] = []
        self.articles_by_path: Dict[str, Article] = {}
        self.wikilink_index: Dict[str, Article] = {}
        self.modules_tree: List[Dict[str, Any]] = []

    def scan(self) -> List[Article]:
        """Полное сканирование базы знаний и построение графа связей."""
        top_dirs = sorted(
            [d for d in os.listdir(self.sources_dir) if os.path.isdir(os.path.join(self.sources_dir, d))],
            key=natural_sort_key
        )

        global_order = 0
        modules_tree = []

        for top_dir in top_dirs:
            m_match = re.match(r"^(\d+)\.\s*(.*)$", top_dir)
            if m_match:
                module_num = int(m_match.group(1))
                module_clean_title = m_match.group(2).strip()
            else:
                module_num = 99
                module_clean_title = top_dir

            mod_slug = f"{module_num:02d}-{slugify(module_clean_title, 35)}"
            full_mod_path = os.path.join(self.sources_dir, top_dir)
            
            module_node = {
                "num": module_num,
                "raw_name": top_dir,
                "title": module_clean_title,
                "slug": mod_slug,
                "subsections": [],
                "articles": []
            }

            entries = sorted(os.listdir(full_mod_path), key=natural_sort_key)
            subdirs = [e for e in entries if os.path.isdir(os.path.join(full_mod_path, e))]
            root_files = [e for e in entries if os.path.isfile(os.path.join(full_mod_path, e)) and e.endswith(".md")]

            # Если в корне модуля есть статьи
            if root_files:
                for rf in root_files:
                    global_order += 1
                    file_src = os.path.join(full_mod_path, rf)
                    raw_title = rf[:-3] if rf.endswith(".md") else rf
                    file_slug = slugify(raw_title, 55)
                    rel_out = f"docs/{mod_slug}/{file_slug}.html"

                    art = Article(
                        title=raw_title,
                        source_path=file_src,
                        rel_output_path=rel_out,
                        module_num=module_num,
                        module_name=top_dir,
                        subsection_name="",
                        global_order=global_order
                    )
                    self._populate_article_stats(art)
                    self.articles.append(art)
                    self.articles_by_path[rel_out] = art
                    module_node["articles"].append(art)

            # Если есть вложенные поддиректории
            for sd in subdirs:
                sd_path = os.path.join(full_mod_path, sd)
                sd_entries = sorted(os.listdir(sd_path), key=natural_sort_key)
                sub_subdirs = [e for e in sd_entries if os.path.isdir(os.path.join(sd_path, e))]
                sd_files = [e for e in sd_entries if os.path.isfile(os.path.join(sd_path, e)) and e.endswith(".md")]

                if sub_subdirs:
                    for ssd in sub_subdirs:
                        ssd_path = os.path.join(sd_path, ssd)
                        ssd_files = [e for e in sorted(os.listdir(ssd_path), key=natural_sort_key) if e.endswith(".md")]
                        sub_sec_name = f"{sd} / {ssd}"
                        sub_slug = f"{slugify(sd, 20)}/{slugify(ssd, 25)}"
                        
                        sub_node = {
                            "name": sub_sec_name,
                            "slug": sub_slug,
                            "articles": []
                        }

                        for sf in ssd_files:
                            global_order += 1
                            file_src = os.path.join(ssd_path, sf)
                            raw_title = sf[:-3] if sf.endswith(".md") else sf
                            file_slug = slugify(raw_title, 55)
                            rel_out = f"docs/{mod_slug}/{sub_slug}/{file_slug}.html"

                            art = Article(
                                title=raw_title,
                                source_path=file_src,
                                rel_output_path=rel_out,
                                module_num=module_num,
                                module_name=top_dir,
                                subsection_name=sub_sec_name,
                                global_order=global_order
                            )
                            self._populate_article_stats(art)
                            self.articles.append(art)
                            self.articles_by_path[rel_out] = art
                            sub_node["articles"].append(art)

                        module_node["subsections"].append(sub_node)
                else:
                    sub_slug = slugify(sd, 35)
                    sub_node = {
                        "name": sd,
                        "slug": sub_slug,
                        "articles": []
                    }
                    for sf in sd_files:
                        global_order += 1
                        file_src = os.path.join(sd_path, sf)
                        raw_title = sf[:-3] if sf.endswith(".md") else sf
                        file_slug = slugify(raw_title, 55)
                        rel_out = f"docs/{mod_slug}/{sub_slug}/{file_slug}.html"

                        art = Article(
                            title=raw_title,
                            source_path=file_src,
                            rel_output_path=rel_out,
                            module_num=module_num,
                            module_name=top_dir,
                            subsection_name=sd,
                            global_order=global_order
                        )
                        self._populate_article_stats(art)
                        self.articles.append(art)
                        self.articles_by_path[rel_out] = art
                        sub_node["articles"].append(art)

                    module_node["subsections"].append(sub_node)

            modules_tree.append(module_node)

        for i in range(len(self.articles)):
            if i > 0:
                self.articles[i].prev_article = self.articles[i - 1]
            if i < len(self.articles) - 1:
                self.articles[i].next_article = self.articles[i + 1]

        self.modules_tree = modules_tree
        self._build_wikilink_index()
        return self.articles

    def _populate_article_stats(self, art: Article) -> None:
        try:
            art.size_bytes = os.path.getsize(art.source_path)
            with open(art.source_path, "r", encoding="utf-8", errors="ignore") as fp:
                content = fp.read()
            art.headings = extract_headings(content)
            art.mermaid_count = len(re.findall(r"```mermaid", content, re.IGNORECASE))
        except Exception:
            pass

    def _build_wikilink_index(self) -> None:
        for art in self.articles:
            self.wikilink_index[art.title] = art
            self.wikilink_index[art.title + ".md"] = art

            norm = normalize_key(art.title)
            self.wikilink_index[norm] = art

            m = re.match(r"^\d+\.\s*(.+)$", art.title)
            if m:
                clean = m.group(1).strip()
                self.wikilink_index[clean] = art
                self.wikilink_index[normalize_key(clean)] = art

    def resolve_wikilink(self, link_raw: str, current_output_rel: str) -> Tuple[Optional[str], str]:
        if "|" in link_raw:
            parts = link_raw.split("|", 1)
            target_part = parts[0].strip()
            display_text = parts[1].strip()
        else:
            target_part = link_raw.strip()
            display_text = target_part

        if "#" in target_part:
            t_parts = target_part.split("#", 1)
            target_name = t_parts[0].strip()
            anchor_name = t_parts[1].strip()
            anchor_slug = "#" + slugify(anchor_name)
        else:
            target_name = target_part
            anchor_slug = ""

        if not target_name:
            clean_display = display_text.lstrip("#")
            return anchor_slug, clean_display

        art = self.wikilink_index.get(target_name)
        if not art:
            art = self.wikilink_index.get(normalize_key(target_name))
        
        if not art:
            m = re.match(r"^\d+\.\s*(.+)$", target_name)
            if m:
                art = self.wikilink_index.get(normalize_key(m.group(1)))

        if art:
            curr_dir = os.path.dirname(current_output_rel)
            rel_href = os.path.relpath(art.rel_output_path, curr_dir).replace("\\", "/")
            full_href = rel_href + anchor_slug
            if display_text == target_part:
                display_text = art.title
            return full_href, display_text

        return None, display_text
