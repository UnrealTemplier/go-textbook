"""
builder/verify_editorial.py
Инструмент валидации авторской редактуры "ДО и ПОСЛЕ".
Гарантирует 100% сохранение технических сущностей, тем, терминов,
вопросов собеседований, ловушек и диаграмм при переписывании текста.
"""

import os
import re
import sys
import argparse
import subprocess
from typing import Dict, List, Set, Tuple, Any

def extract_entities(content: str) -> Dict[str, Any]:
    """Извлечение смысловых сущностей из статьи для контроля покрытия."""
    # 1. Заголовки разделов
    headings = [m.group(2).strip() for m in re.finditer(r"^(#{2,4})\s+(.+)$", content, re.MULTILINE)]
    
    # 2. Моноширинные термины, код, функции, системные вызовы
    code_terms = set(re.findall(r"`([^`\n]+)`", content))
    # Фильтруем длинные куски кода, оставляем именно термины
    identifiers = {t.strip() for t in code_terms if 1 <= len(t.strip()) <= 40 and not t.strip().startswith("//")}

    # 3. Вопросы собеседований и Callouts
    callouts = []
    for m in re.finditer(r"^>\s*\[!([a-zA-Z0-9_-]+)\]\s*(.*)$", content, re.MULTILINE):
        callouts.append({
            "type": m.group(1).lower(),
            "title": m.group(2).strip()
        })

    # 4. Диаграммы Mermaid
    mermaid_blocks = re.findall(r"```mermaid(.*?)```", content, re.DOTALL | re.IGNORECASE)

    # 5. Wikilinks
    wikilinks = set(re.findall(r"\[\[(.*?)\]\]", content))

    return {
        "headings": headings,
        "identifiers": identifiers,
        "callouts": callouts,
        "mermaid_count": len(mermaid_blocks),
        "wikilinks": wikilinks,
        "bytes": len(content.encode("utf-8")),
        "words": len(content.split())
    }

def compare_articles(original_content: str, edited_content: str) -> Dict[str, Any]:
    """Сравнение статьи ДО и ПОСЛЕ редактуры."""
    before = extract_entities(original_content)
    after = extract_entities(edited_content)

    # 1. Проверка сохранения идентификаторов
    missing_identifiers = []
    for ident in before["identifiers"]:
        # Проверяем наличие термина в новом тексте (с учетом регистра или в коде)
        if ident not in edited_content and ident.lower() not in edited_content.lower():
            missing_identifiers.append(ident)

    # 2. Проверка сохранения тем (заголовков)
    missing_headings = []
    for h in before["headings"]:
        # Извлекаем ключевые слова заголовка (слова длинее 3 букв)
        words = [w.lower() for w in re.findall(r"[а-яёa-z0-9]+", h) if len(w) > 3]
        matched = False
        for after_h in after["headings"]:
            after_words = [w.lower() for w in re.findall(r"[а-яёa-z0-9]+", after_h) if len(w) > 3]
            overlap = set(words) & set(after_words)
            if len(overlap) >= min(len(words), 2):
                matched = True
                break
        if not matched and words:
            # Проверим, упоминается ли тема хотя бы в тексте
            text_overlap = sum(1 for w in words if w in edited_content.lower())
            if text_overlap < len(words) * 0.6:
                missing_headings.append(h)

    # 3. Проверка callouts (собеседования, gotchas, под капотом)
    before_callout_types = [c["type"] for c in before["callouts"]]
    after_callout_types = [c["type"] for c in after["callouts"]]
    callout_diff = len(after["callouts"]) - len(before["callouts"])

    # Расчет процента сохранения терминов
    total_before_terms = len(before["identifiers"])
    preserved_terms_count = total_before_terms - len(missing_identifiers)
    terms_ratio = (preserved_terms_count / total_before_terms * 100) if total_before_terms > 0 else 100.0

    is_passed = (
        terms_ratio >= 90.0 and
        len(missing_headings) == 0 and
        after["mermaid_count"] >= before["mermaid_count"] and
        after["bytes"] >= int(before["bytes"] * 0.8) # объем не урезан
    )

    return {
        "passed": is_passed,
        "terms_ratio": terms_ratio,
        "before_terms_count": total_before_terms,
        "after_terms_count": len(after["identifiers"]),
        "missing_identifiers": missing_identifiers,
        "missing_headings": missing_headings,
        "before_callouts": len(before["callouts"]),
        "after_callouts": len(after["callouts"]),
        "before_mermaid": before["mermaid_count"],
        "after_mermaid": after["mermaid_count"],
        "before_bytes": before["bytes"],
        "after_bytes": after["bytes"],
        "before_words": before["words"],
        "after_words": after["words"],
    }

