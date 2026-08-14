from app.domain.documents import normalize_screenplay


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
    assert first.scenes[0].id.startswith("scene-0001-")
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
