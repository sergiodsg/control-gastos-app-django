/**
 * CashFlow Alert dismiss
 */
(function () {
    function init() {
        document.addEventListener('click', function (e) {
            const btn = e.target.closest('[data-cf-dismiss="alert"]');
            if (!btn) return;
            const alert = btn.closest('.cf-alert');
            if (alert) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-8px)';
                alert.style.transition = 'opacity 0.2s, transform 0.2s';
                setTimeout(function () { alert.remove(); }, 200);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
