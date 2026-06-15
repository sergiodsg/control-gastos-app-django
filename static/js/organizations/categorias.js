function initCategorias(config) {
    window.resetForm = function () {
        if (window.userIsViewer) return;
        document.getElementById('categoryForm').reset();
        document.getElementById('categoryForm').action = config.crearUrl;
        document.getElementById('modalTitle').innerText = 'Nueva Categoría';
    };

    window.editCategory = function (id, name, desc, color) {
        if (window.userIsViewer) return;
        const form = document.getElementById('categoryForm');
        form.action = '/categorias/guardar/' + id + '/';
        document.getElementById('modalTitle').innerText = 'Editar Categoría';
        form.querySelector('[name="name"]').value = name;
        form.querySelector('[name="description"]').value = desc;
        form.querySelector('[name="color"]').value = color;
        CFModal.open('categoryModal');
    };

    window.confirmDelete = function (id) {
        if (window.userIsViewer) return;
        document.getElementById('deleteForm').action = '/categorias/eliminar/' + id + '/';
        CFModal.open('deleteModal');
    };
}
