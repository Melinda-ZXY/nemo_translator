from __future__ import annotations

import base64
import io
import json
import wave
from dataclasses import dataclass
from urllib.parse import urlparse

from websocket import create_connection


@dataclass
class TTSResult:
    wav_bytes: bytes
    sample_rate: int
    status: str


def synthesize_tts(
    text: str,
    base_url: str = "http://172.16.60.69:7874",
    emotion: str = "happiness",
    temperature: float = 0.5,
    timeout: int = 120,
) -> TTSResult:
    text = (text or "").strip()
    if not text:
        raise ValueError("TTS text is empty.")

    ws_url = _tts_ws_url(base_url)
    ws = create_connection(ws_url, timeout=timeout)
    chunks: list[bytes] = []
    sample_rate: int | None = None
    status = ""

    try:
        ws.send(
            json.dumps(
                {
                    "text": text,
                    "emotion": emotion,
                    "temperature": temperature,
                },
                ensure_ascii=False,
            )
        )

        while True:
            raw = ws.recv()
            if raw is None:
                raise RuntimeError("TTS WebSocket closed before completion.")
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg.get("status"):
                status = msg["status"]

            if msg_type == "chunk" and msg.get("pcm_b64"):
                sample_rate = int(msg["sample_rate"])
                chunks.append(base64.b64decode(msg["pcm_b64"]))
            elif msg_type == "done":
                sample_rate = int(msg.get("sample_rate") or sample_rate or 16000)
                if msg.get("play_pcm_b64"):
                    pcm_bytes = base64.b64decode(msg["play_pcm_b64"])
                else:
                    pcm_bytes = b"".join(chunks)
                return TTSResult(
                    wav_bytes=_pcm16_to_wav(pcm_bytes, sample_rate),
                    sample_rate=sample_rate,
                    status=status or "Done.",
                )
            elif msg_type == "error":
                raise RuntimeError(msg.get("message") or "TTS server returned an error.")
    finally:
        ws.close()


def _tts_ws_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://", "ws://", "wss://")):
        normalized = f"http://{normalized}"

    parsed = urlparse(normalized)
    scheme = "wss" if parsed.scheme in {"https", "wss"} else "ws"
    netloc = parsed.netloc or parsed.path
    return f"{scheme}://{netloc}/ws/tts"


def _pcm16_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
    return buffer.getvalue()
