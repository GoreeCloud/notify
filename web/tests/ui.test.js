import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const path = name => fileURLToPath(new URL("../" + name, import.meta.url));
const html = readFileSync(path("index.html"), "utf8");
const app = readFileSync(path("app.js"), "utf8");
const css = readFileSync(path("styles.css"), "utf8");

test("every wired UI control exists in the HTML document", () => {
  const ids = [...app.matchAll(/\$\("([a-z][a-z0-9-]+)"\)/g)].map(match => match[1]);
  for (const id of new Set(ids)) assert.ok(html.includes('id="' + id + '"'), id);
});
test("no third-party scripts, unsafe HTML injection, or embedded credentials", () => {
  assert.ok(html.includes('Content-Security-Policy'));
  assert.ok(html.includes('script type="module" src="./app.js"'));
  assert.ok(!/<script[^>]+src="https?:\/\//.test(html));
  assert.ok(!/\.innerHTML\s*=|eval\(|new Function\(/.test(app));
  assert.ok(!/localStorage\.setItem\([^\n]*token/i.test(app));
});
test("mobile, reduced-motion, and accessibility foundations exist", () => {
  assert.ok(css.includes("@media(max-width:700px)"));
  assert.ok(css.includes("prefers-reduced-motion"));
  assert.ok(css.includes(":root:not([data-theme])"), "system light palette must precede JavaScript");
  assert.ok(css.includes(":root.theme-ready"), "initial rendering must skip dark/light transitions");
  assert.ok(css.includes(":focus-visible"));
  for (const id of ["feed", "topics", "search", "compose-message", "settings-dialog", "topic-dialog"])
    assert.ok(html.includes('id="' + id + '"'));
  assert.ok(html.includes('aria-live="polite"'));
});
