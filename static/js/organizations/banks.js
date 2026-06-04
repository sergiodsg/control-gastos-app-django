window.CFBanks = (function () {
    var cache = { bs: null, usd: null };

    function fetchJson(url) {
        return fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (response) { return response.json(); });
    }

    function loadBs(url) {
        if (cache.bs) return Promise.resolve(cache.bs);
        return fetchJson(url).then(function (data) {
            cache.bs = data;
            return cache.bs;
        });
    }

    function loadUsd(url) {
        if (cache.usd) return Promise.resolve(cache.usd);
        return fetchJson(url).then(function (data) {
            cache.usd = data.bancos || data;
            return cache.usd;
        });
    }

    function populateBsSelect(selectEl, selectedCode) {
        if (!selectEl) return Promise.resolve();
        return loadBs(selectEl.dataset.banksUrl).then(function (banks) {
            selectEl.innerHTML = '<option value="">Seleccione un banco</option>';
            banks.forEach(function (bank) {
                var option = document.createElement('option');
                option.value = bank.codigo;
                option.textContent = bank.codigo + ' — ' + bank.nombre;
                option.dataset.bankName = bank.nombre;
                option.dataset.bankRif = bank.rif || '';
                if (selectedCode && bank.codigo === selectedCode) option.selected = true;
                selectEl.appendChild(option);
            });
        });
    }

    function populateUsdSelect(selectEl, selectedName) {
        if (!selectEl) return Promise.resolve();
        return loadUsd(selectEl.dataset.banksUrl).then(function (banks) {
            selectEl.innerHTML = '<option value="">Seleccione un banco</option>';
            banks.forEach(function (bank) {
                var option = document.createElement('option');
                option.value = bank.nombre;
                option.textContent = bank.nombre;
                if (selectedName && bank.nombre === selectedName) option.selected = true;
                selectEl.appendChild(option);
            });
        });
    }

    function bindBsSelect(selectEl, bankNameInput, rifInput) {
        if (!selectEl) return;
        selectEl.addEventListener('change', function () {
            var option = selectEl.options[selectEl.selectedIndex];
            if (bankNameInput) bankNameInput.value = option.dataset.bankName || '';
            if (rifInput && option.dataset.bankRif && !rifInput.dataset.userEdited) {
                rifInput.value = option.dataset.bankRif;
            }
        });
    }

    function bindUsdSelect(selectEl, bankNameInput) {
        if (!selectEl) return;
        selectEl.addEventListener('change', function () {
            if (bankNameInput) bankNameInput.value = selectEl.value;
        });
    }

    return {
        loadBs: loadBs,
        loadUsd: loadUsd,
        populateBsSelect: populateBsSelect,
        populateUsdSelect: populateUsdSelect,
        bindBsSelect: bindBsSelect,
        bindUsdSelect: bindUsdSelect,
    };
})();
