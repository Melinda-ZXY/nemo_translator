from __future__ import annotations

import base64
import io
import json
import wave
from dataclasses import dataclass
from urllib.parse import urlparse

from websocket import create_connection


PINYIN_SYLLABLES = {
    "a",
    "ai",
    "an",
    "ang",
    "ao",
    "ba",
    "bai",
    "ban",
    "bang",
    "bao",
    "bei",
    "ben",
    "beng",
    "bi",
    "bian",
    "biao",
    "bie",
    "bin",
    "bing",
    "bo",
    "bu",
    "ca",
    "cai",
    "can",
    "cang",
    "cao",
    "ce",
    "cen",
    "ceng",
    "cha",
    "chai",
    "chan",
    "chang",
    "chao",
    "che",
    "chen",
    "cheng",
    "chi",
    "chong",
    "chou",
    "chu",
    "chuai",
    "chuan",
    "chuang",
    "chui",
    "chun",
    "chuo",
    "ci",
    "cong",
    "cou",
    "cu",
    "cuan",
    "cui",
    "cun",
    "cuo",
    "da",
    "dai",
    "dan",
    "dang",
    "dao",
    "de",
    "dei",
    "den",
    "deng",
    "di",
    "dia",
    "dian",
    "diao",
    "die",
    "ding",
    "diu",
    "dong",
    "dou",
    "du",
    "duan",
    "dui",
    "dun",
    "duo",
    "e",
    "ei",
    "en",
    "eng",
    "er",
    "fa",
    "fan",
    "fang",
    "fei",
    "fen",
    "feng",
    "fo",
    "fou",
    "fu",
    "ga",
    "gai",
    "gan",
    "gang",
    "gao",
    "ge",
    "gei",
    "gen",
    "geng",
    "gong",
    "gou",
    "gu",
    "gua",
    "guai",
    "guan",
    "guang",
    "gui",
    "gun",
    "guo",
    "ha",
    "hai",
    "han",
    "hang",
    "hao",
    "he",
    "hei",
    "hen",
    "heng",
    "hong",
    "hou",
    "hu",
    "hua",
    "huai",
    "huan",
    "huang",
    "hui",
    "hun",
    "huo",
    "ji",
    "jia",
    "jian",
    "jiang",
    "jiao",
    "jie",
    "jin",
    "jing",
    "jiong",
    "jiu",
    "ju",
    "juan",
    "jue",
    "jun",
    "ka",
    "kai",
    "kan",
    "kang",
    "kao",
    "ke",
    "ken",
    "keng",
    "kong",
    "kou",
    "ku",
    "kua",
    "kuai",
    "kuan",
    "kuang",
    "kui",
    "kun",
    "kuo",
    "la",
    "lai",
    "lan",
    "lang",
    "lao",
    "le",
    "lei",
    "leng",
    "li",
    "lia",
    "lian",
    "liang",
    "liao",
    "lie",
    "lin",
    "ling",
    "liu",
    "lo",
    "long",
    "lou",
    "lu",
    "luan",
    "lue",
    "lun",
    "luo",
    "ma",
    "mai",
    "man",
    "mang",
    "mao",
    "me",
    "mei",
    "men",
    "meng",
    "mi",
    "mian",
    "miao",
    "mie",
    "min",
    "ming",
    "miu",
    "mo",
    "mou",
    "mu",
    "na",
    "nai",
    "nan",
    "nang",
    "nao",
    "ne",
    "nei",
    "nen",
    "neng",
    "ni",
    "nian",
    "niang",
    "niao",
    "nie",
    "nin",
    "ning",
    "niu",
    "nong",
    "nou",
    "nu",
    "nuan",
    "nue",
    "nuo",
    "o",
    "ou",
    "pa",
    "pai",
    "pan",
    "pang",
    "pao",
    "pei",
    "pen",
    "peng",
    "pi",
    "pian",
    "piao",
    "pie",
    "pin",
    "ping",
    "po",
    "pou",
    "pu",
    "qi",
    "qia",
    "qian",
    "qiang",
    "qiao",
    "qie",
    "qin",
    "qing",
    "qiong",
    "qiu",
    "qu",
    "quan",
    "que",
    "qun",
    "ran",
    "rang",
    "rao",
    "re",
    "ren",
    "reng",
    "ri",
    "rong",
    "rou",
    "ru",
    "ruan",
    "rui",
    "run",
    "ruo",
    "sa",
    "sai",
    "san",
    "sang",
    "sao",
    "se",
    "sen",
    "seng",
    "sha",
    "shai",
    "shan",
    "shang",
    "shao",
    "she",
    "shen",
    "sheng",
    "shi",
    "shou",
    "shu",
    "shua",
    "shuai",
    "shuan",
    "shuang",
    "shui",
    "shun",
    "shuo",
    "si",
    "song",
    "sou",
    "su",
    "suan",
    "sui",
    "sun",
    "suo",
    "ta",
    "tai",
    "tan",
    "tang",
    "tao",
    "te",
    "teng",
    "ti",
    "tian",
    "tiao",
    "tie",
    "ting",
    "tong",
    "tou",
    "tu",
    "tuan",
    "tui",
    "tun",
    "tuo",
    "wa",
    "wai",
    "wan",
    "wang",
    "wei",
    "wen",
    "weng",
    "wo",
    "wu",
    "xi",
    "xia",
    "xian",
    "xiang",
    "xiao",
    "xie",
    "xin",
    "xing",
    "xiong",
    "xiu",
    "xu",
    "xuan",
    "xue",
    "xun",
    "ya",
    "yan",
    "yang",
    "yao",
    "ye",
    "yi",
    "yin",
    "ying",
    "yo",
    "yong",
    "you",
    "yu",
    "yuan",
    "yue",
    "yun",
    "za",
    "zai",
    "zan",
    "zang",
    "zao",
    "ze",
    "zei",
    "zen",
    "zeng",
    "zha",
    "zhai",
    "zhan",
    "zhang",
    "zhao",
    "zhe",
    "zhen",
    "zheng",
    "zhi",
    "zhong",
    "zhou",
    "zhu",
    "zhua",
    "zhuai",
    "zhuan",
    "zhuang",
    "zhui",
    "zhun",
    "zhuo",
    "zi",
    "zong",
    "zou",
    "zu",
    "zuan",
    "zui",
    "zun",
    "zuo",
}

