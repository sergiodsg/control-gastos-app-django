/**
 * CashFlow Dropdown — reemplazo de bootstrap dropdown
 */
(function () {
    function closeAll(except) {
        document.querySelectorAll('.cf-dropdown.is-open').forEach(function (el) {
            if (el !== except) el.classList.remove('is-open');
        });
    }

    function init() {
        document.addEventListener('click', function (e) {
            const toggle = e.target.closest('[data-cf-dropdown]');
            if (toggle) {
                e.preventDefault();
                e.stopPropagation();
                const dropdown = toggle.closest('.cf-dropdown');
                if (dropdown) {
                    const isOpen = dropdown.classList.contains('is-open');
                    closeAll();
                    if (!isOpen) dropdown.classList.add('is-open');
                }
                return;
            }

            if (!e.target.closest('.cf-dropdown')) {
                closeAll();
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeAll();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
