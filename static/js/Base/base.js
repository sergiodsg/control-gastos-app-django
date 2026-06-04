(function () {
    const layout = document.getElementById('appLayout');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    const mobileBtn = document.getElementById('sidebarMobileBtn');
    const backdrop = document.getElementById('sidebarBackdrop');

    if (!layout) return;

    const STORAGE_KEY = 'cashflow_sidebar_collapsed';

    function setCollapsed(collapsed) {
        layout.classList.toggle('app-sidebar-collapsed', collapsed);
    }

    function openDrawer() {
        layout.classList.add('sidebar-drawer-open');
        document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
        layout.classList.remove('sidebar-drawer-open');
        document.body.style.overflow = '';
    }

    if (layout.classList.contains('has-sidebar') && window.innerWidth > 992) {
        if (localStorage.getItem(STORAGE_KEY) === '1') {
            setCollapsed(true);
        }
    }

    collapseBtn?.addEventListener('click', function () {
        const collapsed = !layout.classList.contains('app-sidebar-collapsed');
        setCollapsed(collapsed);
        localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
    });

    mobileBtn?.addEventListener('click', function (e) {
        e.preventDefault();
        openDrawer();
    });

    backdrop?.addEventListener('click', closeDrawer);

    layout.querySelectorAll('.app-sidebar-link').forEach(function (link) {
        link.addEventListener('click', function () {
            if (window.innerWidth <= 992) {
                closeDrawer();
            }
        });
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 992) {
            closeDrawer();
        }
    });
})();

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

        // Mostrar un indicador de carga ligero
        container.style.opacity = '0.5';
        container.style.pointerEvents = 'none';

        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newContent = doc.getElementById('transactions-container');
                
                if (newContent) {
                    container.innerHTML = newContent.innerHTML;
                    history.pushState(null, '', url);
                }
                container.style.opacity = '1';
                container.style.pointerEvents = 'auto';
                
                // Re-aplicar preferencia de moneda si es necesario
                if (typeof applyCurrencyPreference === 'function') applyCurrencyPreference();
            })
            .catch(() => {
                container.style.opacity = '1';
                container.style.pointerEvents = 'auto';
            });
    });

    window.addEventListener('popstate', function() {
        location.reload(); // Recargar al usar botones atrás/adelante para simplicidad
    });
}

window.addEventListener('DOMContentLoaded', function () {
    applyCurrencyPreference();
    initAjaxSorting();
});

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

window.addEventListener('DOMContentLoaded', function () {
    applyCurrencyPreference();
});

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

window.addEventListener('DOMContentLoaded', function () {
    applyCurrencyPreference();
});

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

window.addEventListener('DOMContentLoaded', function () {
    applyCurrencyPreference();
});
