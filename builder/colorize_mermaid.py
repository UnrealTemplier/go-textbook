#!/usr/bin/env python3
"""
colorize_mermaid.py — Добавляет семантическую раскраску в бесцветные Mermaid диаграммы.

Обрабатывает только flowchart / graph / stateDiagram (v2).
Вставляет classDef + присваивает классы узлам по ключевым словам.
Пропускает диаграммы у которых уже есть fill: / classDef / style.

Использование:
    python3 builder/colorize_mermaid.py [--dry-run]
"""

import re
import sys
import os
from pathlib import Path

# ─── Семантическая палитра (AGENTS.md §2.5.2) ─────────────────────────────────
CLASSDEF_BLOCK = """\
    classDef process  fill:#1e293b,stroke:#38bdf8,stroke-width:1px,color:#f8fafc
    classDef success  fill:#064e3b,stroke:#34d399,stroke-width:1px,color:#f8fafc
    classDef error    fill:#7f1d1d,stroke:#f87171,stroke-width:1px,color:#f8fafc
    classDef warning  fill:#78350f,stroke:#fbbf24,stroke-width:1px,color:#f8fafc
    classDef entry    fill:#1e3a5f,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    classDef aux      fill:#334155,stroke:#64748b,stroke-width:1px,color:#f8fafc
    classDef system   fill:#312e81,stroke:#a78bfa,stroke-width:1px,color:#f8fafc
    classDef data     fill:#132d29,stroke:#2dd4bf,stroke-width:1px,color:#f8fafc
    classDef network  fill:#881337,stroke:#fb7185,stroke-width:1px,color:#f8fafc
    classDef accent   fill:#1e1b4b,stroke:#818cf8,stroke-width:1px,color:#f8fafc"""

# ─── Ключевые слова для классификации узлов ────────────────────────────────────
KEYWORDS = {
    "error":   [
        r"\bошибк", r"\bpanic\b", r"\bfail", r"\bпаник", r"\bкрит",
        r"\breject", r"\bотказ", r"\bcrash\b", r"\bexception\b",
        r"\berr\b", r"\berror\b", r"\bnot found\b", r"\bнедост",
        r"\binvalid\b", r"\bне найден", r"\bнет\b", r"\bfalse\b",
    ],
    "success": [
        r"\bуспех", r"\bготов", r"\bвыход\b", r"\bdone\b", r"\bcomplete",
        r"\bfinish\b", r"\bок\b", r"\bok\b", r"\bsuccess\b", r"\bвывод\b",
        r"\bresult\b", r"\breturn\b", r"\bend\b", r"\bда\b", r"\byes\b",
        r"\btrue\b", r"\bвозврат", r"\bfinished\b",
    ],
    "warning": [
        r"\?", r"\bреш[её]ни", r"\bпроверк", r"\bcondition\b", r"\bif\b",
        r"\bchoice\b", r"\bcheck\b", r"\bвыбор\b", r"\bветк", r"\bdecision\b",
        r"\bvalidat", r"\bнужно\b", r"\bесли\b", r"\bswitch\b", r"\bcase\b",
    ],
    "entry":   [
        r"\bstart\b", r"\bстарт\b", r"\bbegin\b", r"\bвход\b",
        r"\bточка входа\b", r"\binit\b", r"\bmain\b", r"\bзапуск\b",
        r"\bclient\b", r"\bклиент\b", r"\bпользовател", r"\buser\b",
        r"\bentry\b", r"\brequest\b", r"\bзапрос\b",
    ],
    "system":  [
        r"\bkernel\b", r"\bядро\b", r"\bruntime\b", r"\bsyscall\b",
        r"\bgoroutine\b", r"\bscheduler\b", r"\bпланировщик\b",
        r"\bgc\b", r"\bheap\b", r"\bstack\b", r"\bмемор", r"\bпамять\b",
        r"\basm\b", r"\bос\b", r"\blinux\b", r"\bproc\b", r"\bthread\b",
        r"\bcpu\b", r"\bpaging\b", r"\bvma\b", r"\bmmu\b", r"\btlb\b",
    ],
    "data":    [
        r"\bdb\b", r"\bdatabase\b", r"\bбд\b", r"\bcache\b", r"\bкэш\b",
        r"\bstorage\b", r"\bredis\b", r"\bpostgres\b", r"\bmysql\b",
        r"\bstore\b", r"\bхранилищ", r"\bbucket\b", r"\bindex\b",
        r"\btable\b", r"\bshard\b", r"\breplica\b", r"\bwal\b",
        r"\bqueue\b", r"\bочередь\b", r"\bbuffer\b",
    ],
    "network": [
        r"\bhttp\b", r"\bapi\b", r"\brpc\b", r"\btcp\b", r"\bgrpc\b",
        r"\bсервер\b", r"\bserver\b", r"\bnetwork\b", r"\bсеть\b",
        r"\bresponse\b", r"\bответ\b", r"\bsocket\b", r"\bport\b",
        r"\bproxy\b", r"\bload balancer\b", r"\bbalancer\b", r"\bgateway\b",
        r"\btls\b", r"\bssl\b", r"\bdns\b", r"\bquic\b", r"\budp\b",
    ],
    "accent":  [
        r"\bgoroutine\b", r"\bchannel\b", r"\bchan\b", r"\bканал\b",
        r"\bgoroutin", r"\bmutex\b", r"\bрабочий\b", r"\bworker\b",
        r"\bpool\b", r"\bpipe\b", r"\binterface\b", r"\binterfac",
        r"\bключ\b", r"\bkey\b", r"\btoken\b", r"\bjwt\b",
    ],
}

