import pytest
from app.services.analysis_execution.errors import AnalysisArtifactError
from app.services.analysis_execution.models import ScreenplaySceneSource
from app.services.analysis_execution.screenplay_analysis_plan import (
    plan_screenplay_analysis,
)
from app.services.analysis_execution.screenplay_rewrite_plan import (
    plan_screenplay_rewrite,
)


@pytest.mark.parametrize("kind", ["analysis", "rewrite"])
@pytest.mark.parametrize(
    "defect", ["empty", "cr", "nul", "newline", "no_scenes", "duplicate", "gap", "end"]
)
def test_planners_share_source_integrity_boundary(kind, defect):
    text = "ONE\nTWO\n"
    scenes = (
        ScreenplaySceneSource("scene-1", 0, 4),
        ScreenplaySceneSource("scene-2", 4, 8),
    )
    if defect == "empty":
        text = ""
    elif defect == "cr":
        text = "O\rE\nTWO\n"
    elif defect == "nul":
        text = "O\x00E\nTWO\n"
    elif defect == "newline":
        text = text[:-1]
    elif defect == "no_scenes":
        scenes = ()
    elif defect == "duplicate":
        scenes = (scenes[0], ScreenplaySceneSource("scene-1", 4, 8))
    elif defect == "gap":
        scenes = (scenes[0], ScreenplaySceneSource("scene-2", 5, 8))
    else:
        scenes = (scenes[0], ScreenplaySceneSource("scene-2", 4, 7))
    with pytest.raises(AnalysisArtifactError) as failure:
        if kind == "analysis":
            plan_screenplay_analysis(
                text,
                scenes,
                max_chunk_characters=100,
                max_chunk_scenes=10,
                max_chunks=10,
            )
        else:
            plan_screenplay_rewrite(
                text, scenes, max_chunk_characters=100, max_chunks=10
            )
    assert failure.value.code == "artifact_integrity_failed"
