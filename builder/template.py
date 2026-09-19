"""
builder/template.py
HTML5 шаблоны, CSS стили в стиле Go Workout (Dark Theme) и JS скрипты для
автономной работы портала (file:/// и веб-хостинг).
"""

import os
import html
from typing import Dict, Any, List, Optional
from builder.scanner import Article

GO_LOGO_SVG = (
    '<svg class="logo-go-icon" viewBox="0 42 165 82" fill="#00ADD8" xmlns="http://www.w3.org/2000/svg" aria-label="Go">'
    '<g transform="translate(9, 46)" fill="#00ADD8" fill-rule="evenodd">'
    '<path d="m74.1 22.3c-6.3 1.6-10.6 2.8-16.8 4.4-1.5.4-1.6.5-2.9-1-1.5-1.7-2.6-2.8-4.7-3.8-6.3-3.1-12.4-2.2-18.1 1.5-6.8 4.4-10.3 10.9-10.2 19 .1 8 5.6 14.6 13.5 15.7 6.8.9 12.5-1.5 17-6.6.9-1.1 1.7-2.3 2.7-3.7-3.6 0-8.1 0-19.3 0-2.1 0-2.6-1.3-1.9-3 1.3-3.1 3.7-8.3 5.1-10.9.3-.6 1-1.6 2.5-1.6h36.4c-.2 2.7-.2 5.4-.6 8.1-1.1 7.2-3.8 13.8-8.2 19.6-7.2 9.5-16.6 15.4-28.5 17-9.8 1.3-18.9-.6-26.9-6.6-7.4-5.6-11.6-13-12.7-22.2-1.3-10.9 1.9-20.7 8.5-29.3 7.1-9.3 16.5-15.2 28-17.3 9.4-1.7 18.4-.6 26.5 4.9 5.3 3.5 9.1 8.3 11.6 14.1.6.9.2 1.4-1 1.7z"/>'
    '<path d="m107.2 77.6c-9.1-.2-17.4-2.8-24.4-8.8-5.9-5.1-9.6-11.6-10.8-19.3-1.8-11.3 1.3-21.3 8.1-30.2 7.3-9.6 16.1-14.6 28-16.7 10.2-1.8 19.8-.8 28.5 5.1 7.9 5.4 12.8 12.7 14.1 22.3 1.7 13.5-2.2 24.5-11.5 33.9-6.6 6.7-14.7 10.9-24 12.8-2.7.5-5.4.6-8 .9zm23.8-40.4c-.1-1.3-.1-2.3-.3-3.3-1.8-9.9-10.9-15.5-20.4-13.3-9.3 2.1-15.3 8-17.5 17.4-1.8 7.8 2 15.7 9.2 18.9 5.5 2.4 11 2.1 16.3-.6 7.9-4.1 12.2-10.5 12.7-19.1z" fill-rule="nonzero"/>'
    '</g>'
    '</svg>'
)

def get_rel_root(rel_path: str) -> str:
    """Вычисление пути к корню сайта из относительного пути файла."""
    depth = rel_path.count("/")
    if depth == 0:
        return "./"
    return "../" * depth

