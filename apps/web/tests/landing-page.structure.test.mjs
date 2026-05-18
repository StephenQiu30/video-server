import { readFileSync } from "node:fs";
import { test, describe } from "node:test";
import assert from "node:assert/strict";

const landingSource = readFileSync(new URL("../src/pages/LandingPage.tsx", import.meta.url), "utf8");
const headerSource = readFileSync(new URL("../src/components/layout/Header.tsx", import.meta.url), "utf8");

describe("Landing page structure", () => {
  test("contains essential landing sections", () => {
    const expectedIds = ["hero", "features", "proof", "pricing", "faq", "final-cta"];

    expectedIds.forEach((id) => {
      assert.match(
        landingSource,
        new RegExp(`id=\"${id}\"`),
        `LandingPage should contain section id=${id}`
      );
    });
  });

  test("keeps focused SaaS information architecture", () => {
    assert.match(landingSource, /价值主张|一站式|智能/i);
    assert.match(landingSource, /立即开始|开始体验|开启下载工作流/i);
    assert.match(landingSource, /功能亮点|核心功能|特性/i);
    assert.match(landingSource, /社会证明|用户评价|用户反馈/i);
    assert.match(landingSource, /常见问题|FAQ|疑问/i);
  });

  test("hero should expose desktop and mobile entry CTAs", () => {
    const ctaMatches = landingSource.match(/aria-label=\"[^\"]*开始[^\"]*\"/g) || [];
    assert.ok(ctaMatches.length >= 1, "expected at least one meaningful CTA aria-label in LandingPage");
  });

  test("header anchors should map to landing sections", () => {
    const headerAnchors = ["#features", "#proof", "#pricing", "#faq"];
    headerAnchors.forEach((anchor) => {
      const escapedAnchor = anchor.replace(/#/g, "\\#");
      const anchorPattern = new RegExp(`href=\\\"${escapedAnchor}\\\"|href:\\s*[\"']${escapedAnchor}[\"']`);
      assert.match(
        headerSource,
        anchorPattern,
        `Header should include anchor link ${anchor}`
      );
    });
  });
});
