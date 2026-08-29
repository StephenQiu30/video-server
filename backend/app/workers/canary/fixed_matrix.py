"""Run the versioned public diagnostics without printing source URLs."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.config import get_settings_for_role
from app.domain.providers import ProviderCanaryOutcome, ProviderCanaryStage
from app.workers.canary.fixed_cases import fixed_public_diagnostic_targets
from app.workers.canary.main import build_runtime


async def _run(providers: frozenset[str], stage: str) -> int:
    runtime = build_runtime(get_settings_for_role("provider-canary"))
    targets = tuple(
        target
        for target in fixed_public_diagnostic_targets()
        if (not providers or target.provider_key in providers)
        and (stage == "all" or target.stage.value == stage)
    )
    results: list[dict[str, object]] = []
    try:
        for target in targets:
            result = await runtime.service.execute(target)
            results.append(
                {
                    "provider_key": result.provider_key,
                    "profile_version": result.profile_version,
                    "stage": result.stage.value,
                    "access_mode": result.access_mode.value,
                    "outcome": result.outcome.value,
                    "stable_error_code": result.stable_error_code,
                    "duration_ms": result.duration_ms,
                }
            )
    finally:
        await runtime.close()
    passed = all(
        item["outcome"] == ProviderCanaryOutcome.SUCCEEDED.value for item in results
    )
    print(
        json.dumps(
            {
                "matrix_complete": passed and bool(results),
                "target_count": len(results),
                "results": results,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return 0 if passed and results else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run fixed public Provider metadata/media diagnostics.",
    )
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument(
        "--stage",
        choices=(
            "all",
            ProviderCanaryStage.METADATA.value,
            ProviderCanaryStage.MEDIA.value,
        ),
        default="all",
    )
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(_run(frozenset(arguments.provider), arguments.stage)))


if __name__ == "__main__":
    main()
