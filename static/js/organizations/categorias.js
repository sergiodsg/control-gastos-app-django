function initCategorias(config) {
    window.resetForm = function () {
        document.getElementById('categoryForm').reset();
        document.getElementById('categoryForm').action = config.crearUrl;
        document.getElementById('modalTitle').innerText = 'Nueva Categoría';
    };

    window.editCategory = function (id, name, desc, color) {
        const form = document.getElementById('categoryForm');
        form.action = '/categorias/guardar/' + id + '/';
        document.getElementById('modalTitle').innerText = 'Editar Categoría';
        form.querySelector('[name="name"]').value = name;
        form.querySelector('[name="description"]').value = desc;
        form.querySelector('[name="color"]').value = color;
        CFModal.open('categoryModal');
    };

    window.confirmDelete = function (id) {
        document.getElementById('deleteForm').action = '/categorias/eliminar/' + id + '/';
        CFModal.open('deleteModal');
    };
}
