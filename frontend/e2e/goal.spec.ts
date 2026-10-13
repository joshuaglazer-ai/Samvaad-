import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

// Update 3: "What would you like to do or become?" — say/type it, browse, or not sure yet; then confirm.
const load = (l: string) => JSON.parse(readFileSync(new URL(`../src/i18n/${l}.json`, import.meta.url), "utf-8"));
const [en, hi] = ["en", "hi"].map(load);
const API = "http://localhost:8000";
const SHOTS = process.env.E2E_SHOTS;
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

async function toGoalStep(page: Page, d = en, native = "English", mode = d.mode.learner_only) {
  await page.addInitScript(() => { sessionStorage.setItem("samvaad.readAloud", "false"); localStorage.setItem("samvaad.lite", "1"); });
  await page.goto("/start");
  await page.getByRole("radio", { name: native, exact: true }).click();
  await page.getByRole("button", { name: d.consent.agree }).click();
  await page.getByRole("radio", { name: new RegExp(esc(mode)) }).click();
  await page.getByRole("radio", { name: d.districts.Dharwad }).click();
  await page.getByRole("radio", { name: d.education.class_10 }).click();
  await expect(page.getByRole("heading", { name: d.goal.question })).toBeVisible();
}

async function say(page: Page, text: string, d = en) {
  await page.getByRole("radio", { name: new RegExp(esc(d.goal.say)) }).click();
  await page.getByLabel(d.goal.inputLabel).fill(text);
  await page.getByRole("button", { name: d.goal.check }).click();
}

test("say it (typed, romanised Hindi): closest database trade, confirmed", async ({ page }) => {
  await toGoalStep(page, hi, "हिन्दी");
  await expect(page.getByRole("radio", { name: new RegExp(esc(hi.goal.say)) })).toBeVisible();
  await say(page, "bijli mistri", hi);
  await expect(page.getByTestId("goal-understood")).toHaveText("bijli mistri");
  await expect(page.getByText(hi.goal.closest)).toBeVisible();
  const option = page.getByRole("radio", { name: /इलेक्ट्रीशियन/ });
  await expect(option).toHaveAttribute("aria-checked", "true");
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/goal-confirm-hi.png`, fullPage: true });
  await page.getByRole("button", { name: hi.goal.yesRight }).click();
  await expect(page.getByRole("heading", { name: hi.onboarding.concerns })).toBeVisible();
  await page.getByRole("button", { name: hi.app.back }).click();
  await expect(page.getByTestId("goal-saved-learner")).toHaveText("इलेक्ट्रीशियन");
});

test("say it: an unknown goal is kept as said, with a kind no-data line and no invented trade", async ({ page }) => {
  await toGoalStep(page);
  await say(page, "drone pilot");
  await expect(page.getByText(en.goal.unknownMsg)).toBeVisible();
  await expect(page.getByText(en.goal.closest)).toHaveCount(0);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/goal-unknown-en.png`, fullPage: true });
  await page.getByRole("button", { name: en.goal.saveGoal }).click();
  await page.getByRole("button", { name: en.app.back }).click();
  await expect(page.getByTestId("goal-saved-learner")).toHaveText("drone pilot");
});

test("say it: a degree career is respected; related skill options come from the database", async ({ page }) => {
  await toGoalStep(page);
  await say(page, "I want to be a doctor");
  await expect(page.getByText(en.goal.degreeMsg)).toBeVisible();
  await page.getByRole("button", { name: en.goal.showRelated }).click();
  const healthcare = await (await page.request.get(`${API}/api/trades?language=en&sector=healthcare`)).json();
  for (const tr of healthcare) await expect(page.getByRole("radio", { name: tr.name, exact: true })).toBeVisible();
});

test("browse: search works in any language and leads to the confirm step", async ({ page }) => {
  await toGoalStep(page);
  await page.getByRole("radio", { name: new RegExp(esc(en.goal.browse)) }).click();
  const sectors = await (await page.request.get(`${API}/api/sectors?language=en`)).json();
  for (const s of sectors) await expect(page.getByRole("radio", { name: s.name, exact: true })).toBeVisible();
  await page.getByRole("searchbox").fill("ಸೋಲಾರ್");
  const hits = page.getByRole("radio");
  await expect(hits).toHaveCount(1);
  await hits.first().click();
  await expect(page.getByRole("button", { name: en.goal.yesRight })).toBeVisible();
  await page.getByRole("button", { name: en.goal.chooseDifferent }).click();
  await page.getByRole("searchbox").fill("zzzz");
  await expect(page.getByText(en.goal.noResults)).toBeVisible();
});

