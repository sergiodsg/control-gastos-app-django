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
