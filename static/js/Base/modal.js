/**
 * CashFlow Modal — reemplazo de bootstrap.Modal
 */
const CFModal = (function () {
    const openModals = [];

    function resolveEl(target) {
        if (typeof target === 'string') {
            return document.querySelector(target.startsWith('#') ? target : `#${target}`);
        }
        return target;
    }

    function open(target) {
        const modal = resolveEl(target);
        if (!modal) return;

        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('cf-modal-open');
        openModals.push(modal);

        const focusable = modal.querySelector('input, select, textarea, button:not(.cf-modal__close)');
        if (focusable) focusable.focus();
    }

    function close(target) {
        const modal = target ? resolveEl(target) : openModals[openModals.length - 1];
        if (!modal) return;

        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');

        const idx = openModals.indexOf(modal);
        if (idx > -1) openModals.splice(idx, 1);

        if (openModals.length === 0) {
            document.body.classList.remove('cf-modal-open');
        }
    }

    function closeAll() {
        while (openModals.length) {
            close(openModals[openModals.length - 1]);
        }
    }

    function init() {
        document.addEventListener('click', function (e) {
            const trigger = e.target.closest('[data-cf-modal]');
            if (trigger) {
                e.preventDefault();
                open(trigger.getAttribute('data-cf-modal'));
                return;
            }

            const dismiss = e.target.closest('[data-cf-dismiss="modal"]');
            if (dismiss) {
                e.preventDefault();
                const modal = dismiss.closest('.cf-modal');
                if (modal) close(modal);
                return;
            }

            if (e.target.classList.contains('cf-modal__backdrop')) {
                const modal = e.target.closest('.cf-modal');
                if (modal && modal.getAttribute('data-cf-modal-static') === 'true') {
                    return;
                }
                if (modal) close(modal);
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && openModals.length) {
                const modal = openModals[openModals.length - 1];
                if (modal.getAttribute('data-cf-modal-static') === 'true') {
                    return;
                }
                close(modal);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    return { open, close, closeAll };
})();

window.CFModal = CFModal;
