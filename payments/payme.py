"""Payme Merchant API (JSON-RPC) integratsiyasi.

Payme kabineti webhook URL: https://<domen>/payments/payme/
Autentifikatsiya: HTTP Basic — login "Paycom", parol — merchant kaliti
(settings.PAYME_MERCHANT_KEY).

Qo'llab-quvvatlanadigan metodlar: CheckPerformTransaction, CreateTransaction,
PerformTransaction, CancelTransaction, CheckTransaction, GetStatement.

Summalar Payme tomonidan **tiyin**da yuboriladi (1 so'm = 100 tiyin).
"""
import base64
import json
import logging

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Transaction
from .gateways import resolve_target, target_from_account, ACCOUNT_KEYS

logger = logging.getLogger('payments')


# ── Payme xato kodlari ───────────────────────────────────────────────────────
class PaymeError(Exception):
    def __init__(self, code, message, data=None):
        self.code = code
        self.message = message      # str yoki {ru,uz,en}
        self.data = data
        super().__init__(message)


ERR_TRANSPORT = -32300
ERR_PARSE = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INSUFFICIENT_PRIVILEGE = -32504
ERR_INVALID_AMOUNT = -31001
ERR_TX_NOT_FOUND = -31003
ERR_CANT_PERFORM = -31008
ERR_CANT_CANCEL = -31007
# Account (-31050..-31099)
ERR_ACCOUNT_NOT_FOUND = -31050
ERR_ALREADY_PAID = -31099


def _ms(dt):
    return int(dt.timestamp() * 1000) if dt else 0


def _now_ms():
    return int(timezone.now().timestamp() * 1000)


def _account_field(account):
    """Xato 'data' uchun account maydon nomini topadi (default: order_id)."""
    if isinstance(account, dict):
        for key in ACCOUNT_KEYS:
            if key in account:
                return key
    return 'order_id'


def _localized(uz):
    return {'ru': uz, 'uz': uz, 'en': uz}