CUSTOM_SYLLABLES = {"ki", "ko", "no", "mii", "muu", "nuu", "noo"}
SYLLABLES = PINYIN_SYLLABLES | CUSTOM_SYLLABLES
MAX_SYLLABLE_LEN = max(len(syllable) for syllable in SYLLABLES)


@dataclass
class TTSResult:
    wav_bytes: bytes
    sample_rate: int
    status: str


def nemo_to_tts_text(nemo_text: str) -> str:
    syllables: list[str] = []
    for raw_token in (nemo_text or "").replace("-", " ").split():
        token = _expand_long_vowels(raw_token.lower())
        syllables.extend(_split_syllables(token))
    return f"【{''.join(f'{syllable}1' for syllable in syllables)}】"


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


def _expand_long_vowels(token: str) -> str:
    for vowel in ("i", "u", "o", "a", "e"):
        token = token.replace(f"{vowel}:", vowel * 2)
    return token.replace(":", "")


def _split_syllables(token: str) -> list[str]:
    if not token:
        return []

    split = _split_syllables_from(token, 0, {})
    return split or [token]


def _split_syllables_from(token: str, index: int, memo: dict[int, list[str] | None]) -> list[str] | None:
    if index == len(token):
        return []
    if index in memo:
        return memo[index]

    remaining = len(token) - index
    for length in range(min(MAX_SYLLABLE_LEN, remaining), 0, -1):
        candidate = token[index : index + length]
        if candidate not in SYLLABLES:
            continue
        rest = _split_syllables_from(token, index + length, memo)
        if rest is not None:
            memo[index] = [candidate, *rest]
            return memo[index]

    memo[index] = None
    return None


def _pcm16_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)
    return buffer.getvalue()
