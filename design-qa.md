# Design QA

## Comparison target

- Source visual truth: `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-659a2e96-c895-42d1-b706-be28f986846c.png`
- Implementation screenshot: `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/video-server-balanced-result-1440x1024.png`
- Source pixels: `3372 × 1940`; the source includes Chrome chrome and a larger desktop density.
- Implementation: `1440 × 1024` CSS viewport, captured at `1440 × 1024` pixels.
- State: parsed Bilibili media with eight selectable formats.
- Normalization: comparison uses the parsed-result region and relative column proportions rather than browser chrome or exact source pixels.

## Evidence

- Full view: the former layout placed almost all descriptive content and a tall four-row format grid on the right while leaving the left column as a cover-only surface. The implementation distributes media description to the left and keeps actions on the right.
- Column geometry: both columns are `512px` wide with a `48px` gap inside the native fixed content rail.
- Height balance: the final left media-information column is `401px` high and the right format-action column is `406px` high, a difference of only `5px`.
- Left information: cover, title, provider, duration, and media ID now form one coherent media summary.
- Right information: format count, eight format options, selection state, and the primary download action remain together as one task flow.
- Format density: each format option is `80px` high and uses a compact horizontal label/meta layout, preserving all resolution, container, codec, audio, and FPS information.
- Typography: media title remains the dominant descriptive element; format names remain scannable at compact density; secondary metadata uses the existing Ant Design hierarchy.
- Colors and tokens: the existing white, borderless Vercel-inspired surface and project blue selection/action accent are unchanged.
- Images and assets: the real parsed media cover and existing project assets are used without placeholder or synthetic substitutes.
- Copy: no business information was removed; only its placement and density changed.

## Interaction and responsive checks

- Selected the second format option and verified that `aria-checked` moved from the first option to the second.
- At `820 × 900`, the result changes to one column, retains a `725px` format region, and has no horizontal overflow.
- Build, lint, unit tests, and Ant Design checks passed before final comparison.

## Comparison history

1. Source state: unequal column widths and a right column extending far beyond the cover produced a P1 information-balance issue.
2. First fix: changed the result to equal-width columns and moved title/provider/duration/media ID below the cover. Right-column height was still `528px` versus `401px` on the left, leaving a P2 density mismatch.
3. Final fix: converted each format option to a compact horizontal row and reduced its height. Final measurements are `401px` left and `406px` right with all information preserved.

## Findings

- No actionable P0, P1, or P2 differences remain for the requested information balance.

## Follow-up polish

- None required for this adjustment.

final result: passed
