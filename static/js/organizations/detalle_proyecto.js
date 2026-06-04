function initDetalleProyecto(config) {
    const bcvRate = config.bcvRate;
    const orgsData = config.orgsData;
    let tCurrentInputCurrency = 'USD';

    // Funciones globales de transacción
    window.resetTransactionForm = function () {
        const form = document.getElementById('transactionForm');
        if (!form) return;
        form.reset();
        form.action = config.crearTransUrl;
        document.getElementById('transactionModalTitle').innerText = 'Nueva Transacción';
        
        const orgSelect = form.querySelector('[name="organization"]');
        if (orgSelect) {
            orgSelect.value = config.orgId;
            updateOrgFields(orgSelect.value);
        }
        
        const dateField = form.querySelector('[name="date"]');
        if (dateField) dateField.value = new Date().toISOString().split('T')[0];
        
        const tRate = form.querySelector('[name="daily_rate"]');
        if (tRate) {
            tRate.value = bcvRate;
            tRate.disabled = true;
        }
        
        const tManualRateSwitch = document.getElementById('t_manualRateSwitch');
        if (tManualRateSwitch) tManualRateSwitch.checked = false;
        
        if (dateField) loadTRateForDate(dateField.value);
        
        const egresoRadio = document.getElementById('type_egreso');
        if (egresoRadio) egresoRadio.checked = true;
        
        tCurrentInputCurrency = 'USD';
        const tAmountDisplay = document.getElementById('id_t_amount_display');
        if (tAmountDisplay) tAmountDisplay.value = '';
        updateTCurrencyUI();
    };

    window.editTransaction = function (id, orgId, accId, catId, date, desc, bs, usd, rate, ref, notes, status, valId) {
        const form = document.getElementById('transactionForm');
        if (!form) return;
        form.action = '/transacciones/guardar/' + id + '/';
        document.getElementById('transactionModalTitle').innerText = 'Editar Transacción';
        
        const dateField = form.querySelector('[name="date"]');
        if (dateField) dateField.value = date;
        
        const orgSelect = form.querySelector('[name="organization"]');
        if (orgSelect) {
            orgSelect.value = orgId;
            updateOrgFields(orgId, accId, catId);
        }
        
        form.querySelector('[name="description"]').value = desc;
        form.querySelector('[name="reference_number"]').value = ref;
        form.querySelector('[name="notes"]').value = notes;
        form.querySelector('[name="status"]').value = status;
        
        const vSelect = form.querySelector('[name="valuation"]');
        if (vSelect) vSelect.value = valId;
        
        const tAmountBs = form.querySelector('[name="amount_bs"]');
        const tAmountUsd = form.querySelector('[name="amount_usd"]');
        const tRate = form.querySelector('[name="daily_rate"]');
        
        if (tAmountBs) tAmountBs.value = bs.toString().replace(',', '.');
        if (tAmountUsd) tAmountUsd.value = usd.toString().replace(',', '.');
        if (tRate) {
            tRate.value = rate.toString().replace(',', '.');
            tRate.disabled = false;
        }
        
        const tManualRateSwitch = document.getElementById('t_manualRateSwitch');
        if (tManualRateSwitch) tManualRateSwitch.checked = true;
        
        const valNum = parseFloat(usd.toString().replace(',', '.'));
        const egresoRadio = document.getElementById('type_egreso');
        const ingresoRadio = document.getElementById('type_ingreso');
        if (egresoRadio) egresoRadio.checked = valNum < 0;
        if (ingresoRadio) ingresoRadio.checked = valNum >= 0;
        
        tCurrentInputCurrency = (valNum !== 0 && !isNaN(valNum)) ? 'USD' : 'BS';
        const tAmountDisplay = document.getElementById('id_t_amount_display');
        if (tAmountDisplay) tAmountDisplay.value = Math.abs(valNum || parseFloat(bs.toString().replace(',', '.')) || 0);
        
        updateTCurrencyUI();
        CFModal.open('transactionModal');
    };

    window.duplicateTransaction = function (orgId, accId, catId, date, desc, bs, usd, rate, ref, notes, status, valId) {
        window.resetTransactionForm();
        const form = document.getElementById('transactionForm');
        if (!form) return;
        form.action = config.crearTransUrl;
        document.getElementById('transactionModalTitle').innerText = 'Duplicar Transacción (Nueva)';
        
        const dateField = form.querySelector('[name="date"]');
        if (dateField) dateField.value = date;
        
        const orgSelect = form.querySelector('[name="organization"]');
        if (orgSelect) {
            orgSelect.value = orgId;
            updateOrgFields(orgId, accId, catId);
        }
        
        form.querySelector('[name="description"]').value = desc;
        form.querySelector('[name="reference_number"]').value = ref;
        form.querySelector('[name="notes"]').value = notes;
        form.querySelector('[name="status"]').value = status;
        
        const vSelect = form.querySelector('[name="valuation"]');
        if (vSelect) vSelect.value = valId;
        
        const tAmountBs = form.querySelector('[name="amount_bs"]');
        const tAmountUsd = form.querySelector('[name="amount_usd"]');
        const tRate = form.querySelector('[name="daily_rate"]');
        
        if (tAmountBs) tAmountBs.value = bs.toString().replace(',', '.');
        if (tAmountUsd) tAmountUsd.value = usd.toString().replace(',', '.');
        if (tRate) {
            tRate.value = rate.toString().replace(',', '.');
            tRate.disabled = false;
        }
        
        const tManualRateSwitch = document.getElementById('t_manualRateSwitch');
        if (tManualRateSwitch) tManualRateSwitch.checked = true;
        
        const valNum = parseFloat(usd.toString().replace(',', '.'));
        const egresoRadio = document.getElementById('type_egreso');
        const ingresoRadio = document.getElementById('type_ingreso');
        if (egresoRadio) egresoRadio.checked = valNum < 0;
        if (ingresoRadio) ingresoRadio.checked = valNum >= 0;
        
        tCurrentInputCurrency = (valNum !== 0 && !isNaN(valNum)) ? 'USD' : 'BS';
        const tAmountDisplay = document.getElementById('id_t_amount_display');
        if (tAmountDisplay) tAmountDisplay.value = Math.abs(valNum || parseFloat(bs.toString().replace(',', '.')) || 0);
        
        updateTCurrencyUI();
        CFModal.open('transactionModal');
    };

    // Auxiliares internos
    function updateOrgFields(orgId, selectedAccountId, selectedCategoryId) {
        const data = orgsData[orgId];
        const accountSelect = document.querySelector('select[name="account"]');
        const categorySelect = document.querySelector('select[name="category"]');
        if (!data || !accountSelect || !categorySelect) return;
        
        accountSelect.innerHTML = '<option value="">---------</option>';
        data.accounts.forEach(function (acc) {
            const opt = new Option(acc.name, acc.id);
            if (selectedAccountId && acc.id == selectedAccountId) opt.selected = true;
            accountSelect.add(opt);
        });
        categorySelect.innerHTML = '<option value="">---------</option>';
        data.categories.forEach(function (cat) {
            const opt = new Option(cat.name, cat.id);
            if (selectedCategoryId && cat.id == selectedCategoryId) opt.selected = true;
            categorySelect.add(opt);
        });
    }

    function updateTCurrencyUI() {
        const tCurrencyAddon = document.getElementById('t_currencyAddon');
        const tNextCurrencyLabel = document.getElementById('t_nextCurrencyLabel');
        if (!tCurrencyAddon || !tNextCurrencyLabel) return;
        if (tCurrentInputCurrency === 'USD') {
            tCurrencyAddon.innerText = '$';
            tNextCurrencyLabel.innerText = 'BS';
        } else {
            tCurrencyAddon.innerText = 'Bs';
            tNextCurrencyLabel.innerText = 'USD';
        }
        syncTFields();
    }

    function syncTFields() {
        const tAmountDisplay = document.getElementById('id_t_amount_display');
        const tAmountUsd = document.querySelector('input[name="amount_usd"]');
        const tAmountBs = document.querySelector('input[name="amount_bs"]');
        const tRate = document.querySelector('input[name="daily_rate"]');
        if (!tAmountDisplay || !tAmountUsd || !tAmountBs || !tRate) return;
        
        let val = Math.abs(parseFloat(tAmountDisplay.value)) || 0;
        const rate = parseFloat(tRate.value) || 1;
        const egresoRadio = document.getElementById('type_egreso');
        const isEgreso = egresoRadio ? egresoRadio.checked : true;
        
        if (isEgreso && val > 0) val = -val;
        if (tCurrentInputCurrency === 'USD') {
            tAmountUsd.value = val.toFixed(2);
            tAmountBs.value = (val * rate).toFixed(2);
        } else {
            tAmountBs.value = val.toFixed(2);
            tAmountUsd.value = (rate !== 0) ? (val / rate).toFixed(2) : 0;
        }
        updateTTypeColors();
    }

    function loadTRateForDate(dateValue) {
        const tManualRateSwitch = document.getElementById('t_manualRateSwitch');
        const tRate = document.querySelector('input[name="daily_rate"]');
        if (!dateValue || !tManualRateSwitch || tManualRateSwitch.checked) return;
        fetch(config.bcvRatesUrl + '?date=' + dateValue + '&currency=USD')
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (payload) {
                if (!payload || !payload.ok || typeof payload.rate !== 'number') return;
                if (tRate) {
                    tRate.value = payload.rate.toFixed(4);
                    syncTFields();
                }
            })
            .catch(function () {});
    }

    function updateTTypeColors() {
        const tAmountDisplay = document.getElementById('id_t_amount_display');
        const egresoRadio = document.getElementById('type_egreso');
        if (!tAmountDisplay || !egresoRadio) return;
        const isEgreso = egresoRadio.checked;
        tAmountDisplay.classList.toggle('cf-text-danger', isEgreso);
        tAmountDisplay.classList.toggle('cf-text-success', !isEgreso);
    }

    function setupTListeners() {
        const orgSelect = document.querySelector('select[name="organization"]');
        const tAmountDisplay = document.getElementById('id_t_amount_display');
        const tRate = document.querySelector('input[name="daily_rate"]');
        const tDate = document.querySelector('input[name="date"]');
        const tCurrencyToggleBtn = document.getElementById('t_currencyToggleBtn');
        const tManualRateSwitch = document.getElementById('t_manualRateSwitch');
        const transactionForm = document.getElementById('transactionForm');

        if (orgSelect) orgSelect.addEventListener('change', function () { updateOrgFields(this.value); });
        
        if (tCurrencyToggleBtn) {
            tCurrencyToggleBtn.addEventListener('click', function (e) {
                e.preventDefault();
                const currentVal = parseFloat(tAmountDisplay.value) || 0;
                const rate = parseFloat(tRate.value) || 1;
                if (tCurrentInputCurrency === 'USD') {
                    tAmountDisplay.value = (currentVal * rate).toFixed(2);
                    tCurrentInputCurrency = 'BS';
                } else {
                    tAmountDisplay.value = (rate !== 0) ? (currentVal / rate).toFixed(2) : 0;
                    tCurrentInputCurrency = 'USD';
                }
                updateTCurrencyUI();
            });
        }

        if (tAmountDisplay) tAmountDisplay.addEventListener('input', syncTFields);
        if (tRate) tRate.addEventListener('input', syncTFields);
        
        document.querySelectorAll('input[name="transaction_type"]').forEach(function (r) {
            r.addEventListener('change', syncTFields);
        });

        if (tManualRateSwitch) {
            tManualRateSwitch.addEventListener('change', function (e) {
                if (tRate) tRate.disabled = !e.target.checked;
                if (!e.target.checked && tDate) loadTRateForDate(tDate.value);
            });
        }

        if (tDate) {
            tDate.addEventListener('change', function () { loadTRateForDate(this.value); });
        }

        if (transactionForm) {
            transactionForm.addEventListener('submit', function () {
                if (tRate) tRate.disabled = false;
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupTListeners);
    } else {
        setupTListeners();
    }

    window.confirmDeleteTransaction = function (id) {
        const delForm = document.getElementById('deleteForm');
        if (delForm) delForm.action = '/transacciones/eliminar/' + id + '/?next=' + encodeURIComponent(config.currentPath);
        CFModal.open('deleteModal');
    };

    window.viewTransaction = function (id) {
        const content = document.getElementById('detailContent');
        if (!content) return;
        CFModal.open('detailModal');
        fetch('/transacciones/detalle/' + id + '/')
            .then(function (r) { return r.text(); })
            .then(function (html) { content.innerHTML = html; });
    };

    // --- Lógica de Valuaciones ---
    window.toggleValuations = function () {
        const btn = document.getElementById('toggleValuationsBtn');
        const addBtn = document.getElementById('addValuationBtn');
        const container = document.getElementById('valuationsContainer');
        const summaryCol = document.getElementById('projectSummaryCol');
        if (!container || !btn || !addBtn || !summaryCol) return;
        
        if (container.classList.contains('cf-hidden')) {
            container.classList.remove('cf-hidden');
            addBtn.style.display = 'inline-flex';
            summaryCol.classList.add('project-summary-col--split');
            btn.innerHTML = '<i class="fa-solid fa-eye-slash cf-me-1"></i>Ocultar Valuaciones';
        } else {
            container.classList.add('cf-hidden');
            addBtn.style.display = 'none';
            summaryCol.classList.remove('project-summary-col--split');
            btn.innerHTML = '<i class="fa-solid fa-gear cf-me-1"></i>Gestionar Valuaciones';
        }
    };

    window.resetValuationForm = function () {
        const valForm = document.getElementById('valuationForm');
        if (!valForm) return;
        valForm.reset();
        valForm.action = config.crearValUrl;
        document.getElementById('valModalTitle').innerText = 'Nueva Valuación';
        
        const vManualRateSwitch = document.getElementById('manualRateSwitch');
        const vDailyRateField = valForm.querySelector('input[name="daily_rate"]');
        if (vManualRateSwitch) vManualRateSwitch.checked = false;
        if (vDailyRateField) {
            vDailyRateField.value = bcvRate;
            vDailyRateField.disabled = true;
        }
        
        const vAmountDisplay = document.getElementById('id_amount_display');
        if (vAmountDisplay) vAmountDisplay.value = '';
        // updateVCurrencyUI() ... se puede añadir si es necesario
    };

    window.editValuation = function (id, name, usd, bs, rate) {
        const valForm = document.getElementById('valuationForm');
        if (!valForm) return;
        valForm.action = '/valuaciones/guardar/' + config.projectId + '/' + id + '/';
        document.getElementById('valModalTitle').innerText = 'Editar Valuación';
        valForm.querySelector('[name="name"]').value = name;
        
        const vAmountUsdField = valForm.querySelector('input[name="amount_usd"]');
        const vAmountBsField = valForm.querySelector('input[name="amount_bs"]');
        const vDailyRateField = valForm.querySelector('input[name="daily_rate"]');
        
        if (vAmountUsdField) vAmountUsdField.value = usd.toString().replace(',', '.');
        if (vAmountBsField) vAmountBsField.value = bs.toString().replace(',', '.');
        if (vDailyRateField) {
            vDailyRateField.value = rate.toString().replace(',', '.');
            vDailyRateField.disabled = false;
        }
        
        const vManualRateSwitch = document.getElementById('manualRateSwitch');
        if (vManualRateSwitch) vManualRateSwitch.checked = true;
        
        const vAmountDisplay = document.getElementById('id_amount_display');
        if (vAmountDisplay) vAmountDisplay.value = usd.toString().replace(',', '.');
        
        CFModal.open('valuationModal');
    };

    window.confirmDeleteValuation = function (id) {
        const delValForm = document.getElementById('deleteValForm');
        if (delValForm) delValForm.action = '/valuaciones/eliminar/' + id + '/';
        CFModal.open('deleteValModal');
    };
    
    window.toggleCustomDates = function (value) {
        const div = document.getElementById('custom_date_inputs');
        if (div) div.style.display = (value === 'custom') ? 'block' : 'none';
    };
}
