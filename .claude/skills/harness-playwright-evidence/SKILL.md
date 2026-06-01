---
name: harness-playwright-evidence
description: Use when browser or UI work needs end-to-end validation evidence, including Playwright automation, screenshots, traces, video recordings, console logs, or network logs.
license: MIT
---

# Harness Playwright Evidence

## Purpose

Turn UI validation into reviewable evidence. The preferred harness records what the agent actually tested, so humans can inspect the behavior before `Human Review`.

## Use When

- The ticket changes frontend, browser, auth, checkout, dashboard, onboarding, or any UI flow.
- A reviewer needs more than a textual "tested locally" note.
- A failing UI flow needs repeatable traces, console logs, network logs, screenshots, or video.

## Standard Contract

The project should provide or document:

- Playwright install and browser setup command.
- Test command for the target flow.
- Artifact directory for screenshot, trace, video, console logs, and network logs.
- Recording controls for toolchains that support them, such as `video start` and `video stop`.
- A stable way to annotate or name recordings by ticket ID and scenario.

## Flow

1. Start the app with `harness-local-server`.
2. Run the narrowest Playwright scenario that maps to the ticket acceptance criteria.
3. Capture at least one durable artifact for meaningful UI changes: screenshot, trace, or video.
4. Prefer video recording for end-to-end flows; start recording before the user-visible action and stop after the success state.
5. Collect browser console and network logs when debugging failures.
6. Write exact commands, artifact paths, and pass/fail summary into `## Claude Workpad`.
7. Keep artifacts out of commits unless the project explicitly tracks golden evidence.

## Workpad Evidence Shape

```md
### Validation

- [x] Playwright scenario: `<command>` passed.
- [x] Evidence: screenshot `<path>`, trace `<path>`, video `<path>`.

### Notes

- UI evidence covers acceptance criteria 1-3.
```

## Done

- Evidence can be opened by a human without rerunning the task.
- Failure artifacts are preserved before retrying.
- The PR test plan and Linear Workpad point at the same artifacts.
