function initDetalleProyecto(config) {
    document.addEventListener('DOMContentLoaded', function () {
        const bcvRate = config.bcvRate;
        const orgsData = config.orgsData;
        let currentInputCurrency = 'USD';

        const transactionForm = document.getElementById('transactionForm');
        const orgSelect = transactionForm.querySelector('[name="organization"]');
        const accountSelect = transactionForm.querySelector('[name="account"]');
        const categorySelect = transactionForm.querySelector('[name="category"]');
        const tAmountUsd = transactionForm.querySelector('[name="amount_usd"]');
        const tAmountBs = transactionForm.querySelector('[name="amount_bs"]');
        const tRate = transactionForm.querySelector('[name="daily_rate"]');
        const tDate = transactionForm.querySelector('[name="date"]');
        const tAmountDisplay = document.getElementById('id_t_amount_display');
        const tCurrencyToggleBtn = document.getElementById('t_currencyToggleBtn');
        const tNextCurrencyLabel = document.getElementById('t_nextCurrencyLabel');
        const tCurrencyAddon = document.getElementById('t_currencyAddon');
        const tManualRateSwitch = document.getElementById('t_manualRateSwitch');
        let tCurrentInputCurrency = 'USD';

        function updateOrgFields(orgId, selectedAccountId, selectedCategoryId) {
            const data = orgsData[orgId];
            if (!data) return;
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

        orgSelect.addEventListener('change', function () { updateOrgFields(this.value); });

        window.toggleCustomDates = function (value) {
            document.getElementById('custom_date_inputs').style.display = (value === 'custom') ? 'block' : 'none';
        };

        function updateTCurrencyUI() {
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
            let val = Math.abs(parseFloat(tAmountDisplay.value)) || 0;
            const rate = parseFloat(tRate.value) || 1;
            const isEgreso = document.getElementById('type_egreso').checked;
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
            if (!dateValue || tManualRateSwitch.checked) return;
            fetch(config.bcvRatesUrl + '?date=' + dateValue + '&currency=USD')
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (payload) {
                    if (!payload || !payload.ok || typeof payload.rate !== 'number') return;
                    tRate.value = payload.rate.toFixed(4);
                    syncTFields();
                })
                .catch(function () {});
        }

        function updateTTypeColors() {
            const isEgreso = document.getElementById('type_egreso').checked;
            tAmountDisplay.classList.toggle('cf-text-danger', isEgreso);
            tAmountDisplay.classList.toggle('cf-text-success', !isEgreso);
        }

        window.resetTransactionForm = function () {
            transactionForm.reset();
            transactionForm.action = config.crearTransUrl;
            document.getElementById('transactionModalTitle').innerText = 'Nueva Transacción';
            orgSelect.value = config.orgId;
            updateOrgFields(orgSelect.value);
            transactionForm.querySelector('[name="date"]').value = new Date().toISOString().split('T')[0];
            tRate.value = bcvRate;
            tRate.disabled = true;
            tManualRateSwitch.checked = false;
            loadTRateForDate(transactionForm.querySelector('[name="date"]').value);
            document.getElementById('type_egreso').checked = true;
            tCurrentInputCurrency = 'USD';
            tAmountDisplay.value = '';
            updateTCurrencyUI();
        };

        window.editTransaction = function (id, orgId, accId, catId, date, desc, bs, usd, rate, ref, notes, status, valId) {
            transactionForm.action = '/transacciones/guardar/' + id + '/';
            document.getElementById('transactionModalTitle').innerText = 'Editar Transacción';
            transactionForm.querySelector('[name="date"]').value = date;
            orgSelect.value = orgId;
            updateOrgFields(orgId, accId, catId);
            transactionForm.querySelector('[name="description"]').value = desc;
            transactionForm.querySelector('[name="reference_number"]').value = ref;
            transactionForm.querySelector('[name="notes"]').value = notes;
            transactionForm.querySelector('[name="status"]').value = status;
            transactionForm.querySelector('[name="valuation"]').value = valId;
            tAmountBs.value = bs.replace(',', '.');
            tAmountUsd.value = usd.replace(',', '.');
            tRate.value = rate.replace(',', '.');
            tRate.disabled = false;
            tManualRateSwitch.checked = true;
            const valNum = parseFloat(usd.replace(',', '.'));
            document.getElementById('type_egreso').checked = valNum < 0;
            document.getElementById('type_ingreso').checked = valNum >= 0;
            tCurrentInputCurrency = (valNum !== 0 && !isNaN(valNum)) ? 'USD' : 'BS';
            tAmountDisplay.value = Math.abs(valNum || parseFloat(bs.replace(',', '.')) || 0);
            updateTCurrencyUI();
            CFModal.open('transactionModal');
        };

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

        tAmountDisplay.addEventListener('input', syncTFields);
        tRate.addEventListener('input', syncTFields);
        document.querySelectorAll('input[name="transaction_type"]').forEach(function (r) {
            r.addEventListener('change', syncTFields);
        });
        tManualRateSwitch.addEventListener('change', function (e) {
            tRate.disabled = !e.target.checked;
            if (!e.target.checked) loadTRateForDate(tDate.value);
        });
        tDate.addEventListener('change', function () { loadTRateForDate(this.value); });
        transactionForm.addEventListener('submit', function () { tRate.disabled = false; });

        window.confirmDeleteTransaction = function (id) {
            document.getElementById('deleteForm').action = '/transacciones/eliminar/' + id + '/?next=' + encodeURIComponent(config.currentPath);
            CFModal.open('deleteModal');
        };

        window.viewTransaction = function (id) {
            CFModal.open('detailModal');
            fetch('/transacciones/detalle/' + id + '/')
                .then(function (r) { return r.text(); })
                .then(function (html) { document.getElementById('detailContent').innerHTML = html; });
        };

        const valForm = document.getElementById('valuationForm');
        const vCurrencyToggleBtn = document.getElementById('currencyToggleBtn');
        const vNextCurrencyLabel = document.getElementById('nextCurrencyLabel');
        const vCurrencyAddon = document.getElementById('currencyAddon');
        const vAmountDisplay = document.getElementById('id_amount_display');
        const vAmountUsdField = valForm.querySelector('input[name="amount_usd"]');
        const vAmountBsField = valForm.querySelector('input[name="amount_bs"]');
        const vDailyRateField = valForm.querySelector('input[name="daily_rate"]');
        const vManualRateSwitch = document.getElementById('manualRateSwitch');

        window.toggleValuations = function () {
            const btn = document.getElementById('toggleValuationsBtn');
            const addBtn = document.getElementById('addValuationBtn');
            const container = document.getElementById('valuationsContainer');
            const summaryCol = document.getElementById('projectSummaryCol');
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
            valForm.reset();
            valForm.action = config.crearValUrl;
            document.getElementById('valModalTitle').innerText = 'Nueva Valuación';
            vManualRateSwitch.checked = false;
            vDailyRateField.value = bcvRate;
            vDailyRateField.disabled = true;
            currentInputCurrency = 'USD';
            vAmountDisplay.value = '';
            updateVCurrencyUI();
        };

        window.editValuation = function (id, name, usd, bs, rate) {
            valForm.action = '/valuaciones/guardar/' + config.projectId + '/' + id + '/';
            document.getElementById('valModalTitle').innerText = 'Editar Valuación';
            valForm.querySelector('[name="name"]').value = name;
            vAmountUsdField.value = usd.replace(',', '.');
            vAmountBsField.value = bs.replace(',', '.');
            vDailyRateField.value = rate.replace(',', '.');
            currentInputCurrency = 'USD';
            vAmountDisplay.value = usd.replace(',', '.');
            vManualRateSwitch.checked = true;
            vDailyRateField.disabled = false;
            updateVCurrencyUI();
            CFModal.open('valuationModal');
        };

        window.confirmDeleteValuation = function (id) {
            document.getElementById('deleteValForm').action = '/valuaciones/eliminar/' + id + '/';
            CFModal.open('deleteValModal');
        };

        function updateVCurrencyUI() {
            if (currentInputCurrency === 'USD') {
                vCurrencyAddon.innerText = '$';
                vNextCurrencyLabel.innerText = 'BS';
            } else {
                vCurrencyAddon.innerText = 'Bs';
                vNextCurrencyLabel.innerText = 'USD';
            }
            syncVHiddenFields();
        }

        function syncVHiddenFields() {
            const val = parseFloat(vAmountDisplay.value) || 0;
            const rate = parseFloat(vDailyRateField.value) || 1;
            if (currentInputCurrency === 'USD') {
                vAmountUsdField.value = val.toFixed(2);
                vAmountBsField.value = (val * rate).toFixed(2);
            } else {
                vAmountBsField.value = val.toFixed(2);
                vAmountUsdField.value = (rate !== 0) ? (val / rate).toFixed(2) : 0;
            }
        }

        vCurrencyToggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            const currentVal = parseFloat(vAmountDisplay.value) || 0;
            const rate = parseFloat(vDailyRateField.value) || 1;
            if (currentInputCurrency === 'USD') {
                vAmountDisplay.value = (currentVal * rate).toFixed(2);
                currentInputCurrency = 'BS';
            } else {
                vAmountDisplay.value = (rate !== 0) ? (currentVal / rate).toFixed(2) : 0;
                currentInputCurrency = 'USD';
            }
            updateVCurrencyUI();
        });

        vAmountDisplay.addEventListener('input', syncVHiddenFields);
        vDailyRateField.addEventListener('input', syncVHiddenFields);
        vManualRateSwitch.addEventListener('change', function (e) {
            vDailyRateField.disabled = !e.target.checked;
            if (!e.target.checked) {
                vDailyRateField.value = bcvRate;
                syncVHiddenFields();
            }
        });
        valForm.addEventListener('submit', function () { vDailyRateField.disabled = false; });
    });
}
