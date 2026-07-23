// Generic "action sheet" used by the phone-simplified transaction tables.
// Pages that want it must include a #mobileActionsModal with buttons
// #mobileActionView / #mobileActionDuplicate / #mobileActionEdit / #mobileActionDelete.
// Each row's expand button calls openMobileActionSheet({view, duplicate, edit, delete})
// with the same callbacks the desktop row buttons already use; omitted/undefined
// actions are hidden from the sheet (e.g. a Viewer has no duplicate/edit/delete).
window.openMobileActionSheet = function (actions) {
    const modal = document.getElementById('mobileActionsModal');
    if (!modal) return;

    const buttonIdByAction = {
        view: 'mobileActionView',
        duplicate: 'mobileActionDuplicate',
        edit: 'mobileActionEdit',
        delete: 'mobileActionDelete'
    };

    Object.keys(buttonIdByAction).forEach(function (key) {
        const btn = document.getElementById(buttonIdByAction[key]);
        if (!btn) return;
        const fn = actions ? actions[key] : null;
        if (typeof fn === 'function') {
            btn.style.display = '';
            btn.onclick = function () {
                CFModal.close('mobileActionsModal');
                fn();
            };
        } else {
            btn.style.display = 'none';
        }
    });

    CFModal.open('mobileActionsModal');
};