def render_sidebar(
    modules_tree: List[Dict[str, Any]],
    current_article: Optional[Article],
    rel_root: str
) -> str:
    """Генерация интерактивного сайдбара с древовидным аккордеоном."""
    html_parts = []
    html_parts.append('<div class="sidebar-nav">')

    curr_path = current_article.rel_output_path if current_article else ""

    for mod in modules_tree:
        mod_num = mod["num"]
        mod_title = mod["title"]
        mod_raw = mod["raw_name"]
        
        # Проверяем, активен ли текущий модуль
        is_mod_active = False
        if current_article and current_article.module_num == mod_num:
            is_mod_active = True

        open_attr = "open" if is_mod_active else ""
        active_class = "active-module" if is_mod_active else ""

        html_parts.append(f'<details class="nav-module {active_class}" {open_attr}>')
        html_parts.append(f'<summary class="nav-module-title"><span class="mod-badge">{mod_num}</span> <span class="mod-text">{html.escape(mod_title)}</span></summary>')
        html_parts.append('<div class="nav-module-content">')

        # Статьи в корне модуля
        if mod["articles"]:
            html_parts.append('<ul class="nav-articles-list">')
            for art in mod["articles"]:
                href = rel_root + art.rel_output_path
                is_curr = (art.rel_output_path == curr_path)
                curr_class = ' class="nav-item active"' if is_curr else ' class="nav-item"'
                html_parts.append(f'<li{curr_class}><a href="{href}">{html.escape(art.title)}</a></li>')
            html_parts.append('</ul>')

        # Подразделы
        for sub in mod["subsections"]:
            sub_name = sub["name"]
            is_sub_active = False
            if current_article and current_article.subsection_name == sub_name and current_article.module_num == mod_num:
                is_sub_active = True

            sub_open = "open" if is_sub_active else ""
            active_sub_class = " active-submodule" if is_sub_active else ""
            html_parts.append(f'<details class="nav-submodule{active_sub_class}" {sub_open}>')
            html_parts.append(f'<summary class="nav-submodule-title"><span class="sub-chevron"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg></span><span class="sub-text">{html.escape(sub_name)}</span></summary>')
            html_parts.append('<ul class="nav-articles-list sub-list">')
            for art in sub["articles"]:
                href = rel_root + art.rel_output_path
                is_curr = (art.rel_output_path == curr_path)
                curr_class = ' class="nav-item active"' if is_curr else ' class="nav-item"'
                html_parts.append(f'<li{curr_class}><a href="{href}">{html.escape(art.title)}</a></li>')
            html_parts.append('</ul>')
            html_parts.append('</details>')

        html_parts.append('</div>') # nav-module-content
        html_parts.append('</details>') # nav-module

    html_parts.append('</div>') # sidebar-nav
    return "\n".join(html_parts)

def render_breadcrumbs(article: Article, rel_root: str) -> str:
    """Хлебные крошки над статьей."""
    crumbs = [
        f'<a href="{rel_root}index.html" class="crumb-link">Главная</a>'
    ]
    crumbs.append(f'<span class="crumb-sep">/</span>')
    crumbs.append(f'<span class="crumb-module">{html.escape(article.module_name)}</span>')
    
    if article.subsection_name:
        crumbs.append(f'<span class="crumb-sep">/</span>')
        crumbs.append(f'<span class="crumb-sub">{html.escape(article.subsection_name)}</span>')

    crumbs.append(f'<span class="crumb-sep">/</span>')
    crumbs.append(f'<span class="crumb-current">{html.escape(article.title)}</span>')

    return f'<nav class="breadcrumbs" aria-label="Хлебные крошки">{" ".join(crumbs)}</nav>'

