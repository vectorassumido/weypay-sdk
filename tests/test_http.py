import socket
from decimal import Decimal

import pytest
import requests
import responses

from weypay.errors import ConfigurationError, GatewayUnavailable, PaymentIndeterminate
from weypay.http import (
    DEFAULT_TIMEOUT,
    FakeResponseRegistry,
    GatewayEndpoints,
    perform_request,
    resolve_base_url,
)
from weypay.types import Environment

URL = "https://sandbox.example.pt/api/pay"


# --- resolve_base_url --------------------------------------------------------------------


def test_resolve_base_url_production() -> None:
    endpoints = GatewayEndpoints(
        production="https://prod.example.pt", sandbox="https://sb.example.pt"
    )
    assert resolve_base_url(Environment.PRODUCTION, endpoints) == "https://prod.example.pt"


def test_resolve_base_url_sandbox_when_available() -> None:
    endpoints = GatewayEndpoints(
        production="https://prod.example.pt", sandbox="https://sb.example.pt"
    )
    assert resolve_base_url(Environment.SANDBOX, endpoints) == "https://sb.example.pt"


def test_resolve_base_url_sandbox_without_real_sandbox_raises() -> None:
    """Regra de docs/ENVIRONMENTS.md: ifthenpay não tem sandbox — SANDBOX sem reconhecimento
    explícito não pode bater silenciosamente em produção."""
    endpoints = GatewayEndpoints(production="https://prod.example.pt", sandbox=None)
    with pytest.raises(ConfigurationError, match="não tem sandbox real"):
        resolve_base_url(Environment.SANDBOX, endpoints)


def test_resolve_base_url_sandbox_without_real_sandbox_acknowledged() -> None:
    endpoints = GatewayEndpoints(production="https://prod.example.pt", sandbox=None)
    result = resolve_base_url(Environment.SANDBOX, endpoints, acknowledge_no_sandbox=True)
    assert result == "https://prod.example.pt"


def test_resolve_base_url_rejects_fake() -> None:
    endpoints = GatewayEndpoints(production="https://prod.example.pt")
    with pytest.raises(ConfigurationError, match="FAKE"):
        resolve_base_url(Environment.FAKE, endpoints)


# --- perform_request: caminho real -------------------------------------------------------


@responses.activate
def test_successful_request_returns_data_and_call() -> None:
    responses.add(responses.POST, URL, json={"status": "ok"}, status=200)

    data, call = perform_request(
        method="POST",
        url=URL,
        provider="ifthenpay",
        operation="mbway.create",
        environment=Environment.SANDBOX,
        json_body={"MbWayKey": "secret", "valor": "20.00"},
        secret_keys=frozenset({"MbWayKey"}),
    )

    assert data == {"status": "ok"}
    assert call.http_status == 200
    assert call.outcome == "success"
    assert call.request["MbWayKey"] == "***"
    assert call.duration_ms >= 0


@responses.activate
def test_always_passes_explicit_timeout() -> None:
    responses.add(responses.POST, URL, json={}, status=200)
    _, call = perform_request(
        method="POST",
        url=URL,
        provider="x",
        operation="y",
        environment=Environment.SANDBOX,
    )
    assert call.http_status == 200
    # DEFAULT_TIMEOUT nunca é None — não há chamada sem timeout explícito no módulo.
    assert DEFAULT_TIMEOUT == (5, 15)


@responses.activate
def test_non_2xx_does_not_raise_provider_decides() -> None:
    responses.add(responses.POST, URL, json={"code": "REJECTED"}, status=400)
    data, call = perform_request(
        method="POST", url=URL, provider="x", operation="y", environment=Environment.SANDBOX
    )
    assert data == {"code": "REJECTED"}
    assert call.outcome == "rejected"
    assert call.http_status == 400


def test_connection_error_raises_gateway_unavailable() -> None:
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(responses.POST, URL, body=requests.exceptions.ConnectionError("boom"))
        with pytest.raises(GatewayUnavailable):
            perform_request(
                method="POST",
                url=URL,
                provider="x",
                operation="y",
                environment=Environment.SANDBOX,
            )


