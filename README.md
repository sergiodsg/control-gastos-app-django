# Control de Gastos - Django

Este proyecto es una aplicación de Django para el control de gastos de organizaciones.

## Diagrama de Entidad-Relación (ERD)

Puedes visualizar el esquema de la base de datos en dbdiagram.io siguiendo este enlace:

[Ver Diagrama ER en dbdiagram.io](https://dbdiagram.io/d/Diagrama-de-entidad-relacion-6a1386b8dfb20dafcde08850)

---

## Estructura del Proyecto

- `core/`: Autenticación y registro de usuarios.
- `organizations/`: Modelos principales de organizaciones, cuentas, proyectos, valuaciones y transacciones.
- `CDG/`: Configuración del proyecto Django.
- `templates/`: Plantillas HTML.

## Variables de entorno

Copia `key.env.example` a `key.env` y define al menos `DJANGO_SECRET_KEY`. Django carga `key.env` al arrancar (`manage.py`, WSGI, pruebas).

| Variable | Descripción |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Obligatoria. Clave secreta de Django (variable de entorno leída por `settings`). |
| `DEBUG` | `True` en desarrollo, `False` en producción. |
| `ALLOWED_HOSTS` | Hosts separados por coma. |
| `DATABASE_URL` | Opcional. Por defecto usa SQLite (`db.sqlite3`). |
| `BCV_SSL_VERIFY` | Opcional. Por defecto `true` (usa certificados de `certifi`). Si `fetch_bcv_rates` falla con error SSL en tu PC, en desarrollo puedes usar `false` (menos seguro). |

Sincronizar tasas del BCV (guarda USD/EUR del día en `ExchangeRateHistory`):

```bash
python manage.py fetch_bcv_rates
```

## Arranque local

Tras `migrate`, crea la tabla de caché en base de datos (evita `no such table: django_cache_table`):

```bash
python manage.py createcachetable
```

## Pruebas

```bash
pip install -r requirements.txt
pytest
```