def render_article_page(
    article: Article,
    article_html: str,
    toc: List[Dict[str, Any]],
    modules_tree: List[Dict[str, Any]],
    total_articles: int = 1413
) -> str:
    """Генерация полной HTML-страницы статьи."""
    rel_root = get_rel_root(article.rel_output_path)
    sidebar_html = render_sidebar(modules_tree, article, rel_root)
    breadcrumbs_html = render_breadcrumbs(article, rel_root)

    # Предыдущая и следующая статья
    prev_link_html = ""
    if article.prev_article:
        p_href = rel_root + article.prev_article.rel_output_path
        prev_link_html = f"""
<a href="{p_href}" class="article-nav-card prev-card">
  <div class="nav-dir">← Предыдущая статья</div>
  <div class="nav-title">{html.escape(article.prev_article.title)}</div>
</a>
"""
    else:
        prev_link_html = '<div class="article-nav-placeholder"></div>'

    next_link_html = ""
    if article.next_article:
        n_href = rel_root + article.next_article.rel_output_path
        next_link_html = f"""
<a href="{n_href}" class="article-nav-card next-card">
  <div class="nav-dir">Следующая статья →</div>
  <div class="nav-title">{html.escape(article.next_article.title)}</div>
</a>
"""
    else:
        next_link_html = '<div class="article-nav-placeholder"></div>'

    # Оглавление статьи (TOC)
    toc_items = []
    if toc:
        for t in toc:
            level = t["level"]
            cls = f"toc-item toc-h{level}"
            toc_items.append(f'<li class="{cls}"><a href="#{t["anchor"]}">{html.escape(t["title"])}</a></li>')
        toc_html = f"""
<aside class="article-toc" id="article-toc">
  <div class="toc-header">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
    <span>На этой странице</span>
  </div>
  <ul class="toc-list">
    {"".join(toc_items)}
  </ul>
</aside>
"""
    else:
        toc_html = ""

    reading_time = max(2, int(article.size_bytes / 800))

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(article.title)} | Инженерная энциклопедия бэкенда</title>
  <meta name="description" content="Полное руководство: {html.escape(article.title)}. Go, архитектура систем, computer science.">
  <link rel="icon" href="{rel_root}favicon.ico" sizes="32x32">
  <link rel="icon" type="image/svg+xml" href="{rel_root}favicon.svg" sizes="any">
  <link rel="stylesheet" href="{rel_root}assets/style.css">
  <link rel="stylesheet" href="{rel_root}assets/vendor/prism-tomorrow.min.css">
  <link rel="stylesheet" href="{rel_root}assets/vendor/katex/katex.min.css">
</head>
<body class="theme-dark">
  <div class="reading-progress-bar" id="reading-progress"></div>

  <div class="app-layout">
    <!-- Левый сайдбар -->
    <aside class="app-sidebar" id="app-sidebar">
      <div class="sidebar-header">
        <a href="{rel_root}index.html" class="brand-logo">
          <div class="logo-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
          </div>
          <div class="logo-text">
            <span class="logo-title">{GO_LOGO_SVG} BACKEND</span>
            <span class="logo-sub">Энциклопедия</span>
          </div>
        </a>
      </div>

      <!-- Поиск по сайдбару -->
      <div class="sidebar-search">
        <div class="search-input-wrapper">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <input type="text" id="sidebar-filter" placeholder="Фильтр по лекциям..." autocomplete="off">
          <button class="clear-search-btn" id="clear-filter" title="Очистить">&times;</button>
        </div>
      </div>

      <!-- Оглавление сайдбара -->
      <div class="sidebar-content" id="sidebar-content">
        {sidebar_html}
      </div>

      <div class="sidebar-footer">
        <span class="catalog-stat">Статей: <strong>{total_articles}</strong></span>
        <span class="offline-badge">Offline First</span>
      </div>
    </aside>

    <!-- Ползунок изменения ширины сайдбара (drag-to-resize) -->
    <div class="resizer" id="drag-resizer"></div>

    <!-- Основная контентная область -->
    <main class="app-main" id="app-main">
      <header class="content-header">
        <button class="btn-toggle-sidebar" id="toggle-sidebar" title="Открыть меню">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </button>
        {breadcrumbs_html}
      </header>

      <div class="content-wrapper">
        <article class="article-body">
          <header class="article-header">
            <div class="article-meta-tags">
              <span class="meta-tag module-tag">Модуль {article.module_num}</span>
              <span class="meta-tag read-time">⏱ ~{reading_time} мин чтения</span>
              {f'<span class="meta-tag mermaid-tag">📐 {article.mermaid_count} Mermaid диаграмм</span>' if article.mermaid_count > 0 else ''}
            </div>
            <h1 class="article-title">{html.escape(article.title)}</h1>
          </header>

          <div class="article-markdown">
            {article_html}
          </div>

          <!-- Навигация Предыдущая / Следующая статья -->
          <nav class="article-bottom-nav">
            {prev_link_html}
            {next_link_html}
          </nav>
        </article>

        <!-- Оглавление текущей статьи -->
        {toc_html}
      </div>

      <footer class="app-footer">
        <p>Инженерная веб-энциклопедия бэкенда и языка Go • Авторский стиль Брайана Кернигана</p>
        <p>Собрано автономным генератором без внешних зависимостей. 100% Offline Ready.</p>
      </footer>
    </main>
  </div>

  <!-- Полноэкранный модальный просмотр Mermaid диаграмм -->
  <div class="mermaid-modal" id="mermaid-modal">
    <div class="modal-backdrop" onclick="closeMermaidModal()"></div>
    <div class="modal-dialog">
      <div class="modal-header">
        <span class="modal-title">Архитектурная схема (Mermaid)</span>
        <div class="modal-actions">
          <button class="btn-modal-action" onclick="zoomMermaid(0.2)" title="Приблизить">+</button>
          <button class="btn-modal-action" onclick="zoomMermaid(-0.2)" title="Отдалить">-</button>
          <button class="btn-modal-action" onclick="resetMermaidZoom()" title="100%">1:1</button>
          <button class="btn-modal-action btn-modal-close" onclick="closeMermaidModal()" title="Закрыть (Esc)">&times;</button>
        </div>
      </div>
      <div class="modal-body" id="mermaid-modal-content"></div>
    </div>
  </div>

  <!-- Кнопка Наверх -->
  <button class="btn-scroll-top" id="btn-scroll-top" title="Наверх">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
  </button>

  <!-- Скрипты -->
  <script src="{rel_root}assets/vendor/prism-bundle.min.js"></script>
  <script src="{rel_root}assets/vendor/mermaid.min.js"></script>
  <script src="{rel_root}assets/vendor/katex/katex.min.js"></script>
  <script src="{rel_root}assets/vendor/katex/contrib/auto-render.min.js"></script>
  <script src="{rel_root}assets/main.js"></script>
