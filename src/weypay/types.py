"""Tipos do core. Ver docs/ARCHITECTURE.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .money import Money


class PaymentStatus(Enum):
    """Estado normalizado, comum aos três gateways. O código/texto exato do gateway viaja
    sempre em paralelo em ``raw_status`` — é ele que se persiste para auditoria; a normalização
    é só para a lógica de negócio decidir o próximo passo."""

    PENDING = "pending"
    PAID = "paid"
    DECLINED = "declined"
    EXPIRED = "expired"
    REFUNDED = "refunded"
    UNKNOWN = "unknown"


class Environment(Enum):
    """Ver docs/ENVIRONMENTS.md — os três gateways não oferecem a mesma coisa. A ifthenpay não
    tem sandbox real; SANDBOX nela só é aceite com acknowledge_no_sandbox=True explícito."""

    SANDBOX = "sandbox"
    PRODUCTION = "production"
    FAKE = "fake"


@dataclass(frozen=True)
class GatewayCall:
    """O registo de auditoria de uma chamada HTTP a um gateway. ``request``/``response`` saem
    sempre já redigidos (ver redaction.py) — a aplicação consumidora persiste-os às cegas."""

    correlation_id: str
    provider: str
    operation: str
    url: str
    http_status: int | None
    duration_ms: int
    request: dict[str, Any]
    response: dict[str, Any] | str | None
    outcome: str
    occurred_at: datetime


@dataclass(frozen=True)
class PaymentResult:
    """Resultado de uma criação de pagamento."""

    provider: str
    provider_payment_id: str
    status: PaymentStatus
    raw_status: str
    call: GatewayCall
    redirect_url: str | None = None
    entity: str | None = None
    reference: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class WebhookEvent:
    """Resultado de um callback/webhook, já verificado e normalizado."""

    provider: str
    provider_reference: str
    status: PaymentStatus
    raw_status: str
    dedupe_key: str
    payload: dict[str, Any]
    amount: Money | None = None
    ack_body: dict[str, Any] | None = None
