"""
Speaker detection utilities for MD transcripts.

Parses speaker labels from MacWhisper-generated markdown files.
Speaker labels appear on separate lines in formats:
- Named: "Фамилия Имя" (Cyrillic, two words, capitalized)
- Anonymous: "SpeakerN" (from MacWhisper diarization)

v0.64+: Created for UI display in SpeakerInfo.
v0.65+: Reused for prompt adaptation and chunk headers.
v0.79+: build_speaker_context() for LLM prompts, abbreviate_name() for chunk headers.
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


def abbreviate_name(full_name: str) -> str:
    """Abbreviate 'Фамилия Имя' to 'Фамилия И.'

    Args:
        full_name: Full name like 'Беркин Андрей'

    Returns:
        Abbreviated name like 'Беркин А.' or original if not two words
    """
    parts = full_name.strip().split()
    if len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    return full_name


def build_speaker_context(
    speaker_info: SpeakerInfo | None,
    host_name: str | None = None,
) -> list[str]:
    """Build speaker context block for LLM prompts.

    Returns list of strings for unpacking into prompt_parts via
    ``*build_speaker_context(...)``. Empty list for single-speaker
    scenarios (prompt unchanged).

    Args:
        speaker_info: SpeakerInfo from VideoMetadata (None for legacy)
        host_name: Host/moderator name from metadata.speaker (for lineup)

    Returns:
        List of prompt lines, empty for single/None scenarios
    """
    if speaker_info is None or speaker_info.scenario == "single":
        return []

    scenario = speaker_info.scenario
    base_scenario = scenario.replace("_qa", "")
    has_qa = scenario.endswith("_qa") or scenario == "qa"

    # Pure Q&A with no named co-speakers
    if scenario == "qa":
        anon_list = ", ".join(speaker_info.anonymous_speakers)
        return [
            "",
            "## Мультиспикерный контент",
            f"Тип: вопросы из зала",
            f"Есть Q&A: да ({anon_list})",
        ]

    lines = [
        "",
        "## Мультиспикерный контент",
    ]

    named = speaker_info.named_speakers

    if base_scenario == "co_speakers":
        lines.append(f"Тип: со-спикеры")
        lines.append(f"Спикеры: {', '.join(named)}")
    elif base_scenario == "lineup":
        lines.append(f"Тип: линейка выступлений")
        lines.append(f"Участники: {', '.join(named)}")
        if host_name:
            lines.append(f"Ведущий: {host_name}")

    if has_qa:
        anon_list = ", ".join(speaker_info.anonymous_speakers)
        lines.append(f"Есть Q&A: да ({anon_list})")

    return lines


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

    print(f"\n{passed}/{len(tests)} parse_speakers tests passed")

    # Tests for abbreviate_name
    print("\n--- abbreviate_name tests ---")
    abbrev_tests = [
        ("Беркин Андрей", "Беркин А."),
        ("Дмитрук Светлана", "Дмитрук С."),
        ("SingleName", "SingleName"),
        ("Иванов Иван Иванович", "Иванов Иван Иванович"),
        ("  Беркин Андрей  ", "Беркин А."),
    ]
    abbrev_passed = 0
    for full, expected in abbrev_tests:
        result = abbreviate_name(full)
        ok = result == expected
        status = "OK" if ok else "FAIL"
        if not ok:
            print(f"  {status}: abbreviate_name({full!r}) = {result!r}, expected {expected!r}")
        else:
            print(f"  {status}: {full!r} → {result!r}")
        abbrev_passed += ok
    print(f"\n{abbrev_passed}/{len(abbrev_tests)} abbreviate_name tests passed")

    # Tests for build_speaker_context
    print("\n--- build_speaker_context tests ---")
    ctx_tests = [
        # (speaker_info, host_name, expected_empty, expected_type_substring)
        (None, None, True, None),
        (SpeakerInfo(scenario="single"), None, True, None),
        (
            SpeakerInfo(
                named_speakers=["Беркин Андрей", "Дмитрук Светлана"],
                scenario="co_speakers",
            ),
            None, False, "со-спикеры",
        ),
        (
            SpeakerInfo(
                named_speakers=["Беркин Андрей", "Дмитрук Светлана"],
                anonymous_speakers=["Speaker3"],
                scenario="co_speakers_qa",
            ),
            None, False, "со-спикеры",
        ),
        (
            SpeakerInfo(
                named_speakers=["Иванов Иван", "Петров Пётр", "Сидоров Сидор"],
                scenario="lineup",
            ),
            "Ведущий Имя", False, "линейка",
        ),
        (
            SpeakerInfo(
                named_speakers=["Иванов Иван", "Петров Пётр", "Сидоров Сидор"],
                anonymous_speakers=["Speaker5"],
                scenario="lineup_qa",
            ),
            "Ведущий Имя", False, "линейка",
        ),
        (
            SpeakerInfo(
                anonymous_speakers=["Speaker1", "Speaker2"],
                scenario="qa",
            ),
            None, False, "вопросы из зала",
        ),
    ]
    ctx_passed = 0
    for info, host, expect_empty, expect_sub in ctx_tests:
        result = build_speaker_context(info, host)
        scenario_name = info.scenario if info else "None"
        if expect_empty:
            ok = result == []
            status = "OK" if ok else "FAIL"
            if not ok:
                print(f"  {status}: scenario={scenario_name}, expected [], got {result}")
            else:
                print(f"  {status}: scenario={scenario_name} → []")
        else:
            joined = "\n".join(result)
            ok = expect_sub in joined
            # Check Q&A line for _qa scenarios
            if info and info.scenario.endswith("_qa"):
                ok = ok and "Есть Q&A: да" in joined
            status = "OK" if ok else "FAIL"
            if not ok:
                print(f"  {status}: scenario={scenario_name}, expected '{expect_sub}' in output")
                print(f"    got: {result}")
            else:
                print(f"  {status}: scenario={scenario_name} → contains '{expect_sub}'")
        ctx_passed += ok
    print(f"\n{ctx_passed}/{len(ctx_tests)} build_speaker_context tests passed")

    total = passed + abbrev_passed + ctx_passed
    total_tests = len(tests) + len(abbrev_tests) + len(ctx_tests)
    print(f"\n{'='*40}")
    print(f"Total: {total}/{total_tests} tests passed")