</body>
</html>
"""

def render_index_page(
    modules_tree: List[Dict[str, Any]],
    total_articles: int,
    total_mermaid: int
) -> str:
    """Генерация главной страницы index.html (Интерактивный дашборд и каталог)."""
    rel_root = "./"

    cards_html = []
    for mod in modules_tree:
        num = mod["num"]
        title = mod["title"]
        m_articles = mod["articles"]
        sub_count = len(mod["subsections"])
        
        all_mod_arts = list(m_articles)
        for s in mod["subsections"]:
            all_mod_arts.extend(s["articles"])

        art_count = len(all_mod_arts)
        mermaid_count = sum(a.mermaid_count for a in all_mod_arts)
        first_art_href = rel_root + all_mod_arts[0].rel_output_path if all_mod_arts else "#"

        cards_html.append(f"""
<div class="module-card">
  <div class="module-card-header">
    <span class="card-num-badge">{num:02d}</span>
    <span class="card-count-badge">{art_count} статей</span>
  </div>
  <h3 class="module-card-title">{html.escape(title)}</h3>
  <div class="module-card-meta">
    <span>📐 {mermaid_count} схем</span>
    {f'<span>📁 {sub_count} тем</span>' if sub_count > 0 else '<span>📖 Базовый курс</span>'}
  </div>
  <div class="module-card-actions">
    <a href="{first_art_href}" class="btn-card-start">Начать изучение →</a>
  </div>
