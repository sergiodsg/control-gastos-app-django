function initTransacciones(config) {
    const bcvRate = config.bcvRate;
    let currentInputCurrency = 'USD';

    // Definir funciones globales inmediatamente
    window.resetForm = function () {
        const form = document.getElementById('transactionForm');
        if (!form) return;
        form.reset();
        form.action = config.crearUrl;
        document.getElementById('modalTitle').innerText = 'Nueva Transacción';

        document.getElementById('manualRateSwitch').checked = false;
        const rateField = document.querySelector('input[name="daily_rate"]');
        rateField.value = bcvRate;
        rateField.disabled = true;
        loadRateForDate(form.querySelector('[name="date"]').value);

        document.getElementById('type_egreso').checked = true;
        currentInputCurrency = 'USD';
        document.getElementById('id_amount_display').value = '';
        updateCurrencyUI();
        updateValuationVisibility();
    };

    window.editTransaction = function (id, date, account, ref, desc, notes, cat, project, valuation, status, bs, usd, rate) {
        const form = document.getElementById('transactionForm');
        if (!form) return;
        form.action = '/transacciones/guardar/' + id + '/';
        document.getElementById('modalTitle').innerText = 'Editar Transacción';

        form.querySelector('[name="date"]').value = date;
        form.querySelector('[name="account"]').value = account;
        document.getElementById('id_reference_number_custom').value = ref;
        form.querySelector('[name="reference_number"]').value = ref;
        form.querySelector('[name="description"]').value = desc;
        form.querySelector('[name="notes"]').value = notes;
        form.querySelector('[name="category"]').value = cat;
        form.querySelector('[name="project"]').value = project;
        form.querySelector('[name="status"]').value = status;
        form.querySelector('[name="amount_bs"]').value = bs.toString().replace(',', '.');
        form.querySelector('[name="amount_usd"]').value = usd.toString().replace(',', '.');
        form.querySelector('[name="daily_rate"]').value = rate.toString().replace(',', '.');

        const usdNum = parseFloat(usd.toString().replace(',', '.'));
        if (usdNum < 0) {
            document.getElementById('type_egreso').checked = true;
        } else {
            document.getElementById('type_ingreso').checked = true;
        }

        const vSelect = document.querySelector('select[name="valuation"]');
        if (vSelect) vSelect.value = valuation;
        
        document.getElementById('manualRateSwitch').checked = true;
        document.querySelector('[name="daily_rate"]').disabled = false;

        currentInputCurrency = (usdNum !== 0) ? 'USD' : 'BS';
        document.getElementById('id_amount_display').value = Math.abs((currentInputCurrency === 'USD') ? usdNum : parseFloat(bs.toString().replace(',', '.')));
        updateCurrencyUI();
        updateValuationVisibility();
        CFModal.open('transactionModal');
    };

    window.duplicateTransaction = function (date, account, ref, desc, notes, cat, project, valuation, status, bs, usd, rate) {
        window.resetForm();
        const form = document.getElementById('transactionForm');
        if (!form) return;
        form.action = config.crearUrl;
        document.getElementById('modalTitle').innerText = 'Duplicar Transacción (Nueva)';

        form.querySelector('[name="date"]').value = date;
        form.querySelector('[name="account"]').value = account;
        document.getElementById('id_reference_number_custom').value = ref;
        form.querySelector('[name="reference_number"]').value = ref;
        form.querySelector('[name="description"]').value = desc;
        form.querySelector('[name="notes"]').value = notes;
        form.querySelector('[name="category"]').value = cat;
        form.querySelector('[name="project"]').value = project;
        form.querySelector('[name="status"]').value = status;
        form.querySelector('[name="amount_bs"]').value = bs.toString().replace(',', '.');
        form.querySelector('[name="amount_usd"]').value = usd.toString().replace(',', '.');
        form.querySelector('[name="daily_rate"]').value = rate.toString().replace(',', '.');

        const usdNum = parseFloat(usd.toString().replace(',', '.'));
        if (usdNum < 0) {
            document.getElementById('type_egreso').checked = true;
        } else {
            document.getElementById('type_ingreso').checked = true;
        }

        const vSelect = document.querySelector('select[name="valuation"]');
        if (vSelect) vSelect.value = valuation;
        
        document.getElementById('manualRateSwitch').checked = true;
        document.querySelector('[name="daily_rate"]').disabled = false;

        currentInputCurrency = (usdNum !== 0) ? 'USD' : 'BS';
        document.getElementById('id_amount_display').value = Math.abs((currentInputCurrency === 'USD') ? usdNum : parseFloat(bs.toString().replace(',', '.')));
        
        updateCurrencyUI();
        updateValuationVisibility();
        CFModal.open('transactionModal');
    };

    // Auxiliares privados
    function loadRateForDate(dateValue) {
        const manualRateSwitch = document.getElementById('manualRateSwitch');
        const dailyRateField = document.querySelector('input[name="daily_rate"]');
        if (!dateValue || !manualRateSwitch || manualRateSwitch.checked) return;
        fetch(config.bcvRatesUrl + '?date=' + dateValue + '&currency=USD')
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (payload) {
                if (!payload || !payload.ok || typeof payload.rate !== 'number') return;
                if (dailyRateField) {
                    dailyRateField.value = payload.rate.toFixed(4);
                    syncHiddenFields();
                }
            })
            .catch(function () {});
    }

    function updateCurrencyUI() {
        const currencyAddon = document.getElementById('currencyAddon');
        const nextCurrencyLabel = document.getElementById('nextCurrencyLabel');
        if (!currencyAddon || !nextCurrencyLabel) return;
        if (currentInputCurrency === 'USD') {
            currencyAddon.innerText = '$';
            nextCurrencyLabel.innerText = 'BS';
        } else {
            currencyAddon.innerText = 'Bs';
            nextCurrencyLabel.innerText = 'USD';
        }
        syncHiddenFields();
    }

    function syncHiddenFields() {
        const form = document.getElementById('transactionForm');
        if (!form) return;

        const amountDisplay = document.getElementById('id_amount_display');
        const amountUsdField = form.querySelector('input[name="amount_usd"]');
        const amountBsField = form.querySelector('input[name="amount_bs"]');
        const dailyRateField = form.querySelector('input[name="daily_rate"]');
        if (!amountDisplay || !amountUsdField || !amountBsField || !dailyRateField) return;
        let val = Math.abs(parseFloat(amountDisplay.value)) || 0;
        const rate = parseFloat(dailyRateField.value) || 1;
        const isEgreso = document.getElementById('type_egreso').checked;
        if (isEgreso && val > 0) val = -val;
        if (currentInputCurrency === 'USD') {
            amountUsdField.value = val.toFixed(2);
            amountBsField.value = (val * rate).toFixed(2);
        } else {
            amountBsField.value = val.toFixed(2);
            amountUsdField.value = (rate !== 0) ? (val / rate).toFixed(2) : 0;
        }
        updateTypeColors();
    }

    function updateTypeColors() {
        const amountDisplay = document.getElementById('id_amount_display');
        const isEgreso = document.getElementById('type_egreso').checked;
        if (amountDisplay) {
            amountDisplay.classList.toggle('cf-text-danger', isEgreso);
            amountDisplay.classList.toggle('cf-text-success', !isEgreso);
            amountDisplay.classList.add('cf-fw-bold');
        }
    }

    function updateValuationVisibility() {
        const form = document.getElementById('transactionForm');
        if (!form) return;

        const amountUsdField = form.querySelector('input[name="amount_usd"]');
        const projectSelect = form.querySelector('select[name="project"]');
        const valuationContainer = document.getElementById('valuationContainer');
        const projectsData = config.projectsData || {};
        if (!amountUsdField || !projectSelect || !valuationContainer) return;

        const val = parseFloat(amountUsdField.value) || 0;
        const projectId = projectSelect.value;
        if (val > 0 && projectId && projectsData[projectId] && projectsData[projectId].length > 0) {
            valuationContainer.style.display = 'block';
            filterValuations(projectId);
        } else {
            valuationContainer.style.display = 'none';
            const vSelect = form.querySelector('select[name="valuation"]');
            if (vSelect) vSelect.value = '';
        }
    }

    function filterValuations(projectId) {
        const form = document.getElementById('transactionForm');
        if (!form) return;

        const valuationSelect = form.querySelector('select[name="valuation"]');
        const projectsData = config.projectsData || {};
        if (!valuationSelect) return;
        const valuations = projectsData[projectId] || [];
        const currentValuationId = valuationSelect.value;
        valuationSelect.innerHTML = '<option value="">---------</option>';
        valuations.forEach(function (v) {
            const option = document.createElement('option');
            option.value = v.id;
            option.text = v.name + ' (' + parseFloat(v.amount_usd).toFixed(2) + ' $)';
            if (v.id.toString() === currentValuationId) option.selected = true;
            valuationSelect.appendChild(option);
        });
    }

    // Inicializar listeners solo cuando el DOM esté listo
    function setupListeners() {
        const form = document.getElementById('transactionForm');
        if (!form) return;

        const amountDisplay = document.getElementById('id_amount_display');
        const dailyRateField = form.querySelector('input[name="daily_rate"]');
        const manualRateSwitch = document.getElementById('manualRateSwitch');
        const dateField = form.querySelector('input[name="date"]');
        const projectSelect = form.querySelector('select[name="project"]');
        const currencyToggleBtn = document.getElementById('currencyToggleBtn');

        if (projectSelect) projectSelect.addEventListener('change', updateValuationVisibility);
        
        form.querySelectorAll('input[name="transaction_type"]').forEach(function (radio) {
            radio.addEventListener('change', syncHiddenFields);
        });

        if (currencyToggleBtn) {
            currencyToggleBtn.addEventListener('click', function (e) {
                e.preventDefault();
                const currentVal = parseFloat(amountDisplay.value) || 0;
                const rate = parseFloat(dailyRateField.value) || 1;
                if (currentInputCurrency === 'USD') {
                    amountDisplay.value = (currentVal * rate).toFixed(2);
                    currentInputCurrency = 'BS';
                } else {
                    amountDisplay.value = (rate !== 0) ? (currentVal / rate).toFixed(2) : 0;
                    currentInputCurrency = 'USD';
                }
                updateCurrencyUI();
            });
        }

        if (amountDisplay) {
            amountDisplay.addEventListener('input', function () {
                syncHiddenFields();
                updateValuationVisibility();
            });
        }
        if (dailyRateField) dailyRateField.addEventListener('input', syncHiddenFields);

        if (manualRateSwitch) {
            manualRateSwitch.addEventListener('change', function (e) {
                dailyRateField.disabled = !e.target.checked;
                if (!e.target.checked) loadRateForDate(dateField.value);
            });
            dailyRateField.disabled = !manualRateSwitch.checked;
        }

        if (dateField) {
            dateField.addEventListener('change', function () { loadRateForDate(this.value); });
        }

        if (form) {
            form.addEventListener('submit', function (e) {
                const amount = parseFloat(amountDisplay.value) || 0;
                if (amount === 0) {
                    e.preventDefault();
                    alert('El monto de la transacción no puede ser cero.');
                    return;
                }
                if (dailyRateField) dailyRateField.disabled = false;
            });
        }

        const refInput = document.getElementById('id_reference_number_custom');
        if (refInput) {
            refInput.addEventListener('input', function (e) {
                form.querySelector('[name="reference_number"]').value = e.target.value;
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupListeners);
    } else {
        setupListeners();
    }

    // Otras funciones globales que no dependen del DOM del formulario
    window.viewDetail = function (id) {
        const content = document.getElementById('detailContent');
        if (!content) return;
        content.innerHTML = '<div class="cf-text-center cf-py-4"><div class="cf-spinner"></div></div>';
        CFModal.open('detailModal');
        fetch('/transacciones/detalle/' + id + '/')
            .then(function (r) { return r.text(); })
            .then(function (html) { content.innerHTML = html; })
            .catch(function () {
                content.innerHTML = '<div class="cf-alert cf-alert--danger">Error al cargar los detalles.</div>';
            });
    };

    window.confirmDelete = function (id) {
        const delForm = document.getElementById('deleteForm');
        if (delForm) delForm.action = '/transacciones/eliminar/' + id + '/';
        CFModal.open('deleteModal');
    };

    window.toggleCustomDates = function (value) {
        const customDiv = document.getElementById('custom_date_inputs');
        if (customDiv) customDiv.style.display = (value === 'custom') ? 'block' : 'none';
    };
}
