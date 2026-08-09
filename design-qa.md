# Design QA

## Comparison target

- Source visual truth: `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/vercel-home-reference-1440x1024.png`
- Implementation screenshot: `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/video-server-vercel-borderless-1440x1024.png`
- Source and implementation pixels: `1440 × 1024`.
- Implementation CSS viewport: `1440 × 1024`, device scale factor `1`.
- State: desktop home page before an inspection task has started.
- Comparison scope: reproduce Vercel's restrained white canvas, sparse composition, low-separation surfaces, and generous whitespace while retaining the product's Chinese copy, blue brand accent, and Ant Design Pro shell.

## Evidence

- Full view: both source and implementation use a slim top navigation, a white page canvas, a single focused hero, and substantial unoccupied space instead of stacked cards.
- Focused empty-state check: `.content-wrap`, `.ant-pro-card`, and `.ant-empty` all have a count of `0` before inspection starts.
- Fixed layout check: at `1440px`, the native Ant Design Pro content rail is `1152px` wide and centered from `x=144` to `x=1296`.
- Typography: the hero uses a compact high-contrast hierarchy with tightened display tracking; existing system/Ant Design fonts remain readable and consistent with the application shell.
- Spacing and rhythm: hero spacing is independent of a result placeholder, so the page no longer ends in a large bordered block. The input is the only outlined surface in the empty state because its interaction boundary must remain clear.
- Colors and tokens: ProLayout background, header, and PageContainer backgrounds are explicitly white through native layout tokens. The existing project blue is retained only as the brand/action accent.
- Image quality and assets: the existing project logo is preserved; there are no generated, placeholder, or code-drawn assets in the empty state.
- Copy: navigation, hero, placeholder, platform support, loading, validation, and result copy remain product-specific and unchanged except for removing obsolete empty-state instructions.
- Parsed-result check: the result wrapper has no border, background, or shadow. Format choices use borderless filled states and no card shadow while retaining selection affordance.

## Interaction and console checks

- Submitted an invalid URL and received the expected inline validation message.
- Loaded the development inspection state and confirmed that the real media result and format selection render without a surrounding result card.
- Checked a fresh page load after the final changes: no browser console errors were present.

## Comparison history

1. Initial implementation: gray layout gradient and a large bordered empty `ProCard` remained below the hero. Classified as P1 because it directly contradicted the requested empty state and Vercel visual direction.
2. First fix: switched ProLayout/PageContainer to white native tokens, removed the idle result subtree, converted platform pills to plain labels, and made the parsed result wrapper borderless.
3. Result-state review: Ant Card's default shadow remained on format choices. Classified as P2 because it reintroduced card separation inside the result.
4. Final fix: changed format choices to the borderless variant and explicitly removed card shadows. The empty state, parsed state, console, and primary validation interaction then passed.

## Findings

- No actionable P0, P1, or P2 differences remain within the selected Vercel-inspired visual scope.

## Follow-up polish

- The project blue remains intentionally different from Vercel's black CTA so the existing brand is not erased.

final result: passed
