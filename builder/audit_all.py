"""
builder/audit_all.py
Сквозной аудит качества (QA):
1. Проверка кроссплатформенной совместимости имен файлов (Windows, macOS, Linux).
2. Проверка целостности ссылок (0 broken links).
3. Валидность анкоров и структуры.
4. Корректность и синтаксис диаграмм Mermaid.
"""

import os
import re
import sys
import argparse
from urllib.parse import unquote
from typing import List, Dict, Tuple, Set

# Недопустимые символы Windows (NTFS / FAT): < > : " / \ | ? * и управляющие символы 0-31
WIN_FORBIDDEN_CHARS = set("<>:\"/\\|?*")
# Зарезервированные имена устройств DOS / Windows
WIN_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10))
}

class SiteAuditor:
    def __init__(self, dist_dir: str = "./dist", repo_root: str = "."):
        self.dist_dir = os.path.abspath(dist_dir)
        self.repo_root = os.path.abspath(repo_root)
        self.html_files: List[str] = []
        self.broken_links: List[Dict[str, str]] = []
        self.mermaid_errors: List[Dict[str, str]] = []
        self.missing_anchors: List[Dict[str, str]] = []
        self.filename_issues: List[Tuple[str, str]] = []
        self.scanned_dirs_count = 0
        self.scanned_files_count = 0

    def run_audit(self) -> bool:
        print("=====================================================================")
        print(f"🔬 Запуск сквозного аудита качества: {self.dist_dir}")
        print("=====================================================================")

        # 1. Проверка кроссплатформенной совместимости имен файлов
        print("[1/4] 🖥️ Проверка кроссплатформенной совместимости имен файлов (Windows / macOS / Linux)...")
        self._audit_filenames()
        print(f"      Просканировано каталогов: {self.scanned_dirs_count}, файлов: {self.scanned_files_count}")
        if self.filename_issues:
            print(f"      ❌ Найдено несовместимых имен: {len(self.filename_issues)}")
        else:
            print("      ✅ Все имена файлов и папок на 100% совместимы со всеми ОС.")

        if not os.path.exists(self.dist_dir):
            print(f"❌ ОШИБКА: Директория {self.dist_dir} не найдена. Сначала выполните сборку!")
            return False

        # 2. Поиск всех HTML файлов
        for root, _, files in os.walk(self.dist_dir):
            for f in files:
                if f.endswith(".html"):
                    self.html_files.append(os.path.join(root, f))

        print(f"\n[2/4] 📄 Обнаружено HTML страниц: {len(self.html_files)}")
        if not self.html_files:
            print("❌ ОШИБКА: Нет сгенерированных страниц.")
            return False

        # 3. Аудит каждой страницы
        print(f"[3/4] 🔗 Проверка ссылок, анкоров и диаграмм...")
        
        # Кэш известных id для каждого файла
        file_ids_cache: Dict[str, Set[str]] = {}

        for page_path in self.html_files:
            self._audit_single_page(page_path, file_ids_cache)

        # 4. Подведение итогов
        print("\n[4/4] 📊 Результаты проверки:")
        print(f"      Ошибок несовместимости имен файлов: {len(self.filename_issues)}")
        print(f"      Всего проверено страниц: {len(self.html_files)}")
        print(f"      Битых ссылок (Broken Links): {len(self.broken_links)}")
        print(f"      Ошибок анкоров (Missing Anchors): {len(self.missing_anchors)}")
        print(f"      Ошибок диаграмм Mermaid: {len(self.mermaid_errors)}")

        success = True

        if self.filename_issues:
            success = False
            print("\n❌ НАЙДЕНЫ НЕДОПУСТИМЫЕ ИМЕНА ФАЙЛОВ / ПАПОК ДЛЯ WINDOWS:")
            for path, desc in self.filename_issues[:15]:
                print(f"  Файл/Папка: {path}")
                print(f"  Проблема:   {desc}\n")
            if len(self.filename_issues) > 15:
                print(f"  ... и еще {len(self.filename_issues) - 15} ошибок имен файлов.")

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
            print("🎉 АУДИТ ПРОЙДЕН УСПЕШНО! Все имена файлов, ссылки и диаграммы в безупречном состоянии.")
        else:
            print("⚠️ АУДИТ ВЫЯВИЛ ОШИБКИ, требующие внимания.")
        print("=====================================================================")

        return success

    def _audit_filenames(self):
        """Проверяет все файлы и папки репозитория на совместимость с Windows, macOS и Linux."""
        for root, dirs, files in os.walk(self.repo_root):
            # Пропускаем служебные директории
            rel_root = os.path.relpath(root, self.repo_root)
            parts = rel_root.split(os.sep)
            if any(p in {".git", ".idea", ".vscode", "__pycache__"} or p.startswith(".gemini") for p in parts):
                continue

            self.scanned_dirs_count += len(dirs)
            self.scanned_files_count += len(files)

            # 1. Проверка директорий
            for d in dirs:
                d_rel = os.path.join(rel_root, d) if rel_root != "." else d
                # Запрет точек и пробелов в конце
                if d.endswith(" ") or d.endswith("."):
                    self.filename_issues.append((d_rel, f"Имя директории оканчивается точкой или пробелом: {repr(d)}"))
                # Запрещенные символы
                bad = [c for c in d if c in WIN_FORBIDDEN_CHARS or ord(c) < 32]
                if bad:
                    self.filename_issues.append((d_rel, f"Директория содержит недопустимые для Windows символы {bad}: {repr(d)}"))
                # Зарезервированные имена
                base_name = os.path.splitext(d)[0].upper()
                if base_name in WIN_RESERVED_NAMES:
                    self.filename_issues.append((d_rel, f"Имя директории совпадает с зарезервированным именем устройства Windows: {repr(d)}"))

            # 2. Проверка файлов
            for f in files:
                f_rel = os.path.join(rel_root, f) if rel_root != "." else f
                if f.endswith(" ") or f.endswith("."):
                    self.filename_issues.append((f_rel, f"Имя файла оканчивается точкой или пробелом: {repr(f)}"))
                bad = [c for c in f if c in WIN_FORBIDDEN_CHARS or ord(c) < 32]
                if bad:
                    self.filename_issues.append((f_rel, f"Файл содержит недопустимые для Windows символы {bad}: {repr(f)}"))
                base_name = os.path.splitext(f)[0].upper()
                if base_name in WIN_RESERVED_NAMES:
                    self.filename_issues.append((f_rel, f"Имя файла совпадает с зарезервированным именем устройства Windows: {repr(f)}"))

            # 3. Проверка регистронезависимых коллизий в рамках одной директории
            lower_map = {}
            for name in dirs + files:
                low = name.lower()
                if low in lower_map:
                    col_rel = os.path.join(rel_root, name) if rel_root != "." else name
                    self.filename_issues.append((col_rel, f"Регистровый конфликт с {repr(lower_map[low])} на регистронезависимых ФС (Windows/macOS)"))
                else:
                    lower_map[low] = name

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
    parser = argparse.ArgumentParser(description="Аудитор сгенерированного сайта и совместимости имен файлов")
    parser.add_argument("--dist", default="./dist", help="Путь к скомпилированному сайту")
    parser.add_argument("--repo-root", default=".", help="Корень репозитория для проверки имен файлов")
    args = parser.parse_args()

    auditor = SiteAuditor(args.dist, args.repo_root)
    success = auditor.run_audit()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
