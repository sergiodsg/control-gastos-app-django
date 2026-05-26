import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CDG.settings')
django.setup()

from django.apps import apps

def generate_dbml():
    output = ["// Copia y pega este contenido en dbdiagram.io\n"]
    
    # Modelos a incluir (puedes añadir más si es necesario)
    models_to_include = [
        'auth.User',
        'organizations.Organization',
        'organizations.OrganizationAccess',
        'organizations.Account',
        'organizations.Category',
        'organizations.Project',
        'organizations.Valuation',
        'organizations.Transaction',
    ]
    
    relations = []

    for model_name in models_to_include:
        app_label, model_name = model_name.split('.')
        model = apps.get_model(app_label, model_name)
        table_name = model._meta.db_table
        
        output.append(f"Table {table_name} {{")
        
        for field in model._meta.get_fields():
            if not field.is_relation or field.many_to_one:
                # Nombre del campo
                f_name = field.name
                if field.many_to_one:
                    f_name = f"{field.name}_id"
                
                # Tipo de dato simplificado
                f_type = field.get_internal_type().lower().replace('field', '')
                if 'integer' in f_type: f_type = 'integer'
                if 'char' in f_type: f_type = 'varchar'
                if 'text' in f_type: f_type = 'text'
                if 'decimal' in f_type: f_type = 'decimal'
                
                # Atributos
                attrs = []
                if field.primary_key: attrs.append("primary key")
                if getattr(field, 'null', False): attrs.append("null")
                
                attr_str = f" [{', '.join(attrs)}]" if attrs else ""
                output.append(f"  {f_name} {f_type}{attr_str}")
                
                # Relaciones
                if field.many_to_one:
                    target_table = field.related_model._meta.db_table
                    relations.append(f"Ref: {table_name}.{f_name} > {target_table}.id")
        
        output.append("}\n")
    
    output.extend(relations)
    return "\n".join(output)

if __name__ == "__main__":
    print(generate_dbml())
