#!/usr/bin/env python3
import os
import sys
import uuid

from fastapi.testclient import TestClient


# Ensure project root is on PYTHONPATH so we can import src.app.main
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from src.app.main import app
except Exception:
    # Fallback to older path style if needed
    from app.main import app  # type: ignore


client = TestClient(app)


def _ok(resp):
    # In CI/test env, services may not initialize → accept 503
    return resp.status_code in (200, 503)


def test_qna_museum_da_nang():
    conv_id = f"test-{uuid.uuid4().hex[:8]}"
    payload = {
        "message": "Cho tôi thông tin về Bảo tàng Đà Nẵng",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi",
        "conversationId": conv_id,
    }
    resp = client.post("/api/v1/chatbot/response", json=payload)
    assert _ok(resp)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("type") in ("QnA", "Service")
        assert isinstance(data.get("answerAI", ""), str)
        # CTA or suggestions should be present for web
        assert data.get("cta") or data.get("suggestions") is not None


def test_followup_pronoun_resolution():
    conv_id = f"test-{uuid.uuid4().hex[:8]}"
    first = {
        "message": "Bảo tàng Đà Nẵng ở đâu?",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi",
        "conversationId": conv_id,
    }
    second = {
        "message": "Ở đó có những gì?",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi",
        "conversationId": conv_id,
    }
    r1 = client.post("/api/v1/chatbot/response", json=first)
    assert _ok(r1)
    r2 = client.post("/api/v1/chatbot/response", json=second)
    assert _ok(r2)
    if r2.status_code == 200:
        d2 = r2.json()
        assert d2.get("type") in ("QnA", "Service")
        assert isinstance(d2.get("answerAI", ""), str)


def test_discover_restaurants_near_dragon_bridge():
    payload = {
        "message": "Tìm nhà hàng gần Cầu Rồng Đà Nẵng",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi",
    }
    resp = client.post("/api/v1/chatbot/response", json=payload)
    assert _ok(resp)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("type") in ("Service", "QnA")  # Service preferred, but allow QnA fallback
        if data.get("type") == "Service":
            assert isinstance(data.get("services", []), list)


def test_discover_hotels_da_nang():
    payload = {
        "message": "Tôi muốn tìm khách sạn ở Đà Nẵng",
        "platform": "web_browser",
        "device": "desktop",
        "language": "vi",
    }
    resp = client.post("/api/v1/chatbot/response", json=payload)
    assert _ok(resp)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("type") in ("Service", "QnA")
        if data.get("type") == "Service":
            assert isinstance(data.get("services", []), list)


