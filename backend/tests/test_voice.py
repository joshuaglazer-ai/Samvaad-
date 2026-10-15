"""Optional server voice (Sarvam) — browser speech stays the default; this is only the fallback. No network."""
import base64
import json

import httpx
import pytest

from app import config
from app.routers import voice


@pytest.fixture()
def sarvam(monkeypatch):
    """Turn server voice on with a fake Sarvam; returns the list of requests it received."""
    seen: list[httpx.Request] = []
    replies: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if replies:
            return replies.pop(0)
        if request.url.path == "/text-to-speech":
            return httpx.Response(200, json={"audios": [base64.b64encode(b"MP3DATA").decode()]})
        return httpx.Response(200, json={"transcript": " ನನಗೆ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಆಗಬೇಕು ", "language_code": "kn-IN"})

    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    config.get_settings.cache_clear()
    monkeypatch.setattr(voice, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(voice, "_sleep", lambda s: None)
    voice._tts_cache.clear()
    voice._calls.clear()
    yield seen, replies
    config.get_settings.cache_clear()


def test_status_is_off_without_a_key(client):
    assert client.get("/api/voice/status").json()["server_tts"] is False
    assert client.post("/api/voice/tts", json={"text": "hello", "language": "kn"}).status_code == 503


def test_tts_proxies_to_sarvam_and_caches(client, sarvam):
    seen, _ = sarvam
    assert client.get("/api/voice/status").json() == {"server_tts": True, "server_stt": True, "provider": "sarvam",
                                                      "languages": ["en", "kn", "hi", "te"]}
    r = client.post("/api/voice/tts", json={"text": "ನಮಸ್ಕಾರ", "language": "kn"})
    assert r.status_code == 200 and r.content == b"MP3DATA" and r.headers["content-type"] == "audio/mpeg"
    body = json.loads(seen[0].content)
    assert body["language_code"] == "kn-IN" and body["model"] == "bulbul:v3"
    assert seen[0].headers["api-subscription-key"] == "test-key"
    again = client.post("/api/voice/tts", json={"text": "ನಮಸ್ಕಾರ", "language": "kn"})
    assert again.headers["x-voice-cache"] == "hit" and len(seen) == 1  # no second paid call


def test_stt_transcribes_an_upload(client, sarvam):
    seen, _ = sarvam
    r = client.post("/api/voice/stt", data={"language": "kn"}, files={"file": ("speech.webm", b"\x1a\x45audio", "audio/webm")})
    assert r.json() == {"transcript": "ನನಗೆ ಎಲೆಕ್ಟ್ರಿಷಿಯನ್ ಆಗಬೇಕು", "language": "kn"}
    assert b'name="language_code"' in seen[0].content and b"kn-IN" in seen[0].content


def test_voice_retries_429_then_reports_unavailable(client, sarvam):
    seen, replies = sarvam
    replies.extend([httpx.Response(429), httpx.Response(429), httpx.Response(429)])
    r = client.post("/api/voice/tts", json={"text": "नमस्ते", "language": "hi"})
    assert r.status_code == 502 and len(seen) == 3  # first try + 2 retries


def test_voice_input_limits(client, sarvam):
    assert client.post("/api/voice/tts", json={"text": "x" * 601, "language": "kn"}).status_code == 422
    assert client.post("/api/voice/tts", json={"text": "hi", "language": "fr"}).status_code == 422
    big = b"0" * (voice.MAX_AUDIO_BYTES + 1)
    assert client.post("/api/voice/stt", data={"language": "te"}, files={"file": ("a.webm", big)}).status_code == 413
