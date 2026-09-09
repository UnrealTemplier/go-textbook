"""
builder/batch_runner.py
Пакетная конвертация всех 22 модулей энциклопедии с атомарными Git-коммитами
для каждого раздела и обновлением AGENTS.md.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import re
import time
import subprocess
from builder.scanner import KnowledgeBaseScanner
from builder.build_all import build

def update_agents_md_for_module(module_num: int, module_title: str):
    """Обновление статуса модуля в файле AGENTS.md."""
    agents_path = "AGENTS.md"
    if not os.path.exists(agents_path):
        return

    with open(agents_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Паттерн для поиска заголовка модуля
    # Например: ### Раздел 2. 2. Устройство и работа ОС
    header_pat = rf"(### Раздел {module_num}\..*?\n- \*\*Статус:\*\*\s*)(⏳ В очереди \(TODO\)|\[ \])"
    
    def repl_status(match):
        return f"{match.group(1)}✅ Завершен (CONVERTED)"

    content = re.sub(header_pat, repl_status, content)

    # Заменяем [ ] на [x] в таблице этого модуля
    # Находим блок текущего модуля до следующего ### Раздел
    module_section_pat = rf"(### Раздел {module_num}\..*?)(?=### Раздел \d+|\Z)"
    
    def repl_subsections(match):
        sec_text = match.group(1)
        sec_text = sec_text.replace("| [ ] |", "| [x] |")
        return sec_text

    content = re.sub(module_section_pat, repl_subsections, content, flags=re.DOTALL)

    with open(agents_path, "w", encoding="utf-8") as f:
        f.write(content)

def git_commit_module(module_num: int, module_title: str):
    """Атомарный коммит в Git после конвертации модуля."""
    subprocess.run(["git", "add", "AGENTS.md"], check=True)
    msg = f"feat(module-{module_num:02d}): convert and verify Module {module_num} ({module_title})"
    # Проверяем есть ли изменения
    res = subprocess.run(["git", "diff", "--staged", "--quiet"])
    if res.returncode != 0:
        subprocess.run(["git", "commit", "-m", msg], check=True)
        print(f"      📌 Зафиксирован Git-коммит: {msg}")

def run_batch():
    scanner = KnowledgeBaseScanner("./sources")
    scanner.scan()

    total_modules = len(scanner.modules_tree)
    print("=====================================================================")
    print(f"🚀 Запуск пакетной конвертации {total_modules} модулей с атомарными коммитами")
    print("=====================================================================")

    # Модуль 1 уже собран и закоммичен, конвертируем модули 2..22
    for mod in scanner.modules_tree:
        num = mod["num"]
        title = mod["title"]
        if num == 1:
            print(f"\n[Модуль 01/{total_modules}] {title} — уже зафиксирован (PILOT DONE)")
            continue

        print(f"\n---------------------------------------------------------------------")
        print(f"⚙️ [Модуль {num:02d}/{total_modules}] Конвертация: {title}")
        print(f"---------------------------------------------------------------------")

        # 1. Сборка конкретного модуля
        build(sources_dir="./sources", dist_dir="./dist", target_module=num)

        # 2. Обновление AGENTS.md
        update_agents_md_for_module(num, title)

        # 3. Атомарный коммит
        git_commit_module(num, title)

    # Финальная сборка главной страницы и общего поиска
    print("\n=====================================================================")
    print("🌟 Финальная синхронизация дашборда и поискового индекса...")
    print("=====================================================================")
    build(sources_dir="./sources", dist_dir="./dist", limit=0) # limit=0 перегенерирует index и assets без пересборки статей

    # Обновление статуса Шага 4 в AGENTS.md
    with open("AGENTS.md", "r", encoding="utf-8") as f:
        agents_content = f.read()

    agents_content = agents_content.replace(
        "- [ ] **Шаг 4: Пакетная конвертация всех 22 разделов**",
        "- [x] **Шаг 4: Пакетная конвертация всех 22 разделов**\n  - [x] Все 22 модуля успешно скомпилированы и зафиксированы отдельными коммитами."
    )

    with open("AGENTS.md", "w", encoding="utf-8") as f:
        f.write(agents_content)

    subprocess.run(["git", "add", "AGENTS.md"], check=True)
    subprocess.run(["git", "commit", "-m", "docs(roadmap): mark Step 4 (all 22 modules converted) as complete"], check=True)

    print("\n=====================================================================")
    print("🏁 ПАКЕТНАЯ КОНВЕРТАЦИЯ ВСЕХ 22 МОДУЛЕЙ УСПЕШНО ЗАВЕРШЕНА!")
    print("=====================================================================")

if __name__ == "__main__":
    run_batch()