def test_read_timeout_raises_payment_indeterminate_never_unavailable() -> None:
    """Regra central de docs/SECURITY.md #1: timeout != falha confirmada."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(responses.POST, URL, body=requests.exceptions.Timeout("timed out"))
        with pytest.raises(PaymentIndeterminate):
            perform_request(
                method="POST",
                url=URL,
                provider="x",
                operation="y",
                environment=Environment.SANDBOX,
            )


# --- retry: só em leitura, só em erro de ligação/5xx, nunca em 4xx -----------------------


def test_retry_recovers_after_5xx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("weypay.http._sleep_backoff", lambda attempt: None)
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, URL, json={"err": "1"}, status=503)
        rsps.add(responses.GET, URL, json={"status": "ok"}, status=200)
        data, call = perform_request(
            method="GET",
            url=URL,
            provider="x",
            operation="status",
            environment=Environment.SANDBOX,
            retry=True,
        )
        assert data == {"status": "ok"}
        assert call.http_status == 200


def test_retry_never_fires_on_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    slept = []
    monkeypatch.setattr("weypay.http._sleep_backoff", lambda attempt: slept.append(attempt))
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, URL, json={"err": "bad"}, status=404)
        _, call = perform_request(
            method="GET",
            url=URL,
            provider="x",
            operation="status",
            environment=Environment.SANDBOX,
            retry=True,
        )
        assert call.http_status == 404
        assert slept == []  # nunca dormiu para tentar de novo — 4xx não é retryable


def test_retry_not_attempted_when_retry_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Escrita (criação de pagamento) nunca deve passar retry=True."""
    slept = []
    monkeypatch.setattr("weypay.http._sleep_backoff", lambda attempt: slept.append(attempt))
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, URL, json={}, status=503)
        _, call = perform_request(
            method="POST",
            url=URL,
            provider="x",
            operation="create",
            environment=Environment.SANDBOX,
            retry=False,
        )
        assert call.http_status == 503
        assert slept == []


# --- Environment.FAKE: nunca abre rede ----------------------------------------------------


def test_fake_environment_never_opens_a_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Environment.FAKE não pode abrir um socket")

    monkeypatch.setattr(socket, "socket", _forbidden)

    registry = FakeResponseRegistry()
    registry.register("POST", URL, status_code=200, body={"status": "ok"})

    data, call = perform_request(
        method="POST",
        url=URL,
        provider="x",
        operation="create",
        environment=Environment.FAKE,
        fake_registry=registry,
    )
    assert data == {"status": "ok"}
    assert call.outcome == "fake"


def test_fake_environment_without_registry_raises() -> None:
    with pytest.raises(ConfigurationError, match="fake_registry"):
        perform_request(
            method="POST", url=URL, provider="x", operation="y", environment=Environment.FAKE
        )


def test_fake_environment_missing_fixture_raises_not_falls_through() -> None:
    registry = FakeResponseRegistry()  # vazio, de propósito
    with pytest.raises(ConfigurationError, match="nenhuma fixture registada"):
        perform_request(
            method="POST",
            url=URL,
            provider="x",
            operation="y",
            environment=Environment.FAKE,
            fake_registry=registry,
        )


def test_fake_environment_redacts_secrets_too() -> None:
    registry = FakeResponseRegistry()
    registry.register("POST", URL, status_code=200, body={"MbWayKey": "should-not-leak"})
    _, call = perform_request(
        method="POST",
        url=URL,
        provider="x",
        operation="y",
        environment=Environment.FAKE,
        fake_registry=registry,
        secret_keys=frozenset({"MbWayKey"}),
    )
    assert call.response == {"MbWayKey": "***"}
    assert "should-not-leak" not in str(call.response)


# --- redação de segredos embutidos no URL (não só no corpo) ------------------------------


@responses.activate
def test_redacts_secret_embedded_in_url_path() -> None:
    """A GATEWAY_KEY da PINPAY vai no path do URL, não no corpo — secret_keys não a apanha."""
    gateway_key = "GTW-SECRET-123"
    url_with_secret = f"https://api.example.pt/gateway/pinpay/{gateway_key}"
    responses.add(responses.POST, url_with_secret, json={"RedirectUrl": "https://x"}, status=200)

    _, call = perform_request(
        method="POST",
        url=url_with_secret,
        provider="ifthenpay.pinpay",
        operation="create_payment",
        environment=Environment.SANDBOX,
        redact_url_values=frozenset({gateway_key}),
    )
    assert gateway_key not in call.url
    assert call.url == "https://api.example.pt/gateway/pinpay/***"


@responses.activate
def test_real_request_still_uses_the_unredacted_url() -> None:
    """A redação é só no GatewayCall — o pedido real tem de ir para o URL verdadeiro."""
    gateway_key = "GTW-SECRET-123"
    url_with_secret = f"https://api.example.pt/gateway/pinpay/{gateway_key}"
    responses.add(responses.POST, url_with_secret, json={}, status=200)

    perform_request(
        method="POST",
        url=url_with_secret,
        provider="x",
        operation="y",
        environment=Environment.SANDBOX,
        redact_url_values=frozenset({gateway_key}),
    )
    assert responses.calls[0].request.url == url_with_secret


def test_money_sanity_import_does_not_regress() -> None:
    # smoke test só para garantir que os dois módulos coexistem sem import cycle
    from weypay.money import Money

    assert Money(Decimal("1.00")).to_gateway_string() == "1.00"
