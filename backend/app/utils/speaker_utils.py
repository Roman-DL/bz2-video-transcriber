"""
Speaker detection utilities for MD transcripts.

Parses speaker labels from MacWhisper-generated markdown files.
Speaker labels appear on separate lines in formats:
- Named: "Фамилия Имя" (Cyrillic, two words, capitalized)
- Anonymous: "SpeakerN" (from MacWhisper diarization)

v0.64+: Created for UI display in SpeakerInfo.
v0.65+: Reused for prompt adaptation and chunk headers.
"""

import re

from app.models.schemas import SpeakerInfo

# Matches "Фамилия Имя" or "SpeakerN" on a standalone line
SPEAKER_PATTERN = re.compile(
    r"^(Speaker\d+|[А-ЯЁA-Z][а-яёa-z]+ [А-ЯЁA-Z][а-яёa-z]+)$"
)


def parse_speakers(text: str) -> SpeakerInfo:
    """Parse speaker labels from MD transcript text.

    Scans each line for speaker patterns. Named speakers have
    Cyrillic "Фамилия Имя" format, anonymous are "SpeakerN".

    Args:
        text: Full text of MD transcript

    Returns:
        SpeakerInfo with detected speakers and scenario
    """
    named: set[str] = set()
    anonymous: set[str] = set()

    for line in text.splitlines():
        line = line.strip()
        if SPEAKER_PATTERN.match(line):
            if line.startswith("Speaker"):
                anonymous.add(line)
            else:
                named.add(line)

    return SpeakerInfo(
        named_speakers=sorted(named),
        anonymous_speakers=sorted(anonymous),
        scenario=_determine_scenario(len(named), len(anonymous) > 0),
    )


def _determine_scenario(named_count: int, has_anonymous: bool) -> str:
    """Determine speaker scenario from counts.

    Args:
        named_count: Number of named speakers
        has_anonymous: Whether anonymous speakers exist

    Returns:
        Scenario string: single, co_speakers, lineup, qa, co_speakers_qa, lineup_qa
    """
    if named_count <= 1 and not has_anonymous:
        return "single"
    if named_count <= 1 and has_anonymous:
        return "qa"
    if named_count == 2:
        return "co_speakers_qa" if has_anonymous else "co_speakers"
    return "lineup_qa" if has_anonymous else "lineup"


if __name__ == "__main__":
    # Quick self-tests
    tests = [
        (
            "Добрый день! Сегодня мы поговорим о бизнесе.\n",
            "single", [], [],
        ),
        (
            "Беркин Андрей\nДобрый день!\n\nДмитрук Светлана\nСпасибо!\n",
            "co_speakers", ["Беркин Андрей", "Дмитрук Светлана"], [],
        ),
        (
            "Speaker1\nПривет!\n\nSpeaker2\nДобрый день!\n",
            "qa", [], ["Speaker1", "Speaker2"],
        ),
        (
            "Беркин Андрей\nТекст\n\nSpeaker3\nВопрос?\n",
            "qa", ["Беркин Андрей"], ["Speaker3"],
        ),
        (
            "Иванов Иван\nТекст\n\nПетров Пётр\nТекст\n\nSpeaker5\nВопрос\n",
            "co_speakers_qa", ["Иванов Иван", "Петров Пётр"], ["Speaker5"],
        ),
        (
            "Иванов Иван\nА\n\nПетров Пётр\nБ\n\nСидоров Сидор\nВ\n",
            "lineup", ["Иванов Иван", "Петров Пётр", "Сидоров Сидор"], [],
        ),
    ]

    passed = 0
    for text, expected_scenario, expected_named, expected_anon in tests:
        info = parse_speakers(text)
        ok = (
            info.scenario == expected_scenario
            and info.named_speakers == expected_named
            and info.anonymous_speakers == expected_anon
        )
        status = "OK" if ok else "FAIL"
        if not ok:
            print(f"  {status}: expected {expected_scenario}, got {info.scenario}")
            print(f"    named: {info.named_speakers} vs {expected_named}")
            print(f"    anon: {info.anonymous_speakers} vs {expected_anon}")
        else:
            print(f"  {status}: scenario={info.scenario}")
        passed += ok

    print(f"\n{passed}/{len(tests)} tests passed")
