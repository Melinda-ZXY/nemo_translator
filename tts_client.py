from __future__ import annotations

import base64
import io
import json
import unicodedata
import wave
from dataclasses import dataclass
from urllib.parse import urlparse

from pypinyin.constants import PINYIN_DICT
from websocket import create_connection
from websocket import WebSocketException

from translator_core import LEXICON


VOWELS = set("aeiou")
SPECIAL_TTS_SYLLABLES = {
    "nemo": ["ni", "mo"],
}
NEMO_TTS_TOKENS = {
    part.lower()
    for entry in LEXICON.values()
    for part in entry.get("nemo", "").replace("-", " ").split()
    if part
}
PINYIN_UMLAUTS = str.maketrans(
    {
        "ü": "v",
        "ǖ": "v",
        "ǘ": "v",
        "ǚ": "v",
        "ǜ": "v",
        "Ü": "v",
        "Ǖ": "v",
        "Ǘ": "v",
        "Ǚ": "v",
        "Ǜ": "v",
    }
)


@dataclass
class TTSResult:
    wav_bytes: bytes
    sample_rate: int
    status: str


def nemo_to_tts_text(nemo_text: str) -> str:
    syllables: list[str] = []
    for token in _tts_tokens(nemo_text):
        if token in SPECIAL_TTS_SYLLABLES:
            syllables.extend(SPECIAL_TTS_SYLLABLES[token])
        elif token in NEMO_TTS_TOKENS:
            syllables.extend(_split_no_diphthong_syllables(_expand_long_vowels(token)))
        else:
            syllables.extend(_split_pinyin_loanword(token))
    return f"[{''.join(f'{syllable}1' for syllable in syllables)}]"


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
    try:
        ws = create_connection(ws_url, timeout=timeout)
    except (OSError, WebSocketException) as exc:
        raise RuntimeError(
            f"Could not connect to TTS server at {ws_url}. "
            "If this app is running on Streamlit Cloud, it cannot reach an internal 172.x.x.x address. "
            "Run the app on the same network as the TTS server, or expose the TTS server through a tunnel/public URL."
        ) from exc
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


def _tts_tokens(nemo_text: str) -> list[str]:
    tokens = []
    for raw_token in (nemo_text or "").lower().replace("-", " ").split():
        token = "".join(char for char in raw_token if char.isalpha() or char == ":")
        if token:
            tokens.append(token)
    return tokens


def _expand_long_vowels(token: str) -> str:
    for vowel in VOWELS:
        token = token.replace(f"{vowel}:", vowel * 2)
    return token.replace(":", "")


def _plain_pinyin(text: str) -> str:
    text = text.lower().translate(PINYIN_UMLAUTS)
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if char.isalpha() and not unicodedata.combining(char)
    )


PINYIN_SYLLABLES = {
    syllable
    for raw in PINYIN_DICT.values()
    for syllable in (_plain_pinyin(part) for part in str(raw).split(","))
    if syllable
}
MAX_PINYIN_SYLLABLE_LEN = max((len(syllable) for syllable in PINYIN_SYLLABLES), default=0)


def _split_pinyin_loanword(token: str) -> list[str]:
    token = _plain_pinyin(token)
    if not token or not PINYIN_SYLLABLES:
        return [token] if token else []

    best = _split_pinyin_from(token, 0, {})
    return best if best is not None else [token]


def _split_pinyin_from(token: str, index: int, memo: dict[int, list[str] | None]) -> list[str] | None:
    if index == len(token):
        return []
    if index in memo:
        return memo[index]

    last_index = min(len(token), index + MAX_PINYIN_SYLLABLE_LEN)
    for end_index in range(last_index, index, -1):
        syllable = token[index:end_index]
        if syllable not in PINYIN_SYLLABLES:
            continue
        rest = _split_pinyin_from(token, end_index, memo)
        if rest is not None:
            memo[index] = [syllable, *rest]
            return memo[index]

    memo[index] = None
    return None


def _split_no_diphthong_syllables(token: str) -> list[str]:
    syllables: list[str] = []
    index = 0

    while index < len(token):
        start = index
        while index < len(token) and token[index] not in VOWELS:
            index += 1

        if index >= len(token):
            if syllables:
                syllables[-1] += token[start:]
            else:
                syllables.append(token[start:])
            break

        vowel = token[index]
        index += 1
        if vowel == "i" and index < len(token) and token[index] == "e":
            index += 1
        while index < len(token) and token[index] == vowel:
            index += 1

        syllables.append(token[start:index])

    return syllables


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
