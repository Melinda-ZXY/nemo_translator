from __future__ import annotations

import re

from pypinyin import Style, lazy_pinyin


INITIALS = [
    "zh",
    "ch",
    "sh",
    "b",
    "p",
    "m",
    "f",
    "d",
    "t",
    "n",
    "l",
    "g",
    "k",
    "h",
    "j",
    "q",
    "x",
    "r",
    "z",
    "c",
    "s",
    "y",
    "w",
]
INITIAL_SWAPS = {
    "l": "n",
    "k": "t",
    "g": "d",
    "zh": "z",
    "ch": "c",
    "sh": "s",
}
PINYIN_RE = re.compile(r"^([a-zvü]+)([1-5]?)$")


def convert_text(text: str) -> dict:
    source = text or ""
    raw_units = lazy_pinyin(
        source,
        style=Style.TONE3,
        neutral_tone_with_five=True,
        errors=lambda chars: list(chars),
    )
    if len(raw_units) != len(source):
        raw_units = [
            lazy_pinyin(
                char,
                style=Style.TONE3,
                neutral_tone_with_five=True,
                errors=lambda chars: list(chars),
            )[0]
            for char in source
        ]

    rows = []
    converted_syllables: list[str] = []
    tts_parts: list[str] = []
    current_tts_run: list[str] = []

    for char, original in zip(source, raw_units):
        if _is_cjk(char) and _is_pinyin(original):
            converted, rules = convert_syllable(original)
            rows.append(
                {
                    "字": char,
                    "原拼音": original,
                    "构音障碍拼音": converted,
                    "规则": ", ".join(rules) if rules else "",
                }
            )
            converted_syllables.append(converted)
            current_tts_run.append(converted)
            continue

        if current_tts_run:
            tts_parts.append(f"[{''.join(current_tts_run)}]")
            current_tts_run = []
        tts_parts.append(char)

    if current_tts_run:
        tts_parts.append(f"[{''.join(current_tts_run)}]")

    return {
        "input": source,
        "converted_pinyin": " ".join(converted_syllables),
        "tts_input": "".join(tts_parts),
        "syllables": rows,
    }


def convert_syllable(syllable: str) -> tuple[str, list[str]]:
    base, tone = _split_tone(syllable)
    initial, final = _split_initial(base)

    rules = []
    converted_initial = INITIAL_SWAPS.get(initial, initial)
    if converted_initial != initial:
        rules.append(f"{initial}->{converted_initial}")

    converted_final = final.replace("ei", "ui")
    if converted_final != final:
        rules.append("ei->ui")

    return f"{converted_initial}{converted_final}{tone}", rules


def _split_tone(syllable: str) -> tuple[str, str]:
    normalized = syllable.lower().replace("ü", "v")
    match = PINYIN_RE.match(normalized)
    if not match:
        return normalized, "5"
    return match.group(1), match.group(2) or "5"


def _split_initial(base: str) -> tuple[str, str]:
    for initial in INITIALS:
        if base.startswith(initial):
            return initial, base[len(initial) :]
    return "", base


def _is_pinyin(text: str) -> bool:
    return bool(PINYIN_RE.match(text.lower().replace("ü", "v")))


def _is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"
