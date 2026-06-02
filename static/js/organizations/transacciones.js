function initTransacciones(config) {
    document.addEventListener('DOMContentLoaded', function () {
        const bcvRate = config.bcvRate;
        let currentInputCurrency = 'USD';

        window.resetForm = function () {
            const form = document.getElementById('transactionForm');
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
            form.querySelector('[name="amount_bs"]').value = bs;
            form.querySelector('[name="amount_usd"]').value = usd;
            form.querySelector('[name="daily_rate"]').value = rate;

            if (parseFloat(usd) < 0 || parseFloat(bs) < 0) {
                document.getElementById('type_egreso').checked = true;
            } else {
                document.getElementById('type_ingreso').checked = true;
            }

            valuationSelect.value = valuation;
            document.getElementById('manualRateSwitch').checked = true;
            document.querySelector('[name="daily_rate"]').disabled = false;

            currentInputCurrency = (parseFloat(usd) !== 0) ? 'USD' : 'BS';
            document.getElementById('id_amount_display').value = Math.abs((currentInputCurrency === 'USD') ? usd : bs);
            updateCurrencyUI();
            updateValuationVisibility();
            CFModal.open('transactionModal');
        };

        window.viewDetail = function (id) {
            const content = document.getElementById('detailContent');
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
            document.getElementById('deleteForm').action = '/transacciones/eliminar/' + id + '/';
            CFModal.open('deleteModal');
        };

        window.toggleCustomDates = function (value) {
            const customDiv = document.getElementById('custom_date_inputs');
            customDiv.style.display = (value === 'custom') ? 'block' : 'none';
        };

        const currencyToggleBtn = document.getElementById('currencyToggleBtn');
        const nextCurrencyLabel = document.getElementById('nextCurrencyLabel');
        const currencyAddon = document.getElementById('currencyAddon');
        const amountDisplay = document.getElementById('id_amount_display');
        const amountUsdField = document.querySelector('input[name="amount_usd"]');
        const amountBsField = document.querySelector('input[name="amount_bs"]');
        const dailyRateField = document.querySelector('input[name="daily_rate"]');
        const manualRateSwitch = document.getElementById('manualRateSwitch');
        const dateField = document.querySelector('input[name="date"]');
        const projectSelect = document.querySelector('select[name="project"]');
        const valuationSelect = document.querySelector('select[name="valuation"]');
        const valuationContainer = document.getElementById('valuationContainer');
        const projectsData = config.projectsData || {};

        function updateValuationVisibility() {
            const val = parseFloat(amountUsdField.value) || 0;
            const projectId = projectSelect.value;
            if (val > 0 && projectId && projectsData[projectId] && projectsData[projectId].length > 0) {
                valuationContainer.style.display = 'block';
                filterValuations(projectId);
            } else {
                valuationContainer.style.display = 'none';
                valuationSelect.value = '';
            }
        }

        function filterValuations(projectId) {
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

        if (projectSelect) projectSelect.addEventListener('change', updateValuationVisibility);

        function updateCurrencyUI() {
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

        function loadRateForDate(dateValue) {
            if (!dateValue || manualRateSwitch.checked) return;
            fetch(config.bcvRatesUrl + '?date=' + dateValue + '&currency=USD')
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (payload) {
                    if (!payload || !payload.ok || typeof payload.rate !== 'number') return;
                    dailyRateField.value = payload.rate.toFixed(4);
                    syncHiddenFields();
                })
                .catch(function () {});
        }

        function updateTypeColors() {
            const isEgreso = document.getElementById('type_egreso').checked;
            amountDisplay.classList.toggle('cf-text-danger', isEgreso);
            amountDisplay.classList.toggle('cf-text-success', !isEgreso);
            amountDisplay.classList.add('cf-fw-bold');
        }

        document.querySelectorAll('input[name="transaction_type"]').forEach(function (radio) {
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

        document.getElementById('transactionForm').addEventListener('submit', function () {
            dailyRateField.disabled = false;
        });

        const refInput = document.getElementById('id_reference_number_custom');
        if (refInput) {
            refInput.addEventListener('input', function (e) {
                document.querySelector('[name="reference_number"]').value = e.target.value;
            });
        }
    });
}
