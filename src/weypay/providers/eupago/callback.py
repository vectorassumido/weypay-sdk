"""EuPago Webhooks 2.0 (Realtime Webhooks). Ver docs/providers/eupago-webhooks.md.

Ao contrário do 1.0 (`chave_api` no corpo, nunca confirmado como mecanismo de verificação —
ver docs/OPEN-QUESTIONS.md #4) e do `adminCallback` por-pagamento (formato nunca documentado),
o 2.0 tem uma assinatura verificável de facto: header ``X-Signature``, HMAC-SHA256 sobre o
corpo bruto, com a chave de encriptação gerada no backoffice (Canais → Webhooks 2.0) — distinta
da API key usada para criar pagamentos.

A cifra opcional (``encrypt=true``, AES-256-CBC, corpo em ``data`` + header
``X-Initialization-Vector``) não está implementada aqui, deliberadamente — a assinatura já
garante integridade e autenticidade; cifrar o corpo é sobre confidencialidade em trânsito,
redundante com HTTPS. Ver docs/PLAN.md "Deliberadamente de fora" (anti-overengineering).
"""

from __future__ import annotations

import base64
import binascii
import hmac
import json
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

from ...errors import WebhookVerificationError
from ...money import Money
from ...types import PaymentStatus, WebhookEvent

# Vocabulário oficial (docs/providers/eupago-webhooks.md (c)): Paid, Refund, Error, Cancel,
# Expired. "Error" fica de fora deliberadamente — mapeia para UNKNOWN — a documentação não
# esclarece se é falha definitiva do pagamento ou um erro transitório do lado da EuPago; nunca
# assumir sem confirmar (ver docs/SECURITY.md regra 6: estado desconhecido nunca é tratado
# como falha, só registado).
STATUS_MAP: dict[str, PaymentStatus] = {
    "Paid": PaymentStatus.PAID,
    "Refund": PaymentStatus.REFUNDED,
    "Cancel": PaymentStatus.DECLINED,
    "Expired": PaymentStatus.EXPIRED,
}


def verify_signature(*, body: bytes, signature: str, key: str) -> None:
    """Verifica o header ``X-Signature`` — HMAC-SHA256 sobre o corpo bruto (bytes, tal como
    recebido, antes de qualquer parsing), comparado em tempo constante contra o valor
    recebido (base64-decodificado). ``key`` é a chave de encriptação gerada no backoffice,
    nunca a API key de pagamentos."""
    if not key:
        raise WebhookVerificationError("chave de assinatura EuPago não configurada")
    if not signature:
        raise WebhookVerificationError("cabeçalho X-Signature em falta")
    try:
        received = base64.b64decode(signature, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise WebhookVerificationError(f"X-Signature não é base64 válido: {signature}") from exc
    expected = hmac.new(key.encode(), body, sha256).digest()
    if not hmac.compare_digest(expected, received):
        raise WebhookVerificationError("assinatura X-Signature inválida")


def verify_and_parse(*, body: bytes, signature: str, key: str) -> WebhookEvent:
    """Verifica a assinatura e converte o corpo JSON num ``WebhookEvent``. Levanta
    ``WebhookVerificationError`` em qualquer falha de verificação ou de formato — nunca
    devolve um evento a partir de um pedido não verificado."""
    verify_signature(body=body, signature=signature, key=key)

    try:
        data: dict[str, Any] = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WebhookVerificationError(f"corpo não é JSON válido: {exc}") from exc

    transaction = data.get("transactions")
    if not isinstance(transaction, dict):
        raise WebhookVerificationError("corpo sem campo 'transactions'")

    reference = str(transaction.get("reference", "") or "")
    if not reference:
        raise WebhookVerificationError("'transactions.reference' em falta ou vazio")

    raw_status = str(transaction.get("status", "") or "")
    status = STATUS_MAP.get(raw_status, PaymentStatus.UNKNOWN)

    amount = _parse_amount(transaction.get("amount"))

    return WebhookEvent(
        provider="eupago",
        provider_reference=reference,
        status=status,
        raw_status=raw_status,
        dedupe_key=f"eupago:{reference}:{raw_status}:{transaction.get('trid', '')}",
        payload=data,
        amount=amount,
    )


def _parse_amount(amount_data: object) -> Money | None:
    if not isinstance(amount_data, dict):
        return None
    value = amount_data.get("value")
    if value is None:
        return None
    currency = str(amount_data.get("currency") or "EUR")
    try:
        return Money(Decimal(str(value)), currency)
    except (InvalidOperation, TypeError):
        return None
