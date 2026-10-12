import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const SHOTS = process.env.E2E_SHOTS;
const API = "http://localhost:8000";

async function chatSession(page: Page) {
  const res = await page.request.post(`${API}/api/session`, { data: { language: "en", district: "Mysuru",
    learner_education: "class_10", learner_interests: ["electricity"], top_concerns: ["income"], helper_mode: false, consent_given: true } });
  const { session_id } = await res.json();
  await page.addInitScript((id) => {
    sessionStorage.setItem("samvaad.session", JSON.stringify(id));
    sessionStorage.setItem("samvaad.readAloud", "false");
    localStorage.setItem("samvaad.lite", "1");
  }, session_id);
}

test("follows the system dark setting and uses pure black", async ({ browser }) => {
  const ctx = await browser.newContext({ colorScheme: "dark" });
  const page = await ctx.newPage();
  await page.addInitScript(() => localStorage.setItem("samvaad.lite", "1"));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe("rgb(0, 0, 0)");
  await ctx.close();
});

test("manual toggle wins over the system and is remembered", async ({ browser }) => {
  const ctx = await browser.newContext({ colorScheme: "light" });
  const page = await ctx.newPage();
  await page.addInitScript(() => localStorage.setItem("samvaad.lite", "1"));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByRole("button", { name: "Dark" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Light" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await ctx.close();
});

for (const scheme of ["light", "dark"] as const) {
  test(`chat with cards in ${scheme} mode has no serious a11y violations`, async ({ browser }) => {
    const ctx = await browser.newContext({ colorScheme: scheme });
    const page = await ctx.newPage();
    await chatSession(page);
    await page.goto("/chat");
    await page.getByRole("button", { name: "How much can I earn?" }).click();
    await page.getByRole("button", { name: "What are the next steps after training?" }).click();
    await page.waitForTimeout(1500);
    const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    if (serious.length) console.log(JSON.stringify(serious.map((v) => ({ id: v.id, n: v.nodes.slice(0, 3).map((x) => x.target) }))));
    expect(serious).toEqual([]);
    if (SHOTS) {
      await page.screenshot({ path: `${SHOTS}/chat-${scheme}.png`, fullPage: true });
      await page.goto("/");
      await page.screenshot({ path: `${SHOTS}/landing-${scheme}.png` });
    }
    await ctx.close();
  });

  test(`admin dashboard renders in ${scheme} mode`, async ({ browser }) => {
    test.skip(!SHOTS, "screenshots only");
    const ctx = await browser.newContext({ colorScheme: scheme, viewport: { width: 1400, height: 3000 } });
    const page = await ctx.newPage();
    await page.addInitScript(() => { localStorage.setItem("samvaad.lite", "1"); sessionStorage.setItem("samvaad.adminPin", "change-me"); });
    await page.goto("/admin");
    await expect(page.getByRole("heading", { name: "Evidence Gap Radar" })).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(1500);
    // Tall viewport instead of fullPage: Chromium's full-page capture re-emulates the viewport and catches
    // Recharts' ResponsiveContainer mid-remeasure (blank charts in the image only, not on screen).
    await page.screenshot({ path: `${SHOTS}/admin-${scheme}.png` });
    await ctx.close();
  });
}
