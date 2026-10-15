"""Optional server voice (Sarvam): text-to-speech (Bulbul) and speech-to-text (Saaras) for phones whose browser has
no Kannada / Hindi / Telugu voice. The browser's own speech stays the default (free); the frontend only calls these
when it has to. The Sarvam key never leaves the backend.
"""
from __future__ import annotations

import base64
import logging
import time
from collections import OrderedDict, defaultdict, deque

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field

from ..config import get_settings

router = APIRouter(prefix="/api/voice", tags=["voice"])
log = logging.getLogger("samvaad.voice")

LOCALES = {"en": "en-IN", "kn": "kn-IN", "hi": "hi-IN", "te": "te-IN"}
SARVAM = "https://api.sarvam.ai"
MAX_TEXT = 600            # one bot answer is ~50 words; keeps credit use small
MAX_AUDIO_BYTES = 2_000_000
LIMIT, WINDOW = 40, 600   # requests per client per 10 minutes (demo-grade, in memory)
_calls: dict[str, deque] = defaultdict(deque)
_tts_cache: "OrderedDict[tuple[str, str], bytes]" = OrderedDict()
CACHE_SIZE = 200
_transport: httpx.BaseTransport | None = None  # tests inject a fake transport
_sleep = time.sleep


def enabled() -> bool:
    s = get_settings()
    return bool(s.sarvam_api_key) and s.sarvam_voice_fallback


def _limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    q, now = _calls[client], time.monotonic()
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= LIMIT:
        raise HTTPException(429, "too many voice requests, please wait a few minutes")
    q.append(now)


def _sarvam(path: str, **kwargs) -> dict:
    """POST to Sarvam with the same 429/503 backoff as the chat providers (at most LLM_MAX_RETRIES retries)."""
    s = get_settings()
    with httpx.Client(timeout=30.0, transport=_transport) as http:
        for attempt in range(s.llm_max_retries + 1):
            r = http.post(f"{SARVAM}{path}", headers={"api-subscription-key": s.sarvam_api_key}, **kwargs)
            if r.status_code in (429, 503) and attempt < s.llm_max_retries:
                _sleep(min(1.5 * 2 ** attempt, 10.0))
                continue
            if r.status_code >= 400:
                log.warning("sarvam %s failed: %s %s", path, r.status_code, r.text[:200])
                raise HTTPException(502, "voice service is not available right now")
            return r.json()
    raise HTTPException(502, "voice service is busy right now")


@router.get("/status")
def status() -> dict:
    on = enabled()
    return {"server_tts": on, "server_stt": on, "provider": "sarvam" if on else None, "languages": list(LOCALES)}


class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    language: str = Field(pattern="^(en|kn|hi|te)$")


@router.post("/tts")
def tts(body: TtsIn, request: Request) -> Response:
    if not enabled():
        raise HTTPException(503, "server voice is off")
    key = (body.language, body.text.strip())
    if key in _tts_cache:  # the same question or answer read again costs nothing
        _tts_cache.move_to_end(key)
        return Response(_tts_cache[key], media_type="audio/mpeg", headers={"X-Voice-Cache": "hit"})
    _limit(request)
    data = _sarvam("/text-to-speech", json={"text": key[1], "target_language_code": LOCALES[body.language],
                                            "language_code": LOCALES[body.language], "model": "bulbul:v3",
                                            "pace": 0.95, "output_audio_codec": "mp3", "speech_sample_rate": 22050})
    try:
        audio = base64.b64decode(data["audios"][0])
    except (KeyError, IndexError, ValueError) as exc:
        raise HTTPException(502, "voice service returned no audio") from exc
    _tts_cache[key] = audio
    while len(_tts_cache) > CACHE_SIZE:
        _tts_cache.popitem(last=False)
    return Response(audio, media_type="audio/mpeg", headers={"X-Voice-Cache": "miss"})


@router.post("/stt")
async def stt(request: Request, language: str = Form(..., pattern="^(en|kn|hi|te)$"),
              file: UploadFile = File(...)) -> dict:
    if not enabled():
        raise HTTPException(503, "server voice is off")
    audio = await file.read(MAX_AUDIO_BYTES + 1)
    if not audio:
        raise HTTPException(422, "empty recording")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "recording too long")
    _limit(request)
    data = _sarvam("/speech-to-text",
                   files={"file": (file.filename or "speech.webm", audio, file.content_type or "audio/webm")},
                   data={"model": "saaras:v3", "language_code": LOCALES[language], "mode": "transcribe"})
    return {"transcript": (data.get("transcript") or "").strip(), "language": language}
