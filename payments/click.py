"""Click Shop API integratsiyasi (Prepare / Complete).

Click kabineti URL'lari:
    Prepare URL:  https://<domen>/payments/click/prepare/
    Complete URL: https://<domen>/payments/click/complete/

Imzo (sign_string) MD5 bilan tekshiriladi. Summalar **so'm**da keladi.

Sozlamalar (env): CLICK_SERVICE_ID, CLICK_MERCHANT_ID, CLICK_SECRET_KEY,
CLICK_MERCHANT_USER_ID.
"""
import hashlib
import logging

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Transaction
from .gateways import resolve_target, PAYABLES

logger = logging.getLogger('payments')

# Click xato kodlari
OK = 0
ERR_SIGN = -1
ERR_AMOUNT = -2
ERR_ACTION = -3
ERR_ALREADY_PAID = -4
ERR_NOT_FOUND = -5
ERR_TX_NOT_FOUND = -6
ERR_CANCELLED = -9

ACTION_PREPARE = '0'
ACTION_COMPLETE = '1'


def _secret():
    return getattr(settings, 'CLICK_SECRET_KEY', '')


def _service_id():
    return str(getattr(settings, 'CLICK_SERVICE_ID', ''))


def _parse_merchant_trans_id(value):
    """'order~<id>' → ('order', '<id>')."""
    if value and '~' in value:
        ttype, _, tid = value.partition('~')
        if ttype in PAYABLES:
            return ttype, tid
    return None, None


def _verify_prepare_sign(p):
    raw = (str(p.get('click_trans_id', '')) + str(p.get('service_id', '')) + _secret()
           + str(p.get('merchant_trans_id', '')) + str(p.get('amount', ''))
           + str(p.get('action', '')) + str(p.get('sign_time', '')))
    return hashlib.md5(raw.encode()).hexdigest() == p.get('sign_string', '')


def _verify_complete_sign(p):
    raw = (str(p.get('click_trans_id', '')) + str(p.get('service_id', '')) + _secret()
           + str(p.get('merchant_trans_id', '')) + str(p.get('merchant_prepare_id', ''))
           + str(p.get('amount', '')) + str(p.get('action', '')) + str(p.get('sign_time', '')))
    return hashlib.md5(raw.encode()).hexdigest() == p.get('sign_string', '')


def _amount_matches(obj, ops, amount_str):
    try:
        return abs(float(amount_str) - float(ops['amount'](obj))) < 0.01
    except (ValueError, TypeError):
        return False


def _resp(p, error, note, extra=None):
    body = {
        'click_trans_id': p.get('click_trans_id'),
        'merchant_trans_id': p.get('merchant_trans_id'),
        'error': error,
        'error_note': note,
    }
    if extra:
        body.update(extra)
    return JsonResponse(body)


@csrf_exempt
@require_POST
def click_prepare(request):
    p = request.POST
    if not _verify_prepare_sign(p):
        return _resp(p, ERR_SIGN, 'SIGN CHECK FAILED')
    if str(p.get('action')) != ACTION_PREPARE:
        return _resp(p, ERR_ACTION, 'Action not found')

    ttype, tid = _parse_merchant_trans_id(p.get('merchant_trans_id'))
    if ttype is None:
        return _resp(p, ERR_NOT_FOUND, 'Order not found')
    obj, ops = resolve_target(ttype, tid)
    if obj is None:
        return _resp(p, ERR_NOT_FOUND, 'Order not found')
    if ops['is_paid'](obj):
        return _resp(p, ERR_ALREADY_PAID, 'Already paid')
    if not _amount_matches(obj, ops, p.get('amount')):
        return _resp(p, ERR_AMOUNT, 'Incorrect parameter amount')

    click_trans_id = str(p.get('click_trans_id'))
    tx, _created = Transaction.objects.get_or_create(
        provider='click', provider_transaction_id=click_trans_id,
        defaults={'target_type': ttype, 'target_id': tid,
                  'amount': int(float(p.get('amount', 0))),
                  'state': Transaction.STATE_CREATED},
    )
    return _resp(p, OK, 'Success',
                 {'merchant_prepare_id': str(tx.id)})


@csrf_exempt
@require_POST
@transaction.atomic
def click_complete(request):
    p = request.POST
    if not _verify_complete_sign(p):
        return _resp(p, ERR_SIGN, 'SIGN CHECK FAILED')
    if str(p.get('action')) != ACTION_COMPLETE:
        return _resp(p, ERR_ACTION, 'Action not found')

    click_trans_id = str(p.get('click_trans_id'))
    prepare_id = p.get('merchant_prepare_id')
    # Qator qulflanadi — parallel webhook'lar ikki marta to'lashning oldi olinadi.
    tx = Transaction.objects.select_for_update().filter(
        provider='click', provider_transaction_id=click_trans_id, id=prepare_id).first()
    if tx is None:
        return _resp(p, ERR_TX_NOT_FOUND, 'Transaction does not exist')

    # Click o'z tomonidan xato yuborsa yoki to'lov bekor qilinsa
    if str(p.get('error', '0')) not in ('0', ''):
        if tx.state == Transaction.STATE_CREATED:
            tx.state = Transaction.STATE_CANCELED
            tx.save(update_fields=['state'])
        return _resp(p, ERR_CANCELLED, 'Transaction cancelled')

    obj, ops = resolve_target(tx.target_type, tx.target_id)
    if obj is None:
        return _resp(p, ERR_NOT_FOUND, 'Order not found')
    if not _amount_matches(obj, ops, p.get('amount')):
        return _resp(p, ERR_AMOUNT, 'Incorrect parameter amount')

    if tx.state == Transaction.STATE_PERFORMED:
        return _resp(p, OK, 'Already confirmed',
                     {'merchant_confirm_id': str(tx.id)})
    if tx.state != Transaction.STATE_CREATED:
        return _resp(p, ERR_CANCELLED, 'Transaction cancelled')

    if ops['is_paid'](obj):
        return _resp(p, ERR_ALREADY_PAID, 'Already paid')

    ops['mark_paid'](obj)
    tx.state = Transaction.STATE_PERFORMED
    tx.performed_at = timezone.now()
    tx.save(update_fields=['state', 'performed_at'])
    logger.info('Click PAID: %s:%s amount=%s tx=%s',
                tx.target_type, tx.target_id, tx.amount, tx.id)
    return _resp(p, OK, 'Success', {'merchant_confirm_id': str(tx.id)})


# ── To'lov URL generatori ────────────────────────────────────────────────────
def click_checkout_url(target_type, target_id, amount_som):
    """Click to'lov sahifasi URL'i.

    https://my.click.uz/services/pay?service_id=..&merchant_id=..&amount=..&transaction_param=..
    """
    service_id = _service_id()
    merchant_id = str(getattr(settings, 'CLICK_MERCHANT_ID', ''))
    trans_param = f'{target_type}~{target_id}'
    base = getattr(settings, 'CLICK_CHECKOUT_URL', 'https://my.click.uz/services/pay')
    return (f'{base}?service_id={service_id}&merchant_id={merchant_id}'
            f'&amount={int(amount_som)}&transaction_param={trans_param}')
