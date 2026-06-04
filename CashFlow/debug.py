import json
import logging

from django.conf import settings


SENSITIVE_KEYS = ("password", "csrf", "token", "secret")


def _safe_context(context):
    safe = {}
    for key, value in context.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            safe[key] = "***"
        else:
            safe[key] = value
    return safe


def debug_event(event, **context):
    payload = _safe_context(context)
    message = json.dumps(payload, ensure_ascii=False, default=str)
    logger_name = _logger_name_for_event(event)
    level = _level_for_event(event)
    logging.getLogger(logger_name).log(level, "%s | %s", event, message)

    if level >= logging.WARNING:
        logging.getLogger("cashflow.errors").log(level, "%s | %s", event, message)

    if getattr(settings, "DEBUG", False):
        print(f"[{logging.getLevelName(level)}] {event} | {message}")


def _logger_name_for_event(event):
    if event.startswith("transaccion."):
        return "cashflow.transactions"
    if event.startswith("cuenta."):
        return "cashflow.accounts"
    return "cashflow.debug"


def _level_for_event(event):
    if ".error" in event:
        return logging.ERROR
    if "acceso_denegado" in event:
        return logging.WARNING
    return logging.DEBUG


def first_form_error(form):
    for field_errors in form.errors.as_data().values():
        if field_errors and field_errors[0].messages:
            return field_errors[0].messages[0]
    return "Verifique los datos."
