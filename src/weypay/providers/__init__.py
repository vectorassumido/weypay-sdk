"""Providers — cada sub-pacote é um gateway. Nunca importar de um provider a partir de outro
(ver tests/test_isolation.py) — o que é comum vive em weypay.http/.money/.errors/.types."""
