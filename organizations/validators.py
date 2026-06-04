import re

from django.core.exceptions import ValidationError

RIF_PATTERN = re.compile(r'^[JVEGPFjvegp]\-?\d{8,9}\-?\d?$')
ACCOUNT_NUMBER_PATTERN = re.compile(r'^\d{10,20}$')


def normalize_rif(value):
    return (value or '').strip().upper().replace('-', '').replace(' ', '')


def validate_rif(value):
    normalized = normalize_rif(value)
    if not normalized:
        raise ValidationError('El RIF es obligatorio.')
    if not RIF_PATTERN.match(value.strip()):
        raise ValidationError('Formato de RIF inválido. Ejemplo: J-12345678-9')
    if not re.match(r'^[JVEGPF]\d{8,9}$', normalized):
        raise ValidationError('El RIF debe iniciar con J, V, E, G o P seguido de 8 o 9 dígitos.')
    return normalized


def validate_account_number(value):
    raw = (value or '').strip().replace('-', '').replace(' ', '')
    if not raw:
        raise ValidationError('El número de cuenta es obligatorio.')
    if not ACCOUNT_NUMBER_PATTERN.match(raw):
        raise ValidationError('El número de cuenta debe tener entre 10 y 20 dígitos.')
    return raw


def validate_holder(value):
    holder = (value or '').strip()
    if len(holder) < 3:
        raise ValidationError('El titular debe tener al menos 3 caracteres.')
    if len(holder) > 255:
        raise ValidationError('El titular es demasiado largo.')
    return holder
