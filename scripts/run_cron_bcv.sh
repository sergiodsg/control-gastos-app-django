#!/bin/bash
# Cron BCV — CashFlow (Namecheap / cPanel)
# Uso en crontab: ver logs/CRON.md o inicio.txt

PROJECT_DIR="/home/ssapmcco/cashflow.cpaldaca.com"
PYTHON="/home/ssapmcco/virtualenv/cashflow.cpaldaca.com/3.12/bin/python"
LOG_FILE="${PROJECT_DIR}/logs/cron_bcv.log"

cd "$PROJECT_DIR" || exit 1

export DJANGO_ENV=production
export DEBUG=0

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') - Inicio manage.py bcv ====="
  "$PYTHON" manage.py bcv --strict-window
  EXIT_CODE=$?
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') - Fin bcv (exit ${EXIT_CODE}) ====="
  echo ""
  exit $EXIT_CODE
} >> "$LOG_FILE" 2>&1
