(function () {
    // Apply theme preference from localStorage
    function applyThemePreference() {
        const theme = localStorage.getItem('theme_pref') || 'light';
        document.documentElement.setAttribute('data-theme', theme);
    }

    function applyCurrencyPreference() {
        const pref = localStorage.getItem('currency_pref') || 'USD';
        const usdElements = document.querySelectorAll('.currency-usd-content');
        const bsElements = document.querySelectorAll('.currency-bs-content');

        if (pref === 'USD') {
            usdElements.forEach(function (el) { el.classList.remove('cf-hidden', 'd-none'); });
            bsElements.forEach(function (el) { el.classList.add('cf-hidden', 'd-none'); });
        } else {
            usdElements.forEach(function (el) { el.classList.add('cf-hidden', 'd-none'); });
            bsElements.forEach(function (el) { el.classList.remove('cf-hidden', 'd-none'); });
        }
    }

    function updateTransactionsContainer(url) {
        const container = document.getElementById('transactions-container');
        if (!container) return;

        const kpiContainer = document.getElementById('kpi-container');

        container.classList.add('is-loading');
        if (kpiContainer) kpiContainer.classList.add('is-loading');

        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.text(); })
            .then(function (html) {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newContent = doc.getElementById('transactions-container');
                const newKpiContent = kpiContainer ? doc.getElementById('kpi-container') : null;

                if (newContent) {
                    container.innerHTML = newContent.innerHTML;
                    history.pushState(null, '', url);
                }
                if (kpiContainer && newKpiContent) {
                    kpiContainer.innerHTML = newKpiContent.innerHTML;
                }
                container.classList.remove('is-loading');
                if (kpiContainer) kpiContainer.classList.remove('is-loading');
                applyCurrencyPreference();
                if (typeof window.initResizableTables === 'function') window.initResizableTables();
            })
            .catch(function () {
                container.classList.remove('is-loading');
                if (kpiContainer) kpiContainer.classList.remove('is-loading');
            });
    }

    function initAjaxSorting() {
        const container = document.getElementById('transactions-container');
        if (!container) return;

        container.addEventListener('click', function (e) {
            const link = e.target.closest('.ajax-link');
            if (!link) return;

            e.preventDefault();
            const url = link.getAttribute('href');
            if (!url || url === '#') return;

            updateTransactionsContainer(url);
        });

        window.addEventListener('popstate', function () {
            location.reload();
        });
    }

    function initDynamicSearch() {
        const handleFilterChange = function (e) {
            const input = e.target.closest('.dynamic-search');
            if (!input) return;

            const form = input.closest('form');
            if (!form) return;

            // Lógica de desactivación de periodo si hay rango de fechas
            const periodSelect = form.querySelector('select[name="filter_type"]');
            const dateFrom = form.querySelector('input[name="date_from"]');
            const dateTo = form.querySelector('input[name="date_to"]');

            if (periodSelect && dateFrom && dateTo) {
                const hasDate = dateFrom.value || dateTo.value;
                if (hasDate) {
                    periodSelect.value = 'custom';
                    periodSelect.style.opacity = '0.5';
                    periodSelect.style.pointerEvents = 'none';
                    periodSelect.tabIndex = -1;
                } else {
                    periodSelect.style.opacity = '1';
                    periodSelect.style.pointerEvents = 'auto';
                    periodSelect.tabIndex = 0;
                }
            }

            clearTimeout(input._searchTimeout);
            input._searchTimeout = setTimeout(function () {
                const formData = new FormData(form);
                const params = new URLSearchParams();
                for (const pair of formData.entries()) {
                    // Si el periodo está "desactivado" pero es custom, nos aseguramos de enviarlo
                    if (pair[1] || pair[0] === 'filter_type') {
                        params.append(pair[0], pair[1]);
                    }
                }
                const url = (form.getAttribute('action') || window.location.pathname) + '?' + params.toString();
                updateTransactionsContainer(url);
            }, 500);
        };

        document.addEventListener('input', handleFilterChange);
        document.addEventListener('change', function (e) {
            const input = e.target.closest('.dynamic-search');
            if (input && (input.tagName === 'SELECT' || input.getAttribute('type') === 'date')) {
                handleFilterChange(e);
            }
        });

        // Inicializar estado de los filtros al cargar
        const initialSearch = document.querySelector('.dynamic-search');
        if (initialSearch) {
            const form = initialSearch.closest('form');
            if (form) {
                const periodSelect = form.querySelector('select[name="filter_type"]');
                const dateFrom = form.querySelector('input[name="date_from"]');
                const dateTo = form.querySelector('input[name="date_to"]');
                if (periodSelect && (dateFrom?.value || dateTo?.value)) {
                    periodSelect.value = 'custom';
                    periodSelect.style.opacity = '0.5';
                    periodSelect.style.pointerEvents = 'none';
                }
            }
        }

        // Prevenir envío del formulario al presionar Enter en búsqueda dinámica
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && e.target.classList.contains('dynamic-search')) {
                e.preventDefault();
            }
        });
    }

    function initSidebar() {
        const layout = document.getElementById('appLayout');
        const mobileBtn = document.getElementById('sidebarMobileBtn');
        const backdrop = document.getElementById('sidebarBackdrop');

        if (!layout || !layout.classList.contains('has-sidebar')) return;

        function openDrawer() {
            layout.classList.add('sidebar-drawer-open');
            document.body.style.overflow = 'hidden';
            if (mobileBtn) {
                mobileBtn.setAttribute('aria-expanded', 'true');
                mobileBtn.setAttribute('aria-label', 'Cerrar menú');
            }
        }

        function closeDrawer() {
            layout.classList.remove('sidebar-drawer-open');
            document.body.style.overflow = '';
            if (mobileBtn) {
                mobileBtn.setAttribute('aria-expanded', 'false');
                mobileBtn.setAttribute('aria-label', 'Abrir menú');
            }
        }

        function isMobile() {
            return window.innerWidth <= 992;
        }

        mobileBtn?.addEventListener('click', function (e) {
            e.preventDefault();
            if (layout.classList.contains('sidebar-drawer-open')) {
                closeDrawer();
            } else {
                openDrawer();
            }
        });

        backdrop?.addEventListener('click', closeDrawer);

        layout.querySelectorAll('.app-sidebar-link').forEach(function (link) {
            link.addEventListener('click', function () {
                if (isMobile()) {
                    closeDrawer();
                }
            });
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && layout.classList.contains('sidebar-drawer-open')) {
                closeDrawer();
            }
        });

        window.addEventListener('resize', function () {
            if (!isMobile()) {
                closeDrawer();
            }
        });
    }

    window.addEventListener('DOMContentLoaded', function () {
        initSidebar();
        applyThemePreference();
        applyCurrencyPreference();
        initAjaxSorting();
        initDynamicSearch();
    });
})();
