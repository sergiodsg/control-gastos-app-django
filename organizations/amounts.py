"""Cálculo de montos en Bs. y USD (misma lógica que TransactionForm)."""

from django.utils import timezone

from .models import Account, Transaction


def apply_dual_currency_amounts(amount_bs, amount_usd, daily_rate):
    """
    Completa el monto faltante según la tasa del día.
    Misma regla que TransactionForm.clean().
    """
    daily_rate = daily_rate or 1
    amount_bs = amount_bs or 0
    amount_usd = amount_usd or 0

    if amount_usd and amount_usd != 0 and (not amount_bs or amount_bs == 0):
        amount_bs = round(amount_usd * daily_rate, 2)
    elif amount_bs and amount_bs != 0 and (not amount_usd or amount_usd == 0):
        amount_usd = round(amount_bs / daily_rate, 2) if daily_rate != 0 else 0

    return amount_bs, amount_usd


def opening_balance_transaction_amounts(balance, currency, daily_rate):
    """Montos del saldo inicial según la moneda de la cuenta."""
    if not balance:
        return 0, 0
    if currency == Account.CURRENCY_USD:
        return apply_dual_currency_amounts(0, balance, daily_rate)
    return apply_dual_currency_amounts(balance, 0, daily_rate)


def create_initial_balance_transaction(
    *,
    organization,
    account,
    balance,
    daily_rate,
    tx_date=None,
):
    """Crea la transacción de saldo inicial con equivalente en la otra moneda."""
    balance = balance or 0
    if not balance:
        return None

    rate = daily_rate or 1
    amount_bs, amount_usd = opening_balance_transaction_amounts(
        balance, account.currency, rate
    )

    return Transaction.objects.create(
        organization=organization,
        account=account,
        date=tx_date or timezone.now().date(),
        description=f'Saldo inicial: {account.name}',
        amount_bs=amount_bs,
        amount_usd=amount_usd,
        daily_rate=rate,
        status='completado',
    )