</div>
""")

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Инженерная веб-энциклопедия бэкенда (Go & Computer Science)</title>
  <meta name="description" content="Фундаментальная энциклопедия бэкенда, распределенных систем и языка Go от Брайана Кернигана. 1 400+ статей, 1 400+ схем Mermaid.">
  <link rel="icon" href="{rel_root}favicon.ico" sizes="32x32">
  <link rel="icon" type="image/svg+xml" href="{rel_root}favicon.svg" sizes="any">
  <link rel="stylesheet" href="{rel_root}assets/style.css">
  <link rel="stylesheet" href="{rel_root}assets/vendor/prism-tomorrow.min.css">
</head>
<body class="theme-dark index-page">
  <div class="index-container">
    <!-- Героическая секция -->
    <header class="index-hero">
      <div class="hero-badge">Энциклопедия Computer Science & Backend</div>
      <h1 class="hero-title">Фундаментальный бэкенд на Go: от кремния до распределенных систем</h1>
      <p class="hero-quote">
        <em>«Управление сложностью — вот суть программирования».</em>  
        <span class="quote-author">— Брайан Керниган</span>
      </p>

      <!-- Полнотекстовый живой поиск -->
      <div class="hero-search-box">
        <div class="search-bar-inner">
          <svg class="hero-search-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <input type="text" id="global-search-input" placeholder="Поиск по 1 413 лекциям (например: netpoller, GC, MVCC, Raft, CAS)..." autocomplete="off">
        </div>
        <div class="search-results-dropdown" id="global-search-results"></div>
      </div>

      <!-- Виджеты статистики -->
      <div class="stats-ribbon">
        <div class="stat-box">
          <span class="stat-number">22</span>
          <span class="stat-desc">Тематических модуля</span>
        </div>
        <div class="stat-box">
          <span class="stat-number">{total_articles}</span>
          <span class="stat-desc">Инженерных лекций</span>
        </div>
        <div class="stat-box">
          <span class="stat-number">{total_mermaid}</span>
          <span class="stat-desc">Диаграмм Mermaid</span>
        </div>
        <div class="stat-box">
          <span class="stat-number">100%</span>
          <span class="stat-desc">Offline & file:///</span>
        </div>
      </div>
    </header>

    <!-- Каталог модулей -->
    <section class="modules-catalog">
      <div class="catalog-header">
        <h2 class="section-title">Каталог учебных модулей</h2>
        <p class="section-sub">22 всеобъемлющих курса, выстроенных в строгую логическую последовательность</p>
      </div>

      <div class="modules-grid">
        {"".join(cards_html)}
      </div>
    </section>

    <!-- Дорожная карта обучения -->
    <section class="learning-roadmap">
      <h2 class="section-title">Инженерный трек: как изучать базу</h2>
      <div class="roadmap-timeline">
        <div class="roadmap-step">
          <div class="step-badge">Шаг 1</div>
          <div class="step-content">
            <h4>Кремний и Операционная система (Модули 1–3)</h4>
            <p>Логические вентили, регистры, конвейеры CPU, кэш-линии, виртуальная память, CFS, epoll и сокеты. Без этого понимание рантайма Go невозможно.</p>
          </div>
        </div>
        <div class="roadmap-step">
          <div class="step-badge">Шаг 2</div>
          <div class="step-content">
            <h4>Глубокий Go и Runtime (Модули 4–9)</h4>
            <p>GMP-планировщик, стек горутины, аллокатор mheap, сборщик мусора тройной раскраски, сетевой поллер (netpoller) и архитектура сервисов.</p>
          </div>
        </div>
        <div class="roadmap-step">
          <div class="step-badge">Шаг 3</div>
          <div class="step-content">
            <h4>Хранилища и Распределенные системы (Модули 10–14)</h4>
            <p>B+ Tree vs LSM, MVCC, транзакции, Kafka, NATS, консенсус Raft/Paxos, CAP/PACELC и микросервисы.</p>
          </div>
        </div>
        <div class="roadmap-step">
          <div class="step-badge">Шаг 4</div>
          <div class="step-content">
            <h4>Надежность, Performance & DSA (Модули 15–22)</h4>
            <p>Профилирование pprof, trace, AppSec, алгоритмы, 218 задач LeetCode и глубокая подготовка к BigTech интервью.</p>
          </div>
        </div>
      </div>
    </section>

    <footer class="index-footer">
      <p>Инженерная веб-энциклопедия бэкенда и языка Go • В память о традициях Bell Labs и Брайана Кернигана</p>
      <p>Полностью автономная сборка. Никаких трекеров, рекламы и внешних серверов.</p>
    </footer>
  </div>

  <script src="{rel_root}assets/search-data.js"></script>
  <script src="{rel_root}assets/main.js"></script>
</body>
</html>
"""
