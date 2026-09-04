/**
 * Razorpay API Reference Client Application
 * Dynamic Code Generation, Interactive Playground, Scrollspy, and Search
 */

(function () {
  'use strict';

  // State
  let currentTheme = localStorage.getItem('razorpay_docs_theme') || 'dark';
  let currentLang = localStorage.getItem('razorpay_docs_lang') || 'curl';
  let currentBaseUrl = localStorage.getItem('razorpay_docs_base_url') || 'http://localhost:8000';

  // Apply initial theme
  document.documentElement.setAttribute('data-theme', currentTheme);

  // Initialize once DOM is ready
  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initEnvironmentSelector();
    initLanguageTabs();
    initCodeCopyButtons();
    initResponseTabs();
    initPlaygrounds();
    initScrollSpy();
    initSearch();
    initMobileMenu();
  });

  // Theme Toggler
  function initTheme() {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (!toggleBtn) return;

    updateThemeButtonIcon(toggleBtn);

    toggleBtn.addEventListener('click', () => {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
      localStorage.setItem('razorpay_docs_theme', currentTheme);
      updateThemeButtonIcon(toggleBtn);
    });
  }

  function updateThemeButtonIcon(btn) {
    if (currentTheme === 'dark') {
      btn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>`;
      btn.setAttribute('title', 'Switch to Light Mode');
    } else {
      btn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>`;
      btn.setAttribute('title', 'Switch to Dark Mode');
    }
  }

  // Environment Selector
  function initEnvironmentSelector() {
    const envSelect = document.getElementById('env-select');
    if (!envSelect) return;

    envSelect.value = currentBaseUrl;
    envSelect.addEventListener('change', (e) => {
      currentBaseUrl = e.target.value;
      localStorage.setItem('razorpay_docs_base_url', currentBaseUrl);
      updateAllSnippets();
    });
  }

  // Language Tabs
  function initLanguageTabs() {
    const tabButtons = document.querySelectorAll('.lang-tab-btn');
    tabButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const lang = btn.getAttribute('data-lang');
        setLanguage(lang);
      });
    });

    setLanguage(currentLang);
  }

  function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('razorpay_docs_lang', lang);

    document.querySelectorAll('.lang-tab-btn').forEach((btn) => {
      if (btn.getAttribute('data-lang') === lang) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    updateAllSnippets();
  }

  // Generate Snippets
  function generateSnippet(method, path, body, lang) {
    const fullUrl = `${currentBaseUrl}${path}`;
    const cleanBody = body && body.trim() !== '' ? body : null;

    if (lang === 'curl') {
      let code = `curl -X ${method} "${fullUrl}"`;
      if (method === 'POST' || method === 'PUT') {
        code += ` \\\n  -H "Content-Type: application/json"`;
      }
      if (cleanBody) {
        // format nicely for bash
        try {
          const formatted = JSON.stringify(JSON.parse(cleanBody), null, 2).replace(/"/g, '\\"');
          code += ` \\\n  -d "${formatted}"`;
        } catch (_) {
          code += ` \\\n  -d '${cleanBody}'`;
        }
      }
      return code;
    }

    if (lang === 'python') {
      let code = `import requests\n\nurl = "${fullUrl}"\n`;
      let args = ['url=url'];
      if (cleanBody) {
        code += `payload = ${cleanBody}\nheaders = {"Content-Type": "application/json"}\n`;
        args.push('json=payload', 'headers=headers');
      }
      code += `\nresponse = requests.${method.toLowerCase()}(${args.join(', ')})\nprint(response.status_code)\nprint(response.json())`;
      return code;
    }

    if (lang === 'javascript') {
      let code = `const response = await fetch("${fullUrl}", {\n  method: "${method}",\n`;
      if (cleanBody) {
        code += `  headers: {\n    "Content-Type": "application/json"\n  },\n  body: JSON.stringify(${cleanBody})\n`;
      }
      code += `});\nconst data = await response.json();\nconsole.log(data);`;
      return code;
    }

    if (lang === 'go') {
      let code = `package main\n\nimport (\n\t"fmt"\n\t"net/http"\n\t"io"\n`;
      if (cleanBody) code += `\t"strings"\n`;
      code += `)\n\nfunc main() {\n\turl := "${fullUrl}"\n`;
      if (cleanBody) {
        code += `\tpayload := strings.NewReader(\`${cleanBody}\`)\n`;
        code += `\treq, _ := http.NewRequest("${method}", url, payload)\n`;
        code += `\treq.Header.Add("Content-Type", "application/json")\n`;
      } else {
        code += `\treq, _ := http.NewRequest("${method}", url, nil)\n`;
      }
      code += `\tres, _ := http.DefaultClient.Do(req)\n\tdefer res.Body.Close()\n\tbody, _ := io.ReadAll(res.Body)\n\tfmt.Println(string(body))\n}`;
      return code;
    }

    return '';
  }

  function updateAllSnippets() {
    document.querySelectorAll('.code-panel').forEach((panel) => {
      const method = panel.getAttribute('data-method') || 'GET';
      let path = panel.getAttribute('data-path') || '/';
      
      // Check if there are playground inputs that modify the path
      const pathInput = panel.querySelector('[data-param-type="path"]');
      if (pathInput && pathInput.value) {
        const paramName = pathInput.getAttribute('data-param-name');
        path = path.replace(`{${paramName}}`, encodeURIComponent(pathInput.value));
      }

      // Check query params
      const queryInputs = panel.querySelectorAll('[data-param-type="query"]');
      const queryParams = new URLSearchParams();
      queryInputs.forEach((qi) => {
        if (qi.value) queryParams.append(qi.getAttribute('data-param-name'), qi.value);
      });
      const queryString = queryParams.toString();
      if (queryString) {
        path += (path.includes('?') ? '&' : '?') + queryString;
      }

      const bodyTextarea = panel.querySelector('[data-body-input]');
      const body = bodyTextarea ? bodyTextarea.value : null;

      const codeContainer = panel.querySelector('.code-snippet-pre code');
      if (codeContainer) {
        codeContainer.textContent = generateSnippet(method, path, body, currentLang);
      }
    });
  }

  // Response Status Code Tabs
  function initResponseTabs() {
    document.querySelectorAll('.response-tabs').forEach((tabsContainer) => {
      const buttons = tabsContainer.querySelectorAll('.resp-tab-btn');
      buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
          buttons.forEach((b) => b.classList.remove('active'));
          btn.classList.add('active');

          const status = btn.getAttribute('data-status');
          const panel = btn.closest('.code-panel');
          const statusPill = panel.querySelector('.response-status-pill');
          const respPre = panel.querySelector('.response-body-pre code');

          if (statusPill) {
            statusPill.className = `response-status-pill status-${status}`;
            statusPill.textContent = `${status} ${getStatusText(status)}`;
          }

          const sampleJson = btn.getAttribute('data-sample');
          if (respPre && sampleJson) {
            try {
              respPre.textContent = JSON.stringify(JSON.parse(sampleJson), null, 2);
            } catch (_) {
              respPre.textContent = sampleJson;
            }
          }
        });
      });
    });
  }

  function getStatusText(code) {
    const map = {
      '200': 'OK',
      '201': 'Created',
      '400': 'Bad Request',
      '404': 'Not Found',
      '409': 'Conflict',
      '422': 'Unprocessable Entity',
      '502': 'Bad Gateway',
      '503': 'Service Unavailable',
    };
    return map[code] || '';
  }

  // Interactive Playground (Send Request)
  function initPlaygrounds() {
    document.querySelectorAll('.code-panel').forEach((panel) => {
      const sendBtn = panel.querySelector('.playground-send-btn');
      const inputs = panel.querySelectorAll('.playground-input, .playground-textarea');

      inputs.forEach((input) => {
        input.addEventListener('input', () => {
          updateAllSnippets();
        });
      });

      if (sendBtn) {
        sendBtn.addEventListener('click', async () => {
          const method = panel.getAttribute('data-method') || 'GET';
          let path = panel.getAttribute('data-path') || '/';

          // Replace path parameters
          const pathInputs = panel.querySelectorAll('[data-param-type="path"]');
          pathInputs.forEach((pi) => {
            const name = pi.getAttribute('data-param-name');
            const val = pi.value.trim();
            if (val) {
              path = path.replace(`{${name}}`, encodeURIComponent(val));
            }
          });

          // Query parameters
          const queryInputs = panel.querySelectorAll('[data-param-type="query"]');
          const qParams = new URLSearchParams();
          queryInputs.forEach((qi) => {
            const val = qi.value.trim();
            if (val) qParams.append(qi.getAttribute('data-param-name'), val);
          });
          const qStr = qParams.toString();
          if (qStr) {
            path += (path.includes('?') ? '&' : '?') + qStr;
          }

          const targetUrl = `${currentBaseUrl}${path}`;
          const bodyInput = panel.querySelector('[data-body-input]');
          let bodyPayload = null;
          if (bodyInput && bodyInput.value.trim() && method !== 'GET') {
            bodyPayload = bodyInput.value.trim();
          }

          const statusPill = panel.querySelector('.response-status-pill');
          const respPre = panel.querySelector('.response-body-pre code');
          const originalBtnText = sendBtn.innerHTML;

          sendBtn.disabled = true;
          sendBtn.innerHTML = `
            <svg class="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="16"></circle>
            </svg>
            Sending...`;

          const startTime = performance.now();

          try {
            const fetchOptions = {
              method: method,
              headers: {
                'Accept': 'application/json',
              },
            };

            if (bodyPayload) {
              fetchOptions.headers['Content-Type'] = 'application/json';
              fetchOptions.body = bodyPayload;
            }

            const response = await fetch(targetUrl, fetchOptions);
            const duration = Math.round(performance.now() - startTime);

            const status = response.status;
            let dataText = '';
            try {
              const data = await response.json();
              dataText = JSON.stringify(data, null, 2);
            } catch (_) {
              dataText = await response.text();
            }

            if (statusPill) {
              statusPill.className = `response-status-pill status-${status}`;
              statusPill.textContent = `${status} ${response.statusText || getStatusText(String(status))} • ${duration}ms`;
            }

            if (respPre) {
              respPre.textContent = dataText;
            }
          } catch (err) {
            const duration = Math.round(performance.now() - startTime);
            if (statusPill) {
              statusPill.className = `response-status-pill status-503`;
              statusPill.textContent = `Network Error • ${duration}ms`;
            }
            if (respPre) {
              respPre.textContent = JSON.stringify(
                {
                  error: "Failed to fetch",
                  message: `Could not connect to ${targetUrl}. Is the backend running?`,
                  details: err.message,
                  tip: "To test live requests, start your backend server: uvicorn src.main:app --port 8000"
                },
                null,
                2
              );
            }
          } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalBtnText;
          }
        });
      }
    });
  }

  // Copy Buttons
  function initCodeCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        let textToCopy = '';
        const targetSelector = btn.getAttribute('data-copy-target');

        if (targetSelector) {
          const target = btn.closest('.code-panel')?.querySelector(targetSelector) || document.querySelector(targetSelector);
          if (target) textToCopy = target.textContent;
        } else {
          const parent = btn.parentElement;
          const codeEl = parent?.querySelector('code') || parent?.querySelector('.endpoint-path');
          if (codeEl) textToCopy = codeEl.textContent;
        }

        if (textToCopy) {
          navigator.clipboard.writeText(textToCopy.trim()).then(() => {
            const orig = btn.innerHTML;
            btn.innerHTML = `<span style="color: #34d399; font-size: 0.75rem; font-weight: 600;">✓ Copied</span>`;
            setTimeout(() => {
              btn.innerHTML = orig;
            }, 1800);
          });
        }
      });
    });
  }

  // ScrollSpy for Sidebar
  function initScrollSpy() {
    const sections = document.querySelectorAll('.doc-section');
    const navItems = document.querySelectorAll('.sidebar .nav-item');

    if (sections.length === 0 || navItems.length === 0) return;

    window.addEventListener('scroll', () => {
      let currentId = '';
      const scrollPos = window.scrollY + 120;

      sections.forEach((section) => {
        const top = section.offsetTop;
        const height = section.offsetHeight;
        if (scrollPos >= top && scrollPos < top + height) {
          currentId = section.getAttribute('id');
        }
      });

      if (currentId) {
        navItems.forEach((item) => {
          const href = item.getAttribute('href');
          if (href === `#${currentId}`) {
            item.classList.add('active');
          } else {
            item.classList.remove('active');
          }
        });
      }
    }, { passive: true });
  }

  // Search Modal (Cmd+K)
  function initSearch() {
    const trigger = document.getElementById('search-trigger');
    const modal = document.getElementById('search-modal');
    const input = document.getElementById('search-input');
    const resultsContainer = document.getElementById('search-results');

    if (!trigger || !modal || !input || !resultsContainer) return;

    // Collect all searchable sections
    const items = [];
    document.querySelectorAll('.doc-section').forEach((sec) => {
      const id = sec.getAttribute('id');
      const title = sec.querySelector('.endpoint-title')?.textContent || id;
      const path = sec.querySelector('.endpoint-path')?.textContent || '';
      const method = sec.querySelector('.method-tag')?.textContent || '';
      const desc = sec.querySelector('.endpoint-description')?.textContent || '';

      items.push({ id, title, path, method, desc });
    });

    function openModal() {
      modal.classList.add('open');
      input.value = '';
      renderResults(items);
      input.focus();
    }

    function closeModal() {
      modal.classList.remove('open');
    }

    trigger.addEventListener('click', openModal);

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (modal.classList.contains('open')) {
          closeModal();
        } else {
          openModal();
        }
      }
      if (e.key === 'Escape' && modal.classList.contains('open')) {
        closeModal();
      }
    });

    input.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        renderResults(items);
        return;
      }
      const filtered = items.filter(
        (it) =>
          it.title.toLowerCase().includes(q) ||
          it.path.toLowerCase().includes(q) ||
          it.desc.toLowerCase().includes(q) ||
          it.method.toLowerCase().includes(q)
      );
      renderResults(filtered);
    });

    function renderResults(list) {
      if (list.length === 0) {
        resultsContainer.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-faint); font-size: 0.85rem;">No matching endpoints or guides found</div>`;
        return;
      }

      resultsContainer.innerHTML = list
        .map(
          (it) => `
        <div class="search-result-item" data-target="${it.id}">
          <div class="search-result-info">
            <div class="search-result-title">${it.title}</div>
            <div class="search-result-path">${it.path || it.id}</div>
          </div>
          ${it.method ? `<span class="method-tag ${it.method.toLowerCase()}">${it.method}</span>` : ''}
        </div>`
        )
        .join('');

      resultsContainer.querySelectorAll('.search-result-item').forEach((item) => {
        item.addEventListener('click', () => {
          const targetId = item.getAttribute('data-target');
          closeModal();
          const targetEl = document.getElementById(targetId);
          if (targetEl) {
            targetEl.scrollIntoView({ behavior: 'smooth' });
          }
        });
      });
    }
  }

  // Mobile Menu & Off-Canvas Drawer
  function initMobileMenu() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');

    if (!mobileMenuBtn || !sidebar || !sidebarBackdrop) return;

    function openMobileMenu() {
      sidebar.classList.add('mobile-open');
      sidebarBackdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeMobileMenu() {
      sidebar.classList.remove('mobile-open');
      sidebarBackdrop.classList.remove('open');
      document.body.style.overflow = '';
    }

    mobileMenuBtn.addEventListener('click', () => {
      if (sidebar.classList.contains('mobile-open')) {
        closeMobileMenu();
      } else {
        openMobileMenu();
      }
    });

    sidebarBackdrop.addEventListener('click', closeMobileMenu);

    sidebar.querySelectorAll('.nav-item').forEach((item) => {
      item.addEventListener('click', closeMobileMenu);
    });
  }

})();

