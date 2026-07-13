# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Django app (Spanish UI/domain names) for multi-organization expense/cash-flow tracking ("Control de Gastos"). Users belong to organizations, organizations have accounts/projects/categories/cost centers, and transactions record dual-currency (Bs./USD) movements against a daily BCV exchange rate.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run dev server (SQLite by default in development, no MySQL needed)
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Tests (pytest-django; conftest.py forces an in-memory SQLite DB for tests)
pytest
pytest organizations/tests.py
pytest organizations/tests.py::SomeTestClass::test_something
python manage.py test              # equivalent Django-native runner

# Create a superuser (custom helper script, not just createsuperuser)
python create_superuser.py

# Regenerate DBML schema (used for the dbdiagram.io ER diagram linked in README.md)
python generate_dbml.py

# Sync BCV exchange rates manually (see logs/CRON.md for cron/production usage)
python manage.py bcv                    # fetch immediately, no time window
python manage.py bcv --strict-window    # only runs within --window-hours (default 09,15)
```

There is no configured linter/formatter in this repo — don't assume black/flake8/ruff are wired up.

## Architecture

### Apps

- **`accounts/`** — Django `User` + `Profile` (role: `Editor`/`Viewer`, auto-created via `post_save` signal). `viewer_restricted` decorator blocks write actions for Viewer-role users. `context_processors.user_permissions` injects `user_is_viewer`/`user_is_editor`/`user_role` into every template context; superusers are always treated as editors.
- **`organizations/`** — the core domain app: `Organization`, `OrganizationAccess` (user↔org M2M via through table), `Account`, `Category`, `Project`, `Valuation`, `CostCenter`, `Transaction`. Almost all business logic and views live in `organizations/views.py` (~1900 lines) and `organizations/forms.py`.
- **`BCV/`** — fetches/caches official Venezuelan exchange rates (USD/EUR) from bcv.org.ve, stored in `ExchangeRateHistory`. `BCV/services/bcv_scrapper.py` does the scraping/caching (`get_bcv_rates_cached`); `BCV/management/commands/bcv.py` is the cron entry point (`manage.py bcv`), scheduled at 09:00/15:00 in production (see `logs/CRON.md`).
- **`superadmin_panel/`** — separate admin-only area, gated by `superadmin_required` decorator and `SuperuserPanelMiddleware`, which force-redirects any authenticated superuser away from the normal org-scoped app to `/superadmin/` (superusers never use the regular organization flow).
- **`CashFlow/`** — Django project config: `settings.py`, `db.py` (DB selection), `urls.py`, `debug.py` (structured event logging helper).

### Organization scoping via session

There's no per-request org in the URL. After login, a user picks an organization (`seleccionar_organizacion`), which stores `org_id`/`org_name` in `request.session`. Nearly every view in `organizations/views.py` does:

```python
org_id = request.session.get('org_id')
if not org_id:
    return redirect('home_organizacion')  # or similar
org = get_object_or_404(Organization, id=org_id)
```

When adding a new org-scoped view, follow this same pattern and use `@login_required` (+ `@viewer_restricted` for mutating actions). `salir_organizacion` clears the session keys.

### Dual currency model

Transactions (and account opening balances) store both `amount_bs` and `amount_usd` plus the `daily_rate` used. `organizations/amounts.py::apply_dual_currency_amounts` derives whichever amount is missing from the other, given the rate — this logic is duplicated/mirrored in `TransactionForm.clean()`, so keep both in sync if you change the conversion rule. There's also a "real dollars" side (`real_dollars`, `bank_fee_real_usd`) used for a separate reporting mode (`mode='real'` vs default `mode='bcv'` throughout chart/report code).

### Structured logging (`CashFlow/debug.py`)

Use `debug_event(event, **context)` instead of ad-hoc logging for anything domain-relevant. It:
- Redacts keys containing `password`/`csrf`/`token`/`secret`.
- Routes to a named logger based on the event prefix: `transaccion.*` → `cashflow.transactions`, `cuenta.*` → `cashflow.accounts`, everything else → `cashflow.debug`.
- Escalates to `cashflow.errors` for `WARNING`+ (event names containing `.error` are ERROR; `acceso_denegado` events are WARNING).
- Also prints to console when `DEBUG=True`.

Log files live in `logs/` (rotating handlers configured in `CashFlow/settings.py`): `app.log`, `server_errors.log`, `transactions.log`, `application_errors.log`, `cron_bcv.log`.

### Environment / settings split

`CashFlow/settings.py` reads `DJANGO_ENV` (`development` default, or `production`). In development it defaults to SQLite (`DJANGO_USE_SQLITE=1`, file `test_db.sqlite3` unless overridden); in production it uses MySQL via `CashFlow/db.py`, configured with `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` env vars. `SECRET_KEY`, `ALLOWED_HOSTS`, `DEBUG` are all env-driven for production.

**`CashFlow/settings.py` and `CashFlow/db.py` are `merge=ours` in `.gitattributes`** — when merging `main`↔`dev`, these two files intentionally keep the destination branch's version (dev config stays in `dev`, prod config stays in `main`). Be careful about editing them across branches; check `.gitattributes`/`inicio.txt` before assuming a merge will pick up your changes to these files.

### Deployment

Production is a Namecheap/cPanel host running LiteSpeed + Passenger (see `passenger_wsgi.py`, `.cpanel.yml`, `build.sh`). GitHub Actions (`.github/workflows/deploy.yml`) deploys on push to `main` via SSH: `git pull`, `pip install -r requirements.txt`, `migrate`, `collectstatic`, then touches `tmp/restart.txt` to restart Passenger. `manage.py` lives at the repo root, not inside `CashFlow/` — remember this when writing deployment/cron commands.