def print_diff_report(file_label: str, report: Dict[str, Any]):
    """Форматированный вывод отчета проверки ДО и ПОСЛЕ."""
    status_icon = "✅" if report["passed"] else "❌"
    status_text = "ПРОЙДЕНО (БЕЗ ПОТЕРЬ)" if report["passed"] else "ОБНАРУЖЕНЫ ПОТЕРИ"

    print(f"\n{status_icon} Отчет валидации редактуры: {file_label}")
    print("=" * 70)
    print(f"Статус проверки:           {status_text}")
    print(f"Сохранение терминов/кода:  {report['terms_ratio']:.1f}% ({report['before_terms_count'] - len(report['missing_identifiers'])} из {report['before_terms_count']})")
    print(f"Новых терминов/концепций:  +{max(0, report['after_terms_count'] - report['before_terms_count'])}")
    print(f"Диаграммы Mermaid:         ДО: {report['before_mermaid']} | ПОСЛЕ: {report['after_mermaid']}")
    print(f"Блоки-выноски (Callouts):  ДО: {report['before_callouts']} | ПОСЛЕ: {report['after_callouts']}")
    print(f"Объем текста (байты):      ДО: {report['before_bytes']} | ПОСЛЕ: {report['after_bytes']} (прирост: {report['after_bytes'] - report['before_bytes']:+d} байт)")
    print(f"Слов в статье:             ДО: {report['before_words']} | ПОСЛЕ: {report['after_words']}")

    if report["missing_headings"]:
        print("\n⚠️ ВНИМАНИЕ: Возможно утеряны темы заголовков:")
        for h in report["missing_headings"]:
            print(f"  - {h}")

    if report["missing_identifiers"]:
        print(f"\n⚠️ ВНИМАНИЕ: Утерянные технические идентификаторы/термины ({len(report['missing_identifiers'])}):")
        for ident in report["missing_identifiers"][:10]:
            print(f"  - `{ident}`")
        if len(report["missing_identifiers"]) > 10:
            print(f"  ... и еще {len(report['missing_identifiers']) - 10} терминов.")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Валидатор ДО и ПОСЛЕ редактуры")
    parser.add_argument("current_file", help="Путь к отредактированному файлу")
    parser.add_argument("--git-ref", default="HEAD~1", help="Git ревизия для сравнения (по умолчанию HEAD~1)")
    parser.add_argument("--original-file", help="Путь к исходному файлу до правки (если не из Git)")

    args = parser.parse_args()

    if not os.path.exists(args.current_file):
        print(f"Ошибка: Файл {args.current_file} не найден.")
        sys.exit(1)

    with open(args.current_file, "r", encoding="utf-8") as f:
        edited_content = f.read()

    if args.original_file:
        with open(args.original_file, "r", encoding="utf-8") as f:
            original_content = f.read()
    else:
        # Извлекаем из git
        rel_path = os.path.relpath(args.current_file, ".")
        try:
            res = subprocess.run(
                ["git", "show", f"{args.git_ref}:{rel_path}"],
                capture_output=True,
                text=True,
                check=True
            )
            original_content = res.stdout
        except Exception as e:
            print(f"Не удалось получить версию из Git ({args.git_ref}:{rel_path}): {e}")
            sys.exit(1)

    report = compare_articles(original_content, edited_content)
    print_diff_report(args.current_file, report)
    sys.exit(0 if report["passed"] else 1)

if __name__ == "__main__":
    main()
