"""
Language detection for MD transcripts.

Detects whether transcript is Russian or foreign based on Cyrillic character ratio.
Specific language (EN, ES, etc.) is not determined — only ru vs foreign matters
for pipeline routing (Clean skip, translation instructions).
"""

import re


def detect_language(text: str) -> str:
    """Detect transcript language by Cyrillic character ratio.

    Analyzes first ~500 chars of content text (skipping markdown headers
    and speaker labels) to determine dominant language.

    Args:
        text: Full MD transcript text

    Returns:
        "ru" if >50% letters are Cyrillic, "foreign" otherwise
    """
    # Strip markdown headers and speaker labels, take first 500 chars
    content = _extract_content_text(text)
    sample = content[:500]

    if not sample.strip():
        return "ru"  # Default for empty text

    # Count only letter characters (skip digits, punctuation, whitespace)
    letters = [c for c in sample if c.isalpha()]
    if not letters:
        return "ru"

    cyrillic = sum(1 for c in letters if "\u0400" <= c <= "\u04ff")
    ratio = cyrillic / len(letters)

    return "ru" if ratio > 0.5 else "foreign"


def _extract_content_text(text: str) -> str:
    """Extract content text, skipping headers and speaker labels.

    Removes:
    - Markdown headers (lines starting with #)
    - Speaker labels (SpeakerN or "Фамилия Имя" on standalone lines)

    Args:
        text: Raw MD transcript text

    Returns:
        Content text without headers and speaker labels
    """
    speaker_pattern = re.compile(
        r"^(Speaker\d+|[A-ZА-ЯЁ][a-zа-яё]+ [A-ZА-ЯЁ][a-zа-яё]+)$"
    )
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if speaker_pattern.match(stripped):
            continue
        if stripped:
            lines.append(stripped)
    return " ".join(lines)


def build_language_context(language: str) -> list[str]:
    """Build language context block for LLM prompts.

    Returns list of strings for unpacking into prompt_parts via
    ``*build_language_context(...)``. Empty list for Russian
    transcripts (prompt unchanged).

    Follows same pattern as build_speaker_context() in speaker_utils.py.

    Args:
        language: "ru" or "foreign" from VideoMetadata.language

    Returns:
        List of prompt lines, empty for Russian transcripts
    """
    if language == "ru":
        return []

    return [
        "",
        "## Иностранный транскрипт",
        "",
        "Транскрипт содержит речь на иностранном языке (возможно несколько языков).",
        "- Генерируй текст ПОЛНОСТЬЮ на русском языке",
        "- Используй глоссарий как справочник терминов — применяй canonical формы",
        "- Имена собственные транслитерируй (John Smith → Джон Смит)",
        "- Если в транскрипте есть ошибки транскрибации — исправляй по контексту",
        "- Если спикеры обозначены как Speaker1, Speaker2 — определи их имена из контекста (представление, самопрезентация) и используй в тексте",
    ]


if __name__ == "__main__":
    tests = [
        # (text, expected)
        ("Добрый день! Сегодня мы поговорим о бизнесе.", "ru"),
        ("Good morning everyone! Today we'll talk about business.", "foreign"),
        ("Speaker1\nHello everyone, welcome to our event.\nSpeaker2\nThank you!", "foreign"),
        ("Беркин Андрей\nДобрый день! Сегодня мы поговорим.\n", "ru"),
        (
            "Buenos días! Hoy vamos a hablar sobre el negocio. "
            "And now let me switch to English for a moment.",
            "foreign",
        ),
        ("", "ru"),  # Empty defaults to ru
        ("123 456 789", "ru"),  # No letters defaults to ru
    ]

    passed = 0
    for text, expected in tests:
        result = detect_language(text)
        ok = result == expected
        status = "OK" if ok else "FAIL"
        preview = text[:40].replace("\n", "\\n")
        if not ok:
            print(f"  {status}: detect_language('{preview}...') = {result!r}, expected {expected!r}")
        else:
            print(f"  {status}: '{preview}...' → {result!r}")
        passed += ok

    print(f"\n{passed}/{len(tests)} tests passed")

    # Tests for build_language_context
    print("\n--- build_language_context tests ---")
    ctx_tests = [
        ("ru", True),      # Empty for Russian
        ("foreign", False), # Non-empty for foreign
    ]
    ctx_passed = 0
    for lang, expect_empty in ctx_tests:
        result = build_language_context(lang)
        if expect_empty:
            ok = result == []
        else:
            ok = len(result) > 0 and "Иностранный транскрипт" in "\n".join(result)
        status = "OK" if ok else "FAIL"
        print(f"  {status}: build_language_context({lang!r}) → {'[]' if not result else f'{len(result)} lines'}")
        ctx_passed += ok
    print(f"\n{ctx_passed}/{len(ctx_tests)} build_language_context tests passed")
