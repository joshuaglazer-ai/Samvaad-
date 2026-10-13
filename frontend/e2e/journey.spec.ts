import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

// The app's own translation files, so the test always clicks exactly what users see.
const load = (l: string) => JSON.parse(readFileSync(new URL(`../src/i18n/${l}.json`, import.meta.url), "utf-8"));
const [en, kn, hi, te] = ["en", "kn", "hi", "te"].map(load);

const SHOTS = process.env.E2E_SHOTS; // optional folder for screenshots
const DICTS = { en, kn, hi, te } as const;
const NATIVE = { en: "English", kn: "ಕನ್ನಡ", hi: "हिन्दी", te: "తెలుగు" } as const;
type Lang = keyof typeof DICTS;
const API = "http://localhost:8000";
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

async function shot(page: Page, name: string) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

/** The whole family journey with taps only — no typing (PS outcome 4). Labels come from the app's own i18n files. */
async function journey(page: Page, lang: Lang) {
  const d = DICTS[lang];
  const values = Object.values(d.alignment.values);
  // Sector and trade names come from the API (never hard-coded), in this language.
  const sectors = await (await page.request.get(`${API}/api/sectors?language=${lang}`)).json();
  const trades = await (await page.request.get(`${API}/api/trades?language=${lang}&sector=${sectors[0].slug}`)).json();

  await page.addInitScript(() => {
    sessionStorage.setItem("samvaad.readAloud", "false");
    localStorage.setItem("samvaad.lite", "1");
  });
  await page.goto("/");
  await page.getByRole("radio", { name: NATIVE[lang], exact: true }).click();
  await shot(page, `${lang}-01-landing`);
  await page.getByRole("button", { name: new RegExp(d.landing.start) }).click();

  // onboarding
  await page.getByRole("radio", { name: NATIVE[lang], exact: true }).click();
  await page.getByRole("button", { name: d.consent.agree }).click();
  await page.getByRole("radio", { name: new RegExp(d.mode.together) }).click();
  await page.getByRole("radio", { name: d.districts.Mysuru }).click();
  await page.getByRole("radio", { name: d.education.class_10 }).click();
  // Learner's goal: Browse ideas → a sector → a trade → confirm (taps only).
  await page.getByRole("radio", { name: new RegExp(esc(d.goal.browse)) }).click();
  await page.getByRole("radio", { name: sectors[0].name, exact: true }).click();
  await page.getByRole("radio", { name: trades[0].name, exact: true }).click();
  await expect(page.getByTestId("goal-understood")).toHaveText(trades[0].name);
  await page.getByRole("button", { name: d.goal.yesRight }).click();
  // Parent's hope (answering together): "Not sure yet" picture questions → a suggestion → confirm.
  await expect(page.getByTestId("goal-parent")).toBeVisible();
  await page.getByRole("radio", { name: new RegExp(esc(d.goal.notSure)) }).click();
  for (const yes of [false, true, false, false, false]) {
    await page.getByRole("radio", { name: yes ? d.goal.yes : d.goal.notReally, exact: true }).click();
  }
  await page.getByRole("radio", { name: d.goal.nearHome }).click();
  await expect(page.getByText(d.goal.suggestionsNote)).toBeVisible();
  await page.getByTestId("goal-parent").getByRole("radio").first().click();
  await page.getByRole("button", { name: d.goal.yesRight }).click();
  await page.getByRole("checkbox", { name: d.concerns.income, exact: true }).click();
  await shot(page, `${lang}-02-concerns`);
  await page.getByRole("button", { name: d.app.next }).click();
  await page.getByRole("button", { name: d.app.skip }).click();
  await page.getByRole("radio", { name: d.onboarding.helperNo }).click();
  await page.getByRole("button", { name: d.onboarding.finish }).click();

  // alignment "together": both rows on one screen, saved together (no passing the phone)
  for (const [who, order] of [[d.alignment.learner, values], [d.alignment.parent, [...values].reverse()]] as const) {
    const row = page.getByRole("region", { name: who, exact: true });
    for (const v of order) await row.getByRole("checkbox", { name: v }).click();
  }
  await page.getByRole("button", { name: d.family.saveBoth }).click();
  // Different hopes are shown kindly, side by side.
  await expect(page.getByTestId("goal-compare")).toContainText(d.goal.lookAtBoth);
  await expect(page.getByTestId("goal-learner-label")).toHaveText(trades[0].name);
  await shot(page, `${lang}-03-alignment`);
  await page.getByRole("button", { name: d.alignment.continue }).click();

  // pre mood
  await page.getByRole("radio", { name: d.mood.faces["4"] }).first().click();
  await page.getByRole("button", { name: d.mood.continue }).click();

  // chat via quick replies only
  await page.getByRole("button", { name: d.chat.starter1 }).click();
  await expect(page.getByText(d.app.demoLabel).first()).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("article").first()).toContainText("₹");
  await page.getByRole("button", { name: d.chat.starter3 }).click();
  await expect(page.locator("ol[aria-label]").last()).toBeVisible({ timeout: 15_000 });
  await shot(page, `${lang}-04-chat`);
  await page.getByRole("button", { name: d.chat.finish }).click();

  // post mood → summary
  await page.getByRole("radio", { name: d.mood.faces["4"] }).last().click();
  await page.getByRole("button", { name: d.mood.continue }).click();
  await expect(page.getByRole("heading", { name: d.summary.title })).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("img[alt]").first()).toBeVisible(); // QR code
  await shot(page, `${lang}-05-summary`);
}

for (const lang of ["en", "kn", "hi", "te"] as const) {
  test(`full journey in ${NATIVE[lang]} without typing`, async ({ page }) => {
    await journey(page, lang);
  });
}

test("header language menu switches between all four languages", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("samvaad.lite", "1"));
  await page.goto("/");
  for (const lang of ["hi", "te", "kn", "en"] as const) {
    await page.getByRole("button", { name: /^(Language|ಭಾಷೆ|भाषा|భాష):/ }).click();
    await page.getByRole("menuitemradio", { name: new RegExp(NATIVE[lang]) }).click();
    await expect(page.locator("html")).toHaveAttribute("lang", lang);
    await expect(page.getByRole("button", { name: new RegExp(DICTS[lang].landing.start) })).toBeVisible();
  }
});

test("Lite mode renders no WebGL canvas", async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: "reduce" });
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page.getByRole("button", { name: /^Lite$/ })).toHaveAttribute("aria-pressed", "true");
  await page.waitForTimeout(800);
  expect(await page.locator("canvas").count()).toBe(0);
  await ctx.close();
});

test("3D sky renders when Lite mode is off", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("samvaad.lite", "0"));
  await page.goto("/");
  await expect(page.locator("canvas")).toHaveCount(1, { timeout: 10_000 });
  await shot(page, "landing-3d");
});
