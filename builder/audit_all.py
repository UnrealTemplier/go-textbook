"""
builder/audit_all.py
Сквозной аудит качества (QA): проверка целостности ссылок (0 broken links),
валидности HTML-структуры и корректности Mermaid диаграмм.
"""

import os
import re
import sys
import argparse
from urllib.parse import unquote
from typing import List, Dict, Tuple, Set

class SiteAuditor:
    def __init__(self, dist_dir: str = "./dist"):
        self.dist_dir = os.path.abspath(dist_dir)
        self.html_files: List[str] = []
        self.broken_links: List[Dict[str, str]] = []
        self.mermaid_errors: List[Dict[str, str]] = []
        self.missing_anchors: List[Dict[str, str]] = []

    def run_audit(self) -> bool:
        print("=====================================================================")
        print(f"🔬 Запуск сквозного аудита качества: {self.dist_dir}")
        print("=====================================================================")

        if not os.path.exists(self.dist_dir):
            print(f"❌ ОШИБКА: Директория {self.dist_dir} не найдена. Сначала выполните сборку!")
            return False

        # 1. Поиск всех HTML файлов
        for root, _, files in os.walk(self.dist_dir):
            for f in files:
                if f.endswith(".html"):
                    self.html_files.append(os.path.join(root, f))

        print(f"[1/3] 📄 Обнаружено HTML страниц: {len(self.html_files)}")
        if not self.html_files:
            print("❌ ОШИБКА: Нет сгенерированных страниц.")
            return False

        # 2. Аудит каждой страницы
        print(f"[2/3] 🔗 Проверка ссылок, анкоров и диаграмм...")
        
        # Кэш известных id для каждого файла
        file_ids_cache: Dict[str, Set[str]] = {}

        for page_path in self.html_files:
            self._audit_single_page(page_path, file_ids_cache)

        # 3. Подведение итогов
        print("\n[3/3] 📊 Результаты проверки:")
        print(f"      Всего проверено страниц: {len(self.html_files)}")
        print(f"      Битых ссылок (Broken Links): {len(self.broken_links)}")
        print(f"      Ошибок анкоров (Missing Anchors): {len(self.missing_anchors)}")
        print(f"      Ошибок диаграмм Mermaid: {len(self.mermaid_errors)}")

        success = True

        if self.broken_links:
            success = False
            print("\n❌ НАЙДЕНЫ БИТЫЕ ССЫЛКИ:")
            for item in self.broken_links[:10]:
                print(f"  В файле: {os.path.relpath(item['source'], self.dist_dir)}")
                print(f"  Цель:    {item['target']}")
                print(f"  Ссылка:  {item['raw_href']}\n")
            if len(self.broken_links) > 10:
                print(f"  ... и еще {len(self.broken_links) - 10} битых ссылок.")

        if self.missing_anchors:
            print(f"\n⚠️ Замечания по анкорам (#anchor): {len(self.missing_anchors)} штук.")
            for item in self.missing_anchors[:5]:
                print(f"  В файле: {os.path.relpath(item['source'], self.dist_dir)} -> {item['raw_href']}")

        if self.mermaid_errors:
            success = False
            print("\n❌ ОШИБКИ В ДИАГРАММАХ MERMAID:")
            for err in self.mermaid_errors[:10]:
                print(f"  В файле: {os.path.relpath(err['file'], self.dist_dir)}")
                print(f"  Причина: {err['reason']}\n")

        print("=====================================================================")
        if success:
            print("🎉 АУДИТ ПРОЙДЕН УСПЕШНО! Все ссылки и диаграммы в безупречном состоянии.")
        else:
            print("⚠️ АУДИТ ВЫЯВИЛ ОШИБКИ, требующие внимания.")
        print("=====================================================================")

        return success

    def _audit_single_page(self, page_path: str, file_ids_cache: Dict[str, Set[str]]):
        with open(page_path, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()

        # Извлекаем все id в текущем файле
        ids_in_page = set(re.findall(r'id=["\']([^"\']+)["\']', content))
        file_ids_cache[page_path] = ids_in_page

        # Проверяем ссылки <a href="...">
        hrefs = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', content)
        page_dir = os.path.dirname(page_path)

        for href in hrefs:
            href_clean = href.strip()
            # Пропускаем внешние протоколы и javascript
            if href_clean.startswith(("http://", "https://", "mailto:", "javascript:", "tel:")):
                continue

            if href_clean.startswith("#"):
                # Анкор на текущей странице
                anchor = unquote(href_clean[1:])
                if anchor and anchor not in ids_in_page:
                    self.missing_anchors.append({
                        "source": page_path,
                        "raw_href": href_clean
                    })
                continue

            # Относительный путь к файлу
            parts = href_clean.split("#", 1)
            file_part = parts[0]
            anchor_part = parts[1] if len(parts) > 1 else ""

            target_file_path = os.path.normpath(os.path.join(page_dir, unquote(file_part)))
            if not os.path.exists(target_file_path):
                self.broken_links.append({
                    "source": page_path,
                    "target": target_file_path,
                    "raw_href": href_clean
                })
            elif anchor_part:
                # Проверим анкор в целевом файле
                if target_file_path not in file_ids_cache:
                    with open(target_file_path, "r", encoding="utf-8", errors="ignore") as tfp:
                        file_ids_cache[target_file_path] = set(re.findall(r'id=["\']([^"\']+)["\']', tfp.read()))
                
                target_ids = file_ids_cache[target_file_path]
                if unquote(anchor_part) not in target_ids:
                    self.missing_anchors.append({
                        "source": page_path,
                        "raw_href": href_clean
                    })

        # Проверяем блоки Mermaid
        mermaid_blocks = re.findall(r'<pre class="mermaid">(.*?)</pre>', content, re.DOTALL)
        for b in mermaid_blocks:
            clean_b = b.strip()
            if not clean_b:
                self.mermaid_errors.append({
                    "file": page_path,
                    "reason": "Пустой блок Mermaid"
                })
                continue

            first_line = clean_b.splitlines()[0].strip()
            valid_headers = (
                "flowchart", "graph", "sequencediagram", "classdiagram",
                "statediagram", "statediagram-v2", "erdiagram", "gantt",
                "pie", "gitgraph", "c4context", "mindmap", "timeline",
                "xychart-beta", "block-beta"
            )
            
            header_cmd = first_line.split()[0].lower() if first_line.split() else ""
            if header_cmd not in valid_headers:
                self.mermaid_errors.append({
                    "file": page_path,
                    "reason": f"Неизвестный тип диаграммы Mermaid: \"{first_line[:40]}\""
                })

def main():
    parser = argparse.ArgumentParser(description="Аудитор сгенерированного сайта")
    parser.add_argument("--dist", default="./dist", help="Путь к скомпилированному сайту")
    args = parser.parse_args()

    auditor = SiteAuditor(args.dist)
    success = auditor.run_audit()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
