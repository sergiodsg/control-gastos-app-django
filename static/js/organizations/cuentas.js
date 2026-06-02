function initCuentas(config) {
    let currentInputCurrency = 'USD';

    window.resetForm = function () {
        const form = document.getElementById('accountForm');
        form.reset();
        form.action = config.crearUrl;
        document.getElementById('modalTitle').innerText = 'Nueva Cuenta';
        document.getElementById('initialAmountFields').classList.remove('cf-hidden', 'd-none');

        document.getElementById('manualRateSwitch').checked = false;
        const rateField = document.querySelector('input[name="daily_rate"]');
        rateField.value = config.bcvRate;
        rateField.readOnly = true;

        currentInputCurrency = 'USD';
        document.getElementById('id_amount_display').value = '';
        updateCurrencyUI();
    };

    window.editAccount = function (id, name) {
        const form = document.getElementById('accountForm');
        form.action = '/cuentas/guardar/' + id + '/';
        document.getElementById('modalTitle').innerText = 'Editar Cuenta';
        document.getElementById('initialAmountFields').classList.add('cf-hidden', 'd-none');
        form.querySelector('[name="name"]').value = name;
        CFModal.open('accountModal');
    };

    window.confirmDelete = function (id) {
        document.getElementById('deleteForm').action = '/cuentas/eliminar/' + id + '/';
        CFModal.open('deleteModal');
    };

    const currencyToggleBtn = document.getElementById('currencyToggleBtn');
    const nextCurrencyLabel = document.getElementById('nextCurrencyLabel');
    const currencyAddon = document.getElementById('currencyAddon');
    const amountDisplay = document.getElementById('id_amount_display');
    const amountUsdField = document.querySelector('input[name="initial_amount_usd"]');
    const amountBsField = document.querySelector('input[name="initial_amount_bs"]');
    const dailyRateField = document.querySelector('input[name="daily_rate"]');
    const manualRateSwitch = document.getElementById('manualRateSwitch');

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
        const val = parseFloat(amountDisplay.value) || 0;
        const rate = parseFloat(dailyRateField.value) || 1;
        if (currentInputCurrency === 'USD') {
            amountUsdField.value = val.toFixed(2);
            amountBsField.value = (val * rate).toFixed(2);
        } else {
            amountBsField.value = val.toFixed(2);
            amountUsdField.value = (rate !== 0) ? (val / rate).toFixed(2) : 0;
        }
    }

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

    if (amountDisplay) amountDisplay.addEventListener('input', syncHiddenFields);
    if (dailyRateField) dailyRateField.addEventListener('input', syncHiddenFields);

    if (manualRateSwitch) {
        manualRateSwitch.addEventListener('change', function (e) {
            dailyRateField.readOnly = !e.target.checked;
            if (!e.target.checked) {
                dailyRateField.value = config.bcvRate;
                syncHiddenFields();
            }
        });
    }
}
