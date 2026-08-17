import hashlib

import pytest
from app.domain.documents import ScreenplayElementKind, normalize_screenplay


def test_normalization_is_stable_and_finds_multilingual_scene_headings() -> None:
    source = (
        "\ufeffINT. ROOM - DAY\r\nHello e\u0301.\r\n\r\n## 外景 - 夜\r\n你好世界。\r\n"
    )

    first = normalize_screenplay(source)
    second = normalize_screenplay(source)

    assert first == second
    assert first.text == "INT. ROOM - DAY\nHello é.\n\n## 外景 - 夜\n你好世界。\n"
    assert first.detected_language == "mixed"
    assert len(first.scenes) == 2
    first_digest = hashlib.sha256(b"1:int. room - day").hexdigest()[:12]
    second_digest = hashlib.sha256("2:外景 - 夜".encode()).hexdigest()[:12]
    assert first.scenes[0].id == f"scene-0001-{first_digest}"
    assert first.scenes[1].id == f"scene-0002-{second_digest}"
    assert first.scenes[0].end == first.scenes[1].start
    assert first.scenes[1].end == len(first.text)
    assert first.quality_warnings == ()


def test_missing_heading_produces_one_stable_scene_and_controlled_warning() -> None:
    normalized = normalize_screenplay("A short treatment without headings.")

    assert normalized.text.endswith("\n")
    assert normalized.detected_language == "en-US"
    assert len(normalized.scenes) == 1
    assert normalized.scenes[0].start == 0
    assert normalized.scenes[0].end == len(normalized.text)
    assert normalized.quality_warnings == ("scene_heading_missing",)


def test_multilingual_structure_preserves_exact_element_spans() -> None:
    normalized = normalize_screenplay(
        "INT. ROOM - DAY\n"
        "The room is quiet.\n\n"
        "ALICE\n"
        "(whispering)\n"
        "We should leave.\n\n"
        "内景 客厅 - 夜\n"
        "房间很安静。\n\n"
        "小明\n"
        "（低声）\n"
        "我们该走了。\n"
    )

    expected = [
        (ScreenplayElementKind.HEADING, "INT. ROOM - DAY"),
        (ScreenplayElementKind.ACTION, "The room is quiet."),
        (ScreenplayElementKind.CHARACTER, "ALICE"),
        (ScreenplayElementKind.PARENTHETICAL, "(whispering)"),
        (ScreenplayElementKind.DIALOGUE, "We should leave."),
        (ScreenplayElementKind.HEADING, "内景 客厅 - 夜"),
        (ScreenplayElementKind.ACTION, "房间很安静。"),
        (ScreenplayElementKind.CHARACTER, "小明"),
        (ScreenplayElementKind.PARENTHETICAL, "（低声）"),
        (ScreenplayElementKind.DIALOGUE, "我们该走了。"),
    ]
    actual = [
        (element.kind, normalized.text[element.start : element.end])
        for scene in normalized.scenes
        for element in scene.elements
    ]

    assert actual == expected


def test_tabular_docx_dialogue_is_split_without_changing_source_text() -> None:
    normalized = normalize_screenplay("外景 - 夜\n  小明\t  你好。\n")

    assert [element.kind for element in normalized.scenes[0].elements] == [
        ScreenplayElementKind.HEADING,
        ScreenplayElementKind.CHARACTER,
        ScreenplayElementKind.DIALOGUE,
    ]
    speaker, dialogue = normalized.scenes[0].elements[1:]
    assert normalized.text[speaker.start : speaker.end] == "小明"
    assert normalized.text[dialogue.start : dialogue.end] == "你好。"
    assert normalized.text == "外景 - 夜\n  小明\t  你好。\n"


def test_fountain_and_screenplay_control_lines_keep_their_typed_kinds() -> None:
    normalized = normalize_screenplay(
        "INT. ROOM - NIGHT\n"
        "# Act One\n"
        "= The story begins.\n"
        "CLOSE ON the key.\n"
        "CUT TO:\n"
        "The door opens.\n"
    )

    actual = [
        (element.kind, normalized.text[element.start : element.end])
        for element in normalized.scenes[0].elements
    ]

    assert actual == [
        (ScreenplayElementKind.HEADING, "INT. ROOM - NIGHT"),
        (ScreenplayElementKind.SECTION, "# Act One"),
        (ScreenplayElementKind.SYNOPSIS, "= The story begins."),
        (ScreenplayElementKind.SHOT, "CLOSE ON the key."),
        (ScreenplayElementKind.TRANSITION, "CUT TO:"),
        (ScreenplayElementKind.ACTION, "The door opens."),
    ]


def test_structure_element_budget_rejects_metadata_amplification() -> None:
    source = "INT. ROOM - DAY\n" + "one action line\n" * 20_000

    with pytest.raises(ValueError, match="structure element limit"):
        normalize_screenplay(source)
