from app.domain.analysis import (
    ScreenplayAnalysisResult,
    ScreenplayCharacter,
    ScreenplayEvidenceItem,
    ScreenplayGlossaryTerm,
    ScreenplayRewriteChunk,
    ScreenplayRewriteResult,
    ScreenplayScene,
    ScreenplayStructure,
)


def screenplay_analysis_result() -> ScreenplayAnalysisResult:
    act = ScreenplayEvidenceItem(
        id="act-1",
        title="建立",
        description="建立人物目标。",
        evidence_scene_ids=("scene-1",),
    )
    return ScreenplayAnalysisResult(
        language="zh-CN",
        title="剧本分析",
        logline="一位剪辑师必须在首映前找回丢失的结局。",
        synopsis="主人公追查素材并重新理解自己的创作选择。",
        structure=ScreenplayStructure(
            acts=(act,),
            turning_points=(
                ScreenplayEvidenceItem(
                    id="turn-1",
                    title="素材消失",
                    description="外部目标变成明确危机。",
                    evidence_scene_ids=("scene-1",),
                ),
            ),
            pacing_summary="开场紧凑，转折清晰。",
        ),
        characters=(
            ScreenplayCharacter(
                id="character-1",
                name="林舟",
                goal="找回结局",
                conflict="必须面对自己的删改",
                arc="从逃避转向承担",
                evidence_scene_ids=("scene-1",),
            ),
        ),
        scenes=(
            ScreenplayScene(
                id="analysis-scene-1",
                source_scene_id="scene-1",
                purpose="建立危机",
                conflict="时间不足",
                turn="发现备份线索",
                pacing="快速",
                findings=("目标明确",),
            ),
        ),
        dialogue_findings=(),
        strengths=(act,),
        priority_revisions=(),
    )


def screenplay_rewrite_result(
    *, rewritten_text: str = "INT. EDITING ROOM - NIGHT\n\nLIN: We still have time."
) -> ScreenplayRewriteResult:
    return ScreenplayRewriteResult(
        source_language="zh-CN",
        target_language="en-US",
        source_scene_count=1,
        output_scene_count=1,
        glossary=(
            ScreenplayGlossaryTerm(
                source="林舟", target="Lin Zhou", category="character"
            ),
        ),
        chunks=(
            ScreenplayRewriteChunk(
                source_scene_id="scene-1",
                part_no=1,
                source_sha256="a" * 64,
                rewritten_text=rewritten_text,
            ),
        ),
        change_summary=("统一人物名称并保持场景意图。",),
    )
