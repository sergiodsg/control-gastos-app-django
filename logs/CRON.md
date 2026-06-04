# Cron — sincronización tasas BCV

## Rutas en producción (Namecheap)

| Concepto | Ruta |
|----------|------|
| Proyecto | `/home/ssapmcco/cashflow.cpaldaca.com` |
| Python | `/home/ssapmcco/virtualenv/cashflow.cpaldaca.com/3.12/bin/python` |
| manage.py | `/home/ssapmcco/cashflow.cpaldaca.com/manage.py` |
| Log cron | `/home/ssapmcco/cashflow.cpaldaca.com/logs/cron_bcv.log` |

> **Nota:** `manage.py` está en la raíz del proyecto, no dentro de `CashFlow/`.

## Opción A — Comando directo en cPanel (recomendado)

Ejecutar a las **09:00** y **15:00** (hora del servidor, idealmente `America/Caracas`):

```bash
cd /home/ssapmcco/cashflow.cpaldaca.com && /home/ssapmcco/virtualenv/cashflow.cpaldaca.com/3.12/bin/python manage.py bcv --strict-window >> /home/ssapmcco/cashflow.cpaldaca.com/logs/cron_bcv.log 2>&1
```

### Expresión cron en cPanel

```
0 9,15 * * *
```

## Opción B — Script con marcas de inicio/fin

1. Dar permisos: `chmod +x scripts/run_cron_bcv.sh`
2. En crontab:

```bash
0 9,15 * * * /home/ssapmcco/cashflow.cpaldaca.com/scripts/run_cron_bcv.sh
```

## Logs

- **`logs/cron_bcv.log`**: salida del cron (`stdout`/`stderr` de `manage.py bcv`), igual que `cron_lunes.log` en HojadeTiempo.
- **`logs/cron_bcv.log` (logger Django)**: líneas estructuradas del logger `cashflow.cron.bcv` (inicio, éxito, errores).

Revisar últimas ejecuciones:

```bash
tail -n 80 /home/ssapmcco/cashflow.cpaldaca.com/logs/cron_bcv.log
```

## Variables de entorno

El cron debe usar la misma BD y `SECRET_KEY` que la web. En cPanel suele bastar con cargar el entorno del virtualenv; si falla, exporta antes del comando:

```bash
export DJANGO_ENV=production
export DEBUG=0
```

## Prueba manual (SSH)

```bash
cd /home/ssapmcco/cashflow.cpaldaca.com
source ~/virtualenv/cashflow.cpaldaca.com/3.12/bin/activate
export DJANGO_ENV=production
python manage.py bcv --strict-window
```

Sin ventana horaria (prueba inmediata):

```bash
python manage.py bcv
```
