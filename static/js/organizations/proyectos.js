function initProyectos(config) {
    function resetForm() {
        document.getElementById('projectForm').reset();
        document.getElementById('projectForm').action = config.crearUrl;
        document.getElementById('modalTitle').innerText = 'Nuevo Proyecto';
    }

    window.resetForm = resetForm;

    window.editProject = function (id, name, description) {
        const form = document.getElementById('projectForm');
        form.action = '/proyectos/guardar/' + id + '/';
        document.getElementById('modalTitle').innerText = 'Editar Proyecto';
        form.querySelector('[name="name"]').value = name;
        form.querySelector('[name="description"]').value = description;
        CFModal.open('projectModal');
    };

    window.confirmDelete = function (id) {
        document.getElementById('deleteForm').action = '/proyectos/eliminar/' + id + '/';
        CFModal.open('deleteModal');
    };
}