# Предкомпиляция всех regex
COMPILED_KW: dict[str, list[re.Pattern]] = {
    cls: [re.compile(pat, re.IGNORECASE) for pat in pats]
    for cls, pats in KEYWORDS.items()
}


def classify_label(label: str) -> str:
    """Определяет семантический класс по тексту метки узла."""
    text = label.lower()
    # Приоритет: entry > error > success > warning > data > network > system > accent > process
    for cls in ("entry", "error", "success", "warning", "data", "network", "system", "accent"):
        for pat in COMPILED_KW[cls]:
            if pat.search(text):
                return cls
    return "process"


# ─── Regex для разбора строк диаграмм ─────────────────────────────────────────

# Заголовочная строка: flowchart TD / graph LR / stateDiagram-v2
RE_HEADER = re.compile(
    r'^(flowchart|graph|stateDiagram(?:-v2)?)\s*(\w+)?\s*$',
    re.IGNORECASE
)

# Узел: ID["label"] / ID("label") / ID{label} / ID[label]
# Захватывает: group(1)=node_id, group(2)=label_text
RE_NODE = re.compile(
    r'^(\s*)(\w[\w_-]*)\s*'          # indent + node_id
    r'[\[\(\{>]+\s*'                  # opening bracket
    r'(.*?)'                          # label
    r'[\]\)\}]+\s*'                   # closing bracket
    r'(:{3}\w+)?'                     # optional existing class
    r'\s*$'
)

# Уже аннотированный узел (уже есть :::class)
RE_HAS_CLASS = re.compile(r':::\w+')

# Строки-связи (стрелки) — с ними не работаем
RE_ARROW = re.compile(r'-->|---|-\.\.|==>|-->')

# Строки с существующими стилями
RE_HAS_STYLE = re.compile(r'classDef\b|fill\s*:|style\s+\w')

# Mermaid блок в Markdown (```mermaid ... ```)
RE_MERMAID_BLOCK = re.compile(
    r'(```mermaid\s*\n)(.*?)(```)',
    re.DOTALL
)


def is_already_colored(diagram: str) -> bool:
    """True если диаграмма уже содержит цвета или classDef."""
    return bool(RE_HAS_STYLE.search(diagram))


