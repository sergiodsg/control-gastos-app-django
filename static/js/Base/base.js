(function () {
    const STORAGE_KEY = 'cashflow_sidebar_collapsed';

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

    function initAjaxSorting() {
        const container = document.getElementById('transactions-container');
        if (!container) return;

        container.addEventListener('click', function (e) {
            const link = e.target.closest('.ajax-link');
            if (!link) return;

            e.preventDefault();
            const url = link.getAttribute('href');
            if (!url || url === '#') return;

            container.style.opacity = '0.5';
            container.style.pointerEvents = 'none';

            fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) { return r.text(); })
                .then(function (html) {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const newContent = doc.getElementById('transactions-container');

                    if (newContent) {
                        container.innerHTML = newContent.innerHTML;
                        history.pushState(null, '', url);
                    }
                    container.style.opacity = '1';
                    container.style.pointerEvents = 'auto';
                    applyCurrencyPreference();
                })
                .catch(function () {
                    container.style.opacity = '1';
                    container.style.pointerEvents = 'auto';
                });
        });

        window.addEventListener('popstate', function () {
            location.reload();
        });
    }

    function initSidebar() {
        const layout = document.getElementById('appLayout');
        const collapseBtn = document.getElementById('sidebarCollapseBtn');
        const mobileBtn = document.getElementById('sidebarMobileBtn');
        const backdrop = document.getElementById('sidebarBackdrop');

        if (!layout || !layout.classList.contains('has-sidebar')) return;

        function setCollapsed(collapsed) {
            layout.classList.toggle('app-sidebar-collapsed', collapsed);
            if (collapseBtn) {
                collapseBtn.setAttribute('aria-label', collapsed ? 'Expandir menú' : 'Colapsar menú');
            }
        }

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

        if (!isMobile() && localStorage.getItem(STORAGE_KEY) === '1') {
            setCollapsed(true);
        }

        collapseBtn?.addEventListener('click', function () {
            if (isMobile()) return;
            const collapsed = !layout.classList.contains('app-sidebar-collapsed');
            setCollapsed(collapsed);
            localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
        });

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
            } else {
                layout.classList.remove('app-sidebar-collapsed');
            }
        });
    }

    window.addEventListener('DOMContentLoaded', function () {
        initSidebar();
        applyCurrencyPreference();
        initAjaxSorting();
    });
})();
