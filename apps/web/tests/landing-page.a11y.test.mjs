import { readFileSync } from "node:fs";
import { test, describe } from "node:test";
import assert from "node:assert/strict";

const landingSource = readFileSync(new URL("../src/pages/LandingPage.tsx", import.meta.url), "utf8");
const indexSource = readFileSync(new URL("../src/index.css", import.meta.url), "utf8");
const headerSource = readFileSync(new URL("../src/components/layout/Header.tsx", import.meta.url), "utf8");

function hasEmoji(source) {
  return /[\u{1F300}-\u{1F6FF}\u{2600}-\u{27BF}\u{1F900}-\u{1F9FF}]/u.test(source);
}

describe("Landing page accessibility and iOS-style constraints", () => {
  test("no emoji icons used in landing/header implementation", () => {
    assert.equal(hasEmoji(landingSource), false, "LandingPage should avoid emoji icons");
    assert.equal(hasEmoji(headerSource), false, "Header should avoid emoji icons");
  });

  test("supports reduced motion preference", () => {
    assert.match(indexSource, /prefers-reduced-motion|motion-reduce/, "index.css should include reduced-motion support");
  });

  test("interactive controls are at least touch-friendly (class-level intent)", () => {
    const touchHints = ["min-h-[44px]", "min-w-[44px]", "h-11", "h-12", "py-3"];
    const matched = touchHints.some((hint) => landingSource.includes(hint) || headerSource.includes(hint));
    assert.ok(matched, "Landing page should include touch-friendly control sizing classes");
    assert.match(
      headerSource,
      /aria-label=\{isMobileMenuOpen \? "close menu" : "open menu"\}|aria-label=\"(打开导航菜单|关闭导航菜单|open menu|close menu)\"/i,
      "Header menu button should have a11y aria label"
    );
  });

  test("focus feedback should be defined", () => {
    const combinedSource = `${landingSource}\n${headerSource}\n${indexSource}`;
    assert.match(combinedSource, /focus-visible/, "UI implementation should keep focus-visible states");
  });
});