test("not sure yet: suggestions are marked as suggestions, and deciding later is fine", async ({ page }) => {
  await toGoalStep(page);
  await page.getByRole("radio", { name: new RegExp(esc(en.goal.notSure)) }).click();
  for (const yes of [true, false, true, false, false]) {
    await page.getByRole("radio", { name: yes ? en.goal.yes : en.goal.notReally, exact: true }).click();
  }
  await page.getByRole("radio", { name: en.goal.openToMove }).click();
  await expect(page.getByText(en.goal.suggestionsNote)).toBeVisible();
  const cards = page.getByTestId("goal-learner").getByRole("radio");
  expect(await cards.count()).toBeGreaterThan(0);
  expect(await cards.count()).toBeLessThanOrEqual(3);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/goal-quiz-en.png`, fullPage: true });
  await page.getByRole("button", { name: en.goal.decideLater }).click();
  await expect(page.getByRole("heading", { name: en.onboarding.concerns })).toBeVisible();
});

for (const theme of ["light", "dark"] as const) {
  test(`goal screens have no serious a11y violations (${theme})`, async ({ page }) => {
    const { default: AxeBuilder } = await import("@axe-core/playwright");
    const scan = async () => {
      const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      expect(r.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => v.id)).toEqual([]);
    };
    await page.addInitScript((t) => localStorage.setItem("samvaad.theme", t), theme);
    await toGoalStep(page);
    await scan();
    await page.getByRole("radio", { name: new RegExp(esc(en.goal.browse)) }).click();
    await expect(page.getByRole("heading", { name: en.goal.sectorsTitle })).toBeVisible();
    await scan();
    await page.getByRole("button", { name: en.goal.otherWays }).click();
    await say(page, "bike mechanic");
    await expect(page.getByText(en.goal.closest)).toBeVisible();
    await scan();
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/goal-confirm-${theme}.png`, fullPage: true });
  });
}

test("change goal from chat: an unmatched goal gets a kind reply, a new goal is used next", async ({ page }) => {
  const res = await page.request.post(`${API}/api/session`, { data: { language: "en", district: "Mysuru",
    learner_education: "class_10", consent_given: true, participation_mode: "learner_only",
    aspiration: { text: "drone pilot", language: "en", source: "text" } } });
  const { session_id } = await res.json();
  await page.addInitScript((id) => {
    sessionStorage.setItem("samvaad.readAloud", "false");
    localStorage.setItem("samvaad.lite", "1");
    sessionStorage.setItem("samvaad.session", JSON.stringify(id));
    sessionStorage.setItem("samvaad.profile", JSON.stringify({ language: "en", participation_mode: "learner_only", role: "learner",
      district: "Mysuru", learner_education: "class_10", learner_interests: [], top_concerns: [], helper_mode: false }));
  }, session_id);
  await page.goto("/chat");
  await expect(page.getByTestId("chat-goal-label")).toHaveText("drone pilot");
  await page.getByRole("button", { name: "How much can I earn?" }).click();
  await expect(page.getByText(/I don't have reliable information on this yet/)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("button", { name: "Show other options" })).toBeVisible();

  await page.getByRole("button", { name: en.goal.change }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("radio", { name: new RegExp(esc(en.goal.say)) }).click();
  await dialog.getByLabel(en.goal.inputLabel).fill("wiring work");
  await dialog.getByRole("button", { name: en.goal.check }).click();
  await dialog.getByRole("button", { name: en.goal.yesRight }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByTestId("chat-goal-label")).toHaveText("Wireman");
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/chat-goal.png`, fullPage: true });
  await page.getByLabel(/Type your question|question/i).first().fill("How much can I earn?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator("article").first()).toContainText("₹", { timeout: 15_000 });
});
