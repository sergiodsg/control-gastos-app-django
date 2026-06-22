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

window.initFormCategoriesDropdown = function(selectElement, dropdownEl, initialColorsMap) {
    if (!selectElement || !dropdownEl) return;
    const toggleBtn = dropdownEl.querySelector('.cf-dropdown-multiselect__toggle');
    const menuEl = dropdownEl.querySelector('.cf-dropdown-multiselect__menu');
    if (!toggleBtn || !menuEl) return;

    const toggleText = toggleBtn.querySelector('.cf-dropdown-multiselect__selected-text');
    let colorsMap = initialColorsMap || {};

    function updateText() {
        const checked = [];
        menuEl.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
            const badge = cb.nextElementSibling;
            checked.push(badge ? badge.textContent.trim() : '');
        });
        if (checked.length === 0) {
            toggleText.textContent = "Seleccionar categorías";
        } else if (checked.length === 1) {
            toggleText.textContent = checked[0];
        } else {
            toggleText.textContent = `${checked.length} seleccionadas`;
        }
    }

    function rebuild(newColorsMap) {
        if (newColorsMap) {
            colorsMap = newColorsMap;
        }
        menuEl.innerHTML = '';
        
        if (selectElement.options.length === 0) {
            const noCats = document.createElement('div');
            noCats.className = 'cf-text-muted cf-fs-sm cf-p-2';
            noCats.textContent = 'Sin categorías disponibles';
            menuEl.appendChild(noCats);
            updateText();
            return;
        }

        Array.from(selectElement.options).forEach(opt => {
            if (!opt.value) return;

            const label = document.createElement('label');
            label.className = 'cf-dropdown-multiselect__item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'cf-checkbox';
            checkbox.value = opt.value;
            checkbox.checked = opt.selected;

            checkbox.addEventListener('change', function() {
                opt.selected = checkbox.checked;
                selectElement.dispatchEvent(new Event('change', { bubbles: true }));
                updateText();
            });

            const badge = document.createElement('span');
            badge.className = 'cf-badge cf-badge--pill';
            badge.textContent = opt.textContent;
            badge.style.border = 'none';
            badge.style.padding = '2px 8px';
            badge.style.fontSize = '0.75rem';
            badge.style.color = '#fff';
            
            const color = colorsMap[opt.value] || '#6c757d';
            badge.style.backgroundColor = color;

            label.appendChild(checkbox);
            label.appendChild(badge);
            menuEl.appendChild(label);
        });
        updateText();
    }

    rebuild();

    selectElement.rebuildCustomDropdown = rebuild;
};

