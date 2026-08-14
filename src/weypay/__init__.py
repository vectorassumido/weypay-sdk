"""weypay — cliente partilhado para gateways de pagamento portugueses.

Ver docs/ARCHITECTURE.md para o desenho e docs/SECURITY.md para as regras não-negociáveis.
"""

from .errors import (
    ConfigurationError,
    GatewayRejected,
    GatewayUnavailable,
    PaymentError,
    PaymentIndeterminate,
    WebhookVerificationError,
)
from .money import Money
from .types import Environment, GatewayCall, PaymentResult, PaymentStatus, WebhookEvent

__all__ = [
    "ConfigurationError",
    "Environment",
    "GatewayCall",
    "GatewayRejected",
    "GatewayUnavailable",
    "Money",
    "PaymentError",
    "PaymentIndeterminate",
    "PaymentResult",
    "PaymentStatus",
    "WebhookEvent",
    "WebhookVerificationError",
]
