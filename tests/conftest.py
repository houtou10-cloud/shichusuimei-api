"""Shared test isolation: no test may reach the real Stripe API."""

import pytest

from api import stripe_checkout



@pytest.fixture(autouse=True)
def _no_stripe_consumption_network(monkeypatch):
    monkeypatch.setattr(stripe_checkout, "ensure_session_unused", lambda _session_id: None)
    monkeypatch.setattr(stripe_checkout, "record_reading_consumed", lambda _session_id: None)
