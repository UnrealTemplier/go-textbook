"""
builder/build_all.py
Главный сборочный конвейер инженерной веб-энциклопедии бэкенда (Go & CS).
Поддержка режимов --all, --pilot, --module N, --limit N.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import shutil
import time
import json
import argparse
from typing import List, Optional

from builder.scanner import KnowledgeBaseScanner, Article
from builder.converter import MarkdownConverter
from builder.template import render_article_page, render_index_page

def copy_assets(builder_assets_dir: str, dist_assets_dir: str):
    """Копирование статических ассетов (CSS, JS, Vendor) в dist/assets/."""
    os.makedirs(dist_assets_dir, exist_ok=True)
    if not os.path.exists(builder_assets_dir):
        print(f"[WARN] Builder assets directory not found: {builder_assets_dir}")
        return

    for root, dirs, files in os.walk(builder_assets_dir):
        rel = os.path.relpath(root, builder_assets_dir)
        target_dir = os.path.join(dist_assets_dir, rel) if rel != "." else dist_assets_dir
        os.makedirs(target_dir, exist_ok=True)
        for f in files:
            src_f = os.path.join(root, f)
            dst_f = os.path.join(target_dir, f)
            shutil.copy2(src_f, dst_f)

def generate_search_data_js(articles: List[Article], dist_dir: str):
    """
    Генерация поискового индекса в виде search-data.js.
    Позволяет поиску работать локально через протокол file:/// без блокировок CORS.
    """
    search_items = []
    for art in articles:
        search_items.append({
            "title": art.title,
            "url": art.rel_output_path,
            "module": art.module_name,
            "sub": art.subsection_name,
            "num": art.module_num
        })

    js_content = f"window.SEARCH_DATA = {json.dumps(search_items, ensure_ascii=False, indent=2)};\n"
    assets_dir = os.path.join(dist_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    with open(os.path.join(assets_dir, "search-data.js"), "w", encoding="utf-8") as fp:
        fp.write(js_content)

def build(
    sources_dir: str = "./sources",
    dist_dir: str = "./dist",
    limit: Optional[int] = None,
    target_module: Optional[int] = None,
    is_pilot: bool = False
):
    start_time = time.time()
    print("=====================================================================")
    print("🚀 Старт сборки Инженерной веб-энциклопедии бэкенда (Go Workout Style)")
    print("=====================================================================")

    # 1. Сканирование базы знаний
    print(f"\n[1/4] 🔍 Сканирование директории {sources_dir}...")
    scanner = KnowledgeBaseScanner(sources_dir)
    all_articles = scanner.scan()
    print(f"      Всего обнаружено статей: {len(all_articles)}")
    print(f"      Всего модулей: {len(scanner.modules_tree)}")

    # Фильтрация если указан --pilot, --limit или --module
    articles_to_build = all_articles
    if is_pilot:
        # Пилотный режим: первые 15 статей Модуля 1
        articles_to_build = [a for a in all_articles if a.module_num == 1][:15]
        print(f"      🔥 Режим ПИЛОТА: выбрано первых {len(articles_to_build)} статей Модуля 1")
    elif target_module is not None:
        articles_to_build = [a for a in all_articles if a.module_num == target_module]
        if limit:
            articles_to_build = articles_to_build[:limit]
        print(f"      🎯 Выбран модуль {target_module}: {len(articles_to_build)} статей")
    elif limit is not None:
        articles_to_build = all_articles[:limit]
        print(f"      ⚠️ Ограничение сборки: первые {limit} статей")

    # 2. Подготовка директорий и копирование ассетов
    print(f"\n[2/4] 📦 Подготовка директории {dist_dir} и копирование ассетов...")
    builder_assets = os.path.join(os.path.dirname(__file__), "assets")
    dist_assets = os.path.join(dist_dir, "assets")
    copy_assets(builder_assets, dist_assets)
    generate_search_data_js(all_articles, dist_dir)
    
    # Копирование favicon в корень dist/ и в dist/assets/
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for fav in ["favicon.svg", "favicon.ico"]:
        src_fav = os.path.join(repo_root, fav)
        if os.path.exists(src_fav):
            shutil.copy2(src_fav, os.path.join(dist_dir, fav))
            shutil.copy2(src_fav, os.path.join(dist_assets, fav))
    print("      Ассеты, иконки favicon и файл search-data.js успешно развернуты.")

    # 3. Конвертация Markdown и генерация HTML страниц
    print(f"\n[3/4] ⚙️ Конвертация {len(articles_to_build)} статей в HTML...")
    converter = MarkdownConverter(scanner)
    built_count = 0
    total_mermaid_rendered = 0

    for i, art in enumerate(articles_to_build, 1):
        full_out_path = os.path.join(dist_dir, art.rel_output_path)
        os.makedirs(os.path.dirname(full_out_path), exist_ok=True)

        # Конвертация
        html_content, toc = converter.convert_article(art)
        
        # Рендеринг полного каркаса страницы
        page_html = render_article_page(
            article=art,
            article_html=html_content,
            toc=toc,
            modules_tree=scanner.modules_tree,
            total_articles=len(all_articles)
        )

        with open(full_out_path, "w", encoding="utf-8") as fp:
            fp.write(page_html)

        built_count += 1
        total_mermaid_rendered += art.mermaid_count

        if i % 10 == 0 or i == len(articles_to_build):
            print(f"      Собрано: [{i:4d}/{len(articles_to_build)}] {art.title[:45]}...")

    # 4. Генерация главной страницы (index.html)
    print("\n[4/4] 🏠 Генерация главной страницы (index.html)...")
    index_html = render_index_page(
        modules_tree=scanner.modules_tree,
        total_articles=len(all_articles),
        total_mermaid=sum(a.mermaid_count for a in all_articles)
    )
    index_path = os.path.join(dist_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as fp:
        fp.write(index_html)
    print("      index.html успешно создан.")

    elapsed = time.time() - start_time
    print("\n=====================================================================")
    print(f"✅ СБОРКА УСПЕШНО ЗАВЕРШЕНА за {elapsed:.2f} сек!")
    print(f"   Сгенерировано страниц: {built_count}")
    print(f"   Отрендерено диаграмм Mermaid: {total_mermaid_rendered}")
    print(f"   Выходная директория: {os.path.abspath(dist_dir)}")
    print(f"   Главная страница: file://{os.path.abspath(index_path)}")
    print("=====================================================================")

def main():
    parser = argparse.ArgumentParser(description="Сборщик Инженерной веб-энциклопедии бэкенда")
    parser.add_argument("--all", action="store_true", help="Собрать все 1 413 статей")
    parser.add_argument("--pilot", action="store_true", help="Собрать пилотную версию (первые 15 статей Модуля 1)")
    parser.add_argument("--module", type=int, help="Собрать конкретный номер модуля (1..22)")
    parser.add_argument("--limit", type=int, help="Ограничить количество собираемых статей")
    parser.add_argument("--sources", default="./sources", help="Путь к исходникам (по умолчанию ./sources)")
    parser.add_argument("--dist", default="./dist", help="Выходная папка (по умолчанию ./dist)")

    args = parser.parse_args()

    # По умолчанию, если ничего не передано, собираем пилот
    is_pilot = args.pilot or (not args.all and args.module is None and args.limit is None)

    build(
        sources_dir=args.sources,
        dist_dir=args.dist,
        limit=args.limit,
        target_module=args.module,
        is_pilot=is_pilot
    )

if __name__ == "__main__":
    main()
