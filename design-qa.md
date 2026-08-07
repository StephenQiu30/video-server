# Design QA

**Source visual truth**

- `C:\Users\ADMINI~1\AppData\Local\Temp\codex-clipboard-26068c4e-130d-47e0-805c-e5174604df5c.png`
- Source pixels: 2560 × 1380.
- Source state: empty new-download page showing the detached white form card and excessive vertical separation called out by the user.
- Normalization: the browser pane was cropped from the supplied screenshot and resized to 987 × 985 with Lanczos filtering.

**Implementation evidence**

- Desktop empty state: `E:\StephenQiu\Video\tmp\product-design-redesign\final-idle-no-css.png`
- Desktop parsed state: `E:\StephenQiu\Video\tmp\product-design-redesign\final-active-no-css.png`
- Mobile empty state: `E:\StephenQiu\Video\tmp\product-design-redesign\final-mobile-no-css.png`
- Desktop CSS viewport and pixels: 987 × 985 at device scale 1.
- Mobile CSS viewport and pixels: 390 × 844 at device scale 1.
- Full-view comparison: `E:\StephenQiu\Video\tmp\product-design-redesign\no-css-feedback-comparison.png`

**Findings**

- No remaining P0, P1, or P2 findings.
- Fonts and typography: the page uses the native Ant Design type scale, weights and line heights. The title, description, label and form now read as one continuous hierarchy.
- Spacing and layout rhythm: the form moved from the lower half of the viewport to the next content section below the page description. The detached card shell and excessive center gap are gone.
- Colors and visual tokens: the home page does not declare a background color. Browser inspection reports transparent backgrounds for the ProLayout content, PageContainer and ghost page header. Only the existing Ant Design primary color is configured.
- Image quality and asset fidelity: the invalid transparent thumbnail treatment was removed instead of replacing it with placeholder art.
- Copy and content: all prompts remain Chinese and no promotional or compatibility copy was added.
- Accessibility and interaction: the visible input label, accessible submit button, radio row selection and native focus states remain intact.

**Comparison history**

1. The supplied screenshot exposed a P1 composition issue: the title occupied the top content region while the form floated in a separate white card near the lower half of the viewport.
2. Removed the home-page card shell, the custom vertical-centering CSS and all explicit home-page backgrounds. Rebuilt the form with native PageContainer, ProForm, Row, Col and Form.Item components.
3. The first parsed-state pass exposed a P2 empty thumbnail region. Removed that invalid image area and kept the video metadata in a compact native ProCard.
4. Replaced the custom format-picker CSS with the native Ant Design Table and radio row selection.
5. Final desktop and mobile captures show a continuous content flow with no page-level horizontal overflow and no console errors.

**Primary interactions tested**

- Parsed a public BiliBili URL successfully.
- Verified native radio format selection and four-row pagination state.
- Verified empty and parsed layouts at desktop width.
- Verified the mobile empty layout at 390 × 844.
- Checked browser console errors: none.

**Focused region comparison**

- The normalized side-by-side comparison keeps the complete header, page title, description and form readable, so an additional crop was not required.

**Implementation Checklist**

- [x] Removed the detached white form card.
- [x] Removed custom Home and FormatPicker CSS modules.
- [x] Removed the global CSS background overrides.
- [x] Removed the explicit layout-background theme token.
- [x] Rebuilt the page from native Ant Design Pro and Ant Design components.
- [x] Passed desktop, mobile, interaction and console checks.

**Follow-up Polish**

- None required for this scoped correction.

final result: passed