def colorize_flowchart(diagram: str) -> str:
    """Добавляет classDef + :::class в flowchart/graph диаграмму."""
    lines = diagram.split('\n')
    if not lines:
        return diagram

    # Проверяем, что это именно flowchart/graph (не stateDiagram)
    header = lines[0].strip()
    is_state = header.lower().startswith('statediagram')

    # Для stateDiagram цвета через classDef тоже поддерживаются, добавляем
    # Убедимся что заголовок действительно подходящий
    if not RE_HEADER.match(header):
        return diagram

    new_lines = [lines[0]]  # первая строка — заголовок

    # Вставляем classDef после заголовка
    new_lines.append(CLASSDEF_BLOCK)

    # Для stateDiagram — не аннотируем узлы (синтаксис другой)
    if is_state:
        new_lines.extend(lines[1:])
        return '\n'.join(new_lines)

    # Обрабатываем остальные строки flowchart/graph
    for line in lines[1:]:
        stripped = line.strip()

        # Пропускаем пустые, комментарии, уже имеющие classDef/style/class
        if not stripped or stripped.startswith('%%') or stripped.startswith('class '):
            new_lines.append(line)
            continue

        # Если уже есть аннотация :::class — оставляем как есть
        if RE_HAS_CLASS.search(line):
            new_lines.append(line)
            continue

        # Попытка разобрать строку как узел
        m = RE_NODE.match(line)
        if m:
            indent = m.group(1)
            node_id = m.group(2)
            label = m.group(3)
            css_class = classify_label(label)

            # Перестраиваем строку с добавленным :::class
            # Сохраняем оригинальную строку, просто добавляем в конец :::class
            # (до точки с запятой / стрелки если есть)
            # Ищем конец узла (закрывающую скобку)
            new_line = _append_class_to_node(line, css_class)
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    return '\n'.join(new_lines)


def _append_class_to_node(line: str, css_class: str) -> str:
    """Добавляет :::css_class к строке узла перед возможной стрелкой."""
    # Ищем конец узла — закрывающую скобку узла
    # Паттерн: NODE_DEF --> ... или просто NODE_DEF
    # Нам нужно найти конец первого определения узла и вставить :::class

    # Ищем конец определения первого узла
    # Узел может быть: ID[text] / ID["text"] / ID(text) / ID{text} / ID([text])
    # Используем поиск последовательности: word + bracket_open + content + bracket_close
    node_end_pattern = re.compile(
        r'(\w[\w_-]*\s*'           # node_id
        r'(?:\[[\[\(]|[\[\(\{>])' # opening bracket(s)
        r'[^\]\)\}]*'              # content
        r'[\]\)\}]+)'              # closing bracket(s)
    )

    m = node_end_pattern.search(line)
    if not m:
        return line

    # Позиция после конца первого узла
    insert_pos = m.end()

    # Проверяем что после нет уже :::
    rest = line[insert_pos:]
    if ':::' in rest.split('-->')[0] if '-->' in rest else rest:
        return line  # уже аннотирован

    return line[:insert_pos] + ':::' + css_class + line[insert_pos:]


def colorize_diagram(diagram: str) -> str:
    """Основная точка входа: раскрашивает одну диаграмму если нужно."""
    if is_already_colored(diagram):
        return diagram

    header = diagram.strip().split('\n')[0].strip().lower()
    if not (header.startswith('flowchart') or header.startswith('graph ')
            or header.startswith('statediagram')):
        return diagram  # sequenceDiagram, classDiagram, gantt, etc. — пропускаем

    return colorize_flowchart(diagram)


def process_file(path: Path, dry_run: bool = False) -> int:
    """Обрабатывает один markdown файл. Возвращает число изменённых диаграмм."""
    text = path.read_text(encoding='utf-8')
    changed = 0

    def replace_block(m: re.Match) -> str:
        nonlocal changed
        open_fence = m.group(1)
        body = m.group(2)
        close_fence = m.group(3)
        new_body = colorize_diagram(body)
        if new_body != body:
            changed += 1
            return open_fence + new_body + close_fence
        return m.group(0)

    new_text = RE_MERMAID_BLOCK.sub(replace_block, text)

    if changed > 0 and not dry_run:
        path.write_text(new_text, encoding='utf-8')

    return changed


def main():
    dry_run = '--dry-run' in sys.argv
    sources = Path('/home/ut/work/go-textbook/sources')

    md_files = sorted(sources.rglob('*.md'))
    total_files = 0
    total_diagrams = 0

    print(f"{'[DRY-RUN] ' if dry_run else ''}Обрабатываю {len(md_files)} файлов...")

    for md in md_files:
        n = process_file(md, dry_run=dry_run)
        if n > 0:
            total_files += 1
            total_diagrams += n
            print(f"  ✅ {md.relative_to(sources)} — {n} диаграмм(а)")

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Готово!")
    print(f"  Изменено файлов:   {total_files}")
    print(f"  Раскрашено диаграмм: {total_diagrams}")


if __name__ == '__main__':
    main()
