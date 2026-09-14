/**
 * Go Backend Encyclopedia — Interactive Client Scripts
 * Brian Kernighan Style: Simple, robust, zero-dependency, works on file:///
 */

(function () {
  'use strict';

  // -------------------------------------------------------------------------
  // 1. Инициализация Mermaid.js
  // -------------------------------------------------------------------------
  function initMermaid() {
    if (typeof mermaid !== 'undefined') {
      try {
        mermaid.initialize({
          startOnLoad: true,
          theme: 'dark',
          securityLevel: 'loose',
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          themeVariables: {
            darkMode: true,
            background: '#0e1526',
            primaryColor: '#6366f1',
            primaryTextColor: '#f8fafc',
            primaryBorderColor: '#334155',
            lineColor: '#38bdf8',
            secondaryColor: '#1e293b',
            tertiaryColor: '#0f172a',
            noteBkgColor: '#131d33',
            noteTextColor: '#cbd5e1',
            noteBorderColor: '#38bdf8'
          }
        });
      } catch (err) {
        console.warn('Mermaid initialization warning:', err);
      }
    }
  }

  // -------------------------------------------------------------------------
  // Вспомогательные функции центрирования и плавной прокрутки сайдбара
  // -------------------------------------------------------------------------
  function smoothScroll(container, targetScrollTop, duration = 480) {
    if (!container) return;

    const startScrollTop = container.scrollTop;
    const maxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
    const clampedTarget = Math.max(0, Math.min(maxScroll, Math.round(targetScrollTop)));
    const distance = clampedTarget - startScrollTop;

    if (Math.abs(distance) < 2 || duration <= 0) {
      container.scrollTop = clampedTarget;
      return;
    }

    if (container._scrollAnimId) {
      cancelAnimationFrame(container._scrollAnimId);
      container._scrollAnimId = null;
    }

    const startTime = performance.now();

    // easeOutQuart: мягкое, размеренное и плавное замедление
    function easeOutQuart(t) {
      return 1 - Math.pow(1 - t, 4);
    }

    function step(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(1, elapsed / duration);
      const ease = easeOutQuart(progress);

      container.scrollTop = Math.round(startScrollTop + distance * ease);

      if (progress < 1) {
        container._scrollAnimId = requestAnimationFrame(step);
      } else {
        container.scrollTop = clampedTarget;
        container._scrollAnimId = null;
      }
    }

    container._scrollAnimId = requestAnimationFrame(step);
  }

  function centerElementInContainer(container, element, smooth = false) {
    if (!container || !element) return;

    const containerRect = container.getBoundingClientRect();
    const elementRect = element.getBoundingClientRect();

    if (containerRect.height === 0 || elementRect.height === 0) return;

    const currentScrollTop = container.scrollTop;
    const elementTopInContent = (elementRect.top - containerRect.top) + currentScrollTop;
    const targetScrollTop = elementTopInContent + (elementRect.height / 2) - (container.clientHeight / 2);

    if (smooth) {
      smoothScroll(container, targetScrollTop, 480);
    } else {
      const maxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
      container.scrollTop = Math.max(0, Math.min(maxScroll, Math.round(targetScrollTop)));
    }
  }

  function centerActiveLecture(smooth = false) {
    const container = document.getElementById('sidebar-content');
    if (!container) return;

    const activeItem = container.querySelector('.nav-item.active');
    if (activeItem) {
      let parentDetails = activeItem.closest('details');
      while (parentDetails) {
        if (!parentDetails.hasAttribute('open')) {
          parentDetails.setAttribute('open', '');
        }
        parentDetails = parentDetails.parentElement ? parentDetails.parentElement.closest('details') : null;
      }
      centerElementInContainer(container, activeItem, smooth);
    }
  }

  // -------------------------------------------------------------------------
  // 2. Управление шириной сайдбара (drag-to-resize)
  // -------------------------------------------------------------------------
  function initSidebarResize() {
    const sidebar = document.getElementById('app-sidebar');
    const resizer = document.getElementById('drag-resizer');
    if (!sidebar || !resizer) return;

    const STORAGE_KEY = 'go_encyclopedia_sidebar_width';
    const savedWidth = localStorage.getItem(STORAGE_KEY);
    if (savedWidth) {
      const widthNum = parseInt(savedWidth, 10);
      if (widthNum >= 220 && widthNum <= 550) {
        sidebar.style.width = widthNum + 'px';
      }
    }

    let isResizing = false;

    resizer.addEventListener('mousedown', function (e) {
      isResizing = true;
      resizer.classList.add('resizing');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', function (e) {
      if (!isResizing) return;
      const newWidth = e.clientX;
      if (newWidth >= 220 && newWidth <= 550) {
        sidebar.style.width = newWidth + 'px';
      }
    });

    document.addEventListener('mouseup', function () {
      if (isResizing) {
        isResizing = false;
        resizer.classList.remove('resizing');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        localStorage.setItem(STORAGE_KEY, parseInt(sidebar.style.width, 10));
        centerActiveLecture(false);
      }
    });
  }

  // -------------------------------------------------------------------------
  // 3. Мгновенная фильтрация лекций в сайдбаре
  // -------------------------------------------------------------------------
  function initSidebarFilter() {
    const filterInput = document.getElementById('sidebar-filter');
    const clearBtn = document.getElementById('clear-filter');
    const sidebarContent = document.getElementById('sidebar-content');
    if (!filterInput || !sidebarContent) return;

    const navItems = sidebarContent.querySelectorAll('.nav-item');
    const modules = sidebarContent.querySelectorAll('.nav-module');
    const submodules = sidebarContent.querySelectorAll('.nav-submodule');

    filterInput.addEventListener('input', function () {
      const query = filterInput.value.trim().toLowerCase();

      if (clearBtn) {
        clearBtn.style.display = query ? 'block' : 'none';
      }

      if (!query) {
        navItems.forEach(item => item.style.display = '');
        modules.forEach(mod => {
          mod.style.display = '';
          // Восстанавливаем только активный
          if (!mod.classList.contains('active-module')) {
            mod.removeAttribute('open');
          }
        });
        submodules.forEach(sub => {
          sub.style.display = '';
          sub.removeAttribute('open');
        });
        setTimeout(function () {
          centerActiveLecture(true);
        }, 30);
        return;
      }

      // Если есть поисковый запрос:
      modules.forEach(mod => {
        let modHasMatches = false;
        const modItems = mod.querySelectorAll('.nav-item');

        modItems.forEach(item => {
          const text = item.textContent.toLowerCase();
          if (text.includes(query)) {
            item.style.display = '';
            modHasMatches = true;
          } else {
            item.style.display = 'none';
          }
        });

        // Проверяем подмодули
        const modSubs = mod.querySelectorAll('.nav-submodule');
        modSubs.forEach(sub => {
          let subHasMatches = false;
          const subItems = sub.querySelectorAll('.nav-item');
          subItems.forEach(si => {
            if (si.textContent.toLowerCase().includes(query)) {
              subHasMatches = true;
            }
          });
          if (subHasMatches) {
            sub.style.display = '';
            sub.setAttribute('open', '');
          } else {
            sub.style.display = 'none';
          }
        });

        if (modHasMatches) {
          mod.style.display = '';
          mod.setAttribute('open', '');
        } else {
          mod.style.display = 'none';
        }
      });
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        filterInput.value = '';
        filterInput.dispatchEvent(new Event('input'));
        filterInput.focus();
      });
    }
  }

  // -------------------------------------------------------------------------
  // 4. Копирование кода в 1 клик
  // -------------------------------------------------------------------------
  window.copyCodeBlock = function (btn) {
    const codeWrapper = btn.closest('.code-block');
    if (!codeWrapper) return;
    const codeEl = codeWrapper.querySelector('code');
    if (!codeEl) return;

    const textToCopy = codeEl.innerText || codeEl.textContent;

    navigator.clipboard.writeText(textToCopy).then(() => {
      const originalHTML = btn.innerHTML;
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <span style="color:#10b981; font-weight:600;">Скопировано!</span>
      `;
      btn.style.borderColor = '#10b981';

      setTimeout(() => {
        btn.innerHTML = originalHTML;
        btn.style.borderColor = '';
      }, 2000);
    }).catch(err => {
      console.error('Copy failed:', err);
    });
  };

  // -------------------------------------------------------------------------
  // 5. Полноэкранный модальный просмотр диаграмм Mermaid и зумирование
  // -------------------------------------------------------------------------
  let currentMermaidZoom = 1.0;

  window.toggleMermaidModal = function (btn) {
    const wrapper = btn.closest('.mermaid-wrapper');
    if (!wrapper) return;
    const svgEl = wrapper.querySelector('.mermaid svg');
    if (!svgEl) return;

    const modal = document.getElementById('mermaid-modal');
    const container = document.getElementById('mermaid-modal-content');
    if (!modal || !container) return;

    container.innerHTML = '';
    const clonedSvg = svgEl.cloneNode(true);
    container.appendChild(clonedSvg);

    currentMermaidZoom = 1.0;
    clonedSvg.style.transform = `scale(${currentMermaidZoom})`;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  };

  window.closeMermaidModal = function () {
    const modal = document.getElementById('mermaid-modal');
    if (!modal) return;
    modal.classList.remove('active');
    document.body.style.overflow = '';
  };

  window.zoomMermaid = function (delta) {
    const container = document.getElementById('mermaid-modal-content');
    if (!container) return;
    const svg = container.querySelector('svg');
    if (!svg) return;

    currentMermaidZoom = Math.max(0.3, Math.min(3.5, currentMermaidZoom + delta));
    svg.style.transform = `scale(${currentMermaidZoom})`;
  };

  window.resetMermaidZoom = function () {
    const container = document.getElementById('mermaid-modal-content');
    if (!container) return;
    const svg = container.querySelector('svg');
    if (!svg) return;

    currentMermaidZoom = 1.0;
    svg.style.transform = `scale(1.0)`;
  };

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      window.closeMermaidModal();
    }
  });

  // Зум колесиком мыши в модалке
  const modalBody = document.getElementById('mermaid-modal-content');
  if (modalBody) {
    modalBody.addEventListener('wheel', function (e) {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.15 : -0.15;
      window.zoomMermaid(delta);
    }, { passive: false });
  }

  // -------------------------------------------------------------------------
  // 6. Индикатор чтения и кнопка "Наверх"
  // -------------------------------------------------------------------------
  function initScrollProgress() {
    const progressEl = document.getElementById('reading-progress');
    const btnScrollTop = document.getElementById('btn-scroll-top');

    window.addEventListener('scroll', function () {
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;

      if (progressEl && docHeight > 0) {
        const percent = Math.min(100, Math.max(0, (scrollTop / docHeight) * 100));
        progressEl.style.width = percent + '%';
      }

      if (btnScrollTop) {
        if (scrollTop > 350) {
          btnScrollTop.classList.add('visible');
        } else {
          btnScrollTop.classList.remove('visible');
        }
      }
    });

    if (btnScrollTop) {
      btnScrollTop.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  // -------------------------------------------------------------------------
  // 7. Мобильное меню сайдбара
  // -------------------------------------------------------------------------
  function initMobileMenu() {
    const toggleBtn = document.getElementById('toggle-sidebar');
    const sidebar = document.getElementById('app-sidebar');
    if (!toggleBtn || !sidebar) return;

    toggleBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      const isOpen = sidebar.classList.toggle('open');
      if (isOpen) {
        setTimeout(function () {
          centerActiveLecture(false);
        }, 150);
      }
    });

    document.addEventListener('click', function (e) {
      if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
        if (!sidebar.contains(e.target) && e.target !== toggleBtn) {
          sidebar.classList.remove('open');
        }
      }
    });
  }

  // -------------------------------------------------------------------------
  // 8. Живой полнотекстовый поиск на главной странице (index.html)
  // -------------------------------------------------------------------------
  function initGlobalSearch() {
    const searchInput = document.getElementById('global-search-input');
    const dropdown = document.getElementById('global-search-results');
    if (!searchInput || !dropdown) return;

    // Данные подгружаются из window.SEARCH_DATA (search-data.js)
    searchInput.addEventListener('input', function () {
      const q = searchInput.value.trim().toLowerCase();
      if (!q || !window.SEARCH_DATA) {
        dropdown.classList.remove('active');
        dropdown.innerHTML = '';
        return;
      }

      const words = q.split(/\s+/);
      const matches = [];

      for (let i = 0; i < window.SEARCH_DATA.length; i++) {
        const item = window.SEARCH_DATA[i];
        const titleLower = item.title.toLowerCase();
        const modLower = item.module.toLowerCase();
        
        let score = 0;
        let matchedAll = true;

        for (let w = 0; w < words.length; w++) {
          const word = words[w];
          if (titleLower.includes(word)) {
            score += 10;
          } else if (modLower.includes(word)) {
            score += 3;
          } else {
            matchedAll = false;
            break;
          }
        }

        if (matchedAll) {
          matches.push({ item, score });
        }
      }

      matches.sort((a, b) => b.score - a.score);

      if (matches.length === 0) {
        dropdown.innerHTML = '<div style="padding:16px; color:#94a3b8; font-size:0.9rem;">Ничего не найдено. Попробуйте другой запрос (например: GC, Raft, epoll, каналы).</div>';
        dropdown.classList.add('active');
        return;
      }

      const topResults = matches.slice(0, 15);
      let resHTML = '';

      topResults.forEach(({ item }) => {
        resHTML += `
          <a href="${item.url}" class="search-result-item">
            <div class="search-res-title">${escapeHtml(item.title)}</div>
            <div class="search-res-module">${escapeHtml(item.module)} ${item.sub ? '• ' + escapeHtml(item.sub) : ''}</div>
          </a>
        `;
      });

      dropdown.innerHTML = resHTML;
      dropdown.classList.add('active');
    });

    document.addEventListener('click', function (e) {
      if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // -------------------------------------------------------------------------
  // 9. Автоцентрирование сайдбара и плавная размеренная анимация аккордеона
  // -------------------------------------------------------------------------
  function initSidebarCentering() {
    const container = document.getElementById('sidebar-content');
    if (!container) return;

    // Отмена анимации программного скролла при ручной прокрутке колесиком или тачем
    container.addEventListener('wheel', function () {
      if (container._scrollAnimId) {
        cancelAnimationFrame(container._scrollAnimId);
        container._scrollAnimId = null;
      }
    }, { passive: true });
    container.addEventListener('touchmove', function () {
      if (container._scrollAnimId) {
        cancelAnimationFrame(container._scrollAnimId);
        container._scrollAnimId = null;
      }
    }, { passive: true });

    let userHasScrolled = false;
    container.addEventListener('wheel', function () {
      userHasScrolled = true;
    }, { passive: true, once: true });
    container.addEventListener('touchmove', function () {
      userHasScrolled = true;
    }, { passive: true, once: true });

    // 1. Всегда центрируем сайдбар на текущей выбранной лекции при открытии страницы
    centerActiveLecture(false);

    requestAnimationFrame(function () {
      if (!userHasScrolled) {
        centerActiveLecture(false);
      }
    });

    setTimeout(function () {
      if (!userHasScrolled) {
        centerActiveLecture(false);
      }
    }, 120);

    window.addEventListener('pageshow', function () {
      centerActiveLecture(false);
    });

    // 2. Плавная и более медленная анимация аккордеона (сворачивание/разворачивание)
    const ANIMATION_DURATION = 480; // комфортная, плавная длительность (0.48с)
    const EASING = 'cubic-bezier(0.22, 1, 0.36, 1)';

    container.addEventListener('click', function (e) {
      const summary = e.target.closest('.nav-module-title, .nav-submodule-title');
      if (!summary) return;

      const details = summary.closest('details');
      if (!details) return;

      const content = details.querySelector('.nav-module-content') || details.querySelector('.sub-list') || details.children[1];
      if (!content) return;

      e.preventDefault();
      e.stopPropagation();

      const isOpen = details.hasAttribute('open');

      // Прерываем предыдущую анимацию этого блока, если пользователь кликает повторно
      if (content._anim) {
        content._anim.cancel();
        content._anim = null;
      }

      if (isOpen) {
        // --- СВОРАЧИВАНИЕ МОДУЛЯ ---
        const startHeight = content.offsetHeight;
        if (startHeight <= 0) {
          details.removeAttribute('open');
          return;
        }

        // Вычисляем целевой скролл для центрирования заголовка модуля
        const containerRect = container.getBoundingClientRect();
        const summaryRect = summary.getBoundingClientRect();
        const summaryTopInContent = (summaryRect.top - containerRect.top) + container.scrollTop;

        // В свёрнутом состоянии максимальный скролл уменьшится на startHeight
        const finalMaxScroll = Math.max(0, (container.scrollHeight - startHeight) - container.clientHeight);
        const desiredScrollTop = summaryTopInContent + (summaryRect.height / 2) - (container.clientHeight / 2);
        const targetScrollTop = Math.max(0, Math.min(finalMaxScroll, Math.round(desiredScrollTop)));

        // Плавно и медленно скроллим сайдбар к центру заголовка
        smoothScroll(container, targetScrollTop, ANIMATION_DURATION);

        // Плавно анимируем схлопывание высоты и прозрачности контента
        content.style.overflow = 'hidden';
        const anim = content.animate([
          { height: startHeight + 'px', opacity: 1 },
          { height: '0px', opacity: 0 }
        ], {
          duration: ANIMATION_DURATION,
          easing: EASING
        });

        content._anim = anim;

        anim.onfinish = function () {
          content._anim = null;
          details.removeAttribute('open');
          content.style.overflow = '';
          content.style.height = '';
          content.style.opacity = '';
        };

        anim.oncancel = function () {
          content._anim = null;
          content.style.overflow = '';
          content.style.height = '';
          content.style.opacity = '';
        };

      } else {
        // --- РАЗВОРАЧИВАНИЕ МОДУЛЯ ---
        details.setAttribute('open', '');
        content.style.height = 'auto';
        content.style.overflow = 'hidden';
        const fullHeight = content.offsetHeight;

        if (fullHeight <= 0) {
          content.style.overflow = '';
          return;
        }

        // Вычисляем целевой скролл
        const activeItem = details.querySelector('.nav-item.active');
        const containerRect = container.getBoundingClientRect();

        let targetScrollTop;
        if (activeItem) {
          // Если внутри находится активная лекция — центрируемся на ней
          const itemRect = activeItem.getBoundingClientRect();
          const itemTopInContent = (itemRect.top - containerRect.top) + container.scrollTop;
          const maxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
          const desired = itemTopInContent + (itemRect.height / 2) - (container.clientHeight / 2);
          targetScrollTop = Math.max(0, Math.min(maxScroll, Math.round(desired)));
        } else {
          // Иначе центрируемся на заголовке развернутого модуля
          const summaryRect = summary.getBoundingClientRect();
          const summaryTopInContent = (summaryRect.top - containerRect.top) + container.scrollTop;
          const desired = summaryTopInContent + (summaryRect.height / 2) - (container.clientHeight / 2);
          const maxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
          targetScrollTop = Math.max(0, Math.min(maxScroll, Math.round(desired)));
        }

        // Плавно скроллим контейнер синхронно с разворачиванием
        smoothScroll(container, targetScrollTop, ANIMATION_DURATION);

        // Плавно анимируем раскрытие высоты и появление контента
        const anim = content.animate([
          { height: '0px', opacity: 0 },
          { height: fullHeight + 'px', opacity: 1 }
        ], {
          duration: ANIMATION_DURATION,
          easing: EASING
        });

        content._anim = anim;

        anim.onfinish = function () {
          content._anim = null;
          content.style.overflow = '';
          content.style.height = '';
          content.style.opacity = '';
        };

        anim.oncancel = function () {
          content._anim = null;
          content.style.overflow = '';
          content.style.height = '';
          content.style.opacity = '';
        };
      }
    });
  }

  // -------------------------------------------------------------------------
  // Запуск при загрузке DOM
  // -------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', function () {
    initMermaid();
    initSidebarResize();
    initSidebarFilter();
    initSidebarCentering();
    initScrollProgress();
    initMobileMenu();
    initGlobalSearch();
  });

})();