@method_decorator(csrf_exempt, name='dispatch')
class PaymeMerchantView(View):
    """Payme JSON-RPC webhook."""

    def post(self, request, *args, **kwargs):
        # ── Auth ──
        if not self._check_auth(request):
            logger.warning('Payme webhook: auth failed from %s',
                           request.META.get('REMOTE_ADDR'))
            return self._error(None, ERR_INSUFFICIENT_PRIVILEGE,
                               _localized("Ruxsat yo'q (autentifikatsiya xato)."))
        # ── Parse ──
        try:
            payload = json.loads(request.body.decode() or '{}')
        except (ValueError, TypeError):
            return self._error(None, ERR_PARSE, _localized("JSON o'qishda xatolik."))

        rpc_id = payload.get('id')
        method = payload.get('method')
        params = payload.get('params', {}) or {}

        handlers = {
            'CheckPerformTransaction': self.check_perform,
            'CreateTransaction': self.create_transaction,
            'PerformTransaction': self.perform_transaction,
            'CancelTransaction': self.cancel_transaction,
            'CheckTransaction': self.check_transaction,
            'GetStatement': self.get_statement,
        }
        handler = handlers.get(method)
        if handler is None:
            return self._error(rpc_id, ERR_METHOD_NOT_FOUND,
                               _localized(f"Metod topilmadi: {method}"))
        logger.info('Payme webhook: method=%s', method)
        try:
            result = handler(params)
            return JsonResponse({'jsonrpc': '2.0', 'id': rpc_id, 'result': result})
        except PaymeError as e:
            logger.warning('Payme %s error: code=%s', method, e.code)
            return self._error(rpc_id, e.code, e.message, e.data)

    # ── Auth ──────────────────────────────────────────────────────────────
    def _check_auth(self, request):
        key = getattr(settings, 'PAYME_MERCHANT_KEY', '')
        if not key:
            return False
        header = request.META.get('HTTP_AUTHORIZATION', '')
        if not header.startswith('Basic '):
            return False
        try:
            decoded = base64.b64decode(header[6:]).decode()
        except Exception:
            return False
        # Format: "Paycom:<merchant_key>"
        _, _, provided = decoded.partition(':')
        return provided == key

    def _error(self, rpc_id, code, message, data=None):
        err = {'code': code, 'message': message}
        if data is not None:
            err['data'] = data
        return JsonResponse({'jsonrpc': '2.0', 'id': rpc_id, 'error': err})

    # ── Umumiy validatsiya ────────────────────────────────────────────────
    def _resolve_and_validate(self, params, check_amount=True):
        account = params.get('account', {})
        ttype, tid = target_from_account(account)
        if ttype is None:
            raise PaymeError(ERR_ACCOUNT_NOT_FOUND,
                             _localized("Hisob (account) noto'g'ri."),
                             data=_account_field(account))
        obj, ops = resolve_target(ttype, tid)
        if obj is None:
            raise PaymeError(ERR_ACCOUNT_NOT_FOUND,
                             _localized("Buyurtma topilmadi."),
                             data=_account_field(account))
        if check_amount:
            amount_som = ops['amount'](obj)
            if int(params.get('amount', 0)) != amount_som * 100:
                raise PaymeError(ERR_INVALID_AMOUNT, _localized("Summa noto'g'ri."))
        return ttype, tid, obj, ops

    # ── Metodlar ──────────────────────────────────────────────────────────
    def check_perform(self, params):
        ttype, tid, obj, ops = self._resolve_and_validate(params)
        if ops['is_paid'](obj):
            raise PaymeError(ERR_ALREADY_PAID,
                             _localized("To'lov allaqachon amalga oshirilgan."),
                             data=_account_field(params.get('account', {})))
        return {'allow': True}

    @transaction.atomic
    def create_transaction(self, params):
        payme_id = params.get('id')
        existing = Transaction.objects.select_for_update().filter(
            provider='payme', provider_transaction_id=payme_id).first()
        if existing:
            if existing.state != Transaction.STATE_CREATED:
                raise PaymeError(ERR_CANT_PERFORM,
                                 _localized("Tranzaksiya holati noto'g'ri."))
            return {
                'create_time': _ms(existing.created_at),
                'transaction': str(existing.id),
                'state': existing.state,
            }

        ttype, tid, obj, ops = self._resolve_and_validate(params)
        if ops['is_paid'](obj):
            raise PaymeError(ERR_ALREADY_PAID,
                             _localized("To'lov allaqachon amalga oshirilgan."),
                             data=_account_field(params.get('account', {})))
        # Bir obyekt uchun bir vaqtning o'zida bitta faol tranzaksiya
        active = Transaction.objects.select_for_update().filter(
            provider='payme', target_type=ttype, target_id=tid,
            state=Transaction.STATE_CREATED).exclude(provider_transaction_id=payme_id)
        if active.exists():
            raise PaymeError(ERR_ALREADY_PAID,
                             _localized("Buyurtma uchun to'lov jarayonda."),
                             data=_account_field(params.get('account', {})))

        tx = Transaction.objects.create(
            provider='payme', provider_transaction_id=payme_id,
            target_type=ttype, target_id=tid,
            amount=int(params.get('amount', 0)) // 100,
            state=Transaction.STATE_CREATED,
            payme_time=params.get('time'),
        )
        return {
            'create_time': _ms(tx.created_at),
            'transaction': str(tx.id),
            'state': tx.state,
        }

    @transaction.atomic
    def perform_transaction(self, params):
        # Qator qulflanadi — parallel webhook'lar ikki marta to'lashning oldi olinadi.
        tx = self._get_tx(params.get('id'), lock=True)
        if tx.state == Transaction.STATE_CREATED:
            obj, ops = resolve_target(tx.target_type, tx.target_id)
            if obj is not None:
                ops['mark_paid'](obj)
            tx.state = Transaction.STATE_PERFORMED
            tx.performed_at = timezone.now()
            tx.save(update_fields=['state', 'performed_at'])
            logger.info('Payme PAID: %s:%s amount=%s tx=%s',
                        tx.target_type, tx.target_id, tx.amount, tx.id)
        elif tx.state != Transaction.STATE_PERFORMED:
            raise PaymeError(ERR_CANT_PERFORM,
                             _localized("Tranzaksiyani bajarib bo'lmaydi."))
        return {
            'transaction': str(tx.id),
            'perform_time': _ms(tx.performed_at),
            'state': tx.state,
        }

    @transaction.atomic
    def cancel_transaction(self, params):
        tx = self._get_tx(params.get('id'), lock=True)
        reason = params.get('reason')
        if tx.state == Transaction.STATE_CREATED:
            tx.state = Transaction.STATE_CANCELED
            tx.reason = reason
            tx.canceled_at = timezone.now()
            tx.save(update_fields=['state', 'reason', 'canceled_at'])
        elif tx.state == Transaction.STATE_PERFORMED:
            # To'langanidan keyin bekor — obyektni to'lanmagan holatga qaytaramiz
            obj, ops = resolve_target(tx.target_type, tx.target_id)
            if obj is not None:
                ops['mark_unpaid'](obj)
            tx.state = Transaction.STATE_CANCELED_AFTER_PERFORM
            tx.reason = reason
            tx.canceled_at = timezone.now()
            tx.save(update_fields=['state', 'reason', 'canceled_at'])
        return {
            'transaction': str(tx.id),
            'cancel_time': _ms(tx.canceled_at),
            'state': tx.state,
        }

    def check_transaction(self, params):
        tx = self._get_tx(params.get('id'))
        return {
            'create_time': _ms(tx.created_at),
            'perform_time': _ms(tx.performed_at),
            'cancel_time': _ms(tx.canceled_at),
            'transaction': str(tx.id),
            'state': tx.state,
            'reason': tx.reason,
        }

    def get_statement(self, params):
        frm = params.get('from', 0)
        to = params.get('to', _now_ms())
        qs = Transaction.objects.filter(provider='payme')
        out = []
        for tx in qs:
            t = _ms(tx.created_at)
            if t < frm or t > to:
                continue
            out.append({
                'id': tx.provider_transaction_id,
                'time': tx.payme_time or t,
                'amount': tx.amount * 100,
                'account': {f'{tx.target_type}_id': tx.target_id},
                'create_time': _ms(tx.created_at),
                'perform_time': _ms(tx.performed_at),
                'cancel_time': _ms(tx.canceled_at),
                'transaction': str(tx.id),
                'state': tx.state,
                'reason': tx.reason,
            })
        return {'transactions': out}

    def _get_tx(self, payme_id, lock=False):
        qs = Transaction.objects.filter(
            provider='payme', provider_transaction_id=payme_id)
        if lock:
            # select_for_update faqat atomic blok ichida ishlaydi (perform/cancel).
            qs = qs.select_for_update()
        tx = qs.first()
        if tx is None:
            raise PaymeError(ERR_TX_NOT_FOUND, _localized("Tranzaksiya topilmadi."))
        return tx


# ── Checkout URL generatori (mobil/web uchun) ────────────────────────────────
def payme_checkout_url(target_type, target_id, amount_som):
    """Payme to'lov sahifasi URL'ini yaratadi.

    https://checkout.paycom.uz/<base64(m=merchant;ac.<key>=<id>;a=<tiyin>)>
    """
    merchant_id = getattr(settings, 'PAYME_MERCHANT_ID', '')
    key = next((k for k, v in ACCOUNT_KEYS.items() if v == target_type), 'order_id')
    raw = f'm={merchant_id};ac.{key}={target_id};a={int(amount_som) * 100}'
    encoded = base64.b64encode(raw.encode()).decode()
    base = getattr(settings, 'PAYME_CHECKOUT_URL', 'https://checkout.paycom.uz')
    return f'{base}/{encoded}'
