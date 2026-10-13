import { expect, test, type Page } from "@playwright/test";

const SHOTS = process.env.E2E_SHOTS; // optional folder for screenshots

async function shot(page: Page, name: string) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
}

/** The whole family journey with taps only — no typing (PS outcome 4). */
async function journey(page: Page, lang: "en" | "kn") {
  const L = lang === "en"
    ? { start: /Start together/, agree: "I agree, continue", district: "Mysuru", edu: "Class 10 (SSLC)", interest: "Electricity",
        concern: "Income", next: "Next", skip: "Skip", helperNo: "No, we are using it ourselves", finish: "Continue",
        save: "Save my order", cont: "Continue to the conversation", face: "Hopeful", moodCont: "Continue",
        starter: "How much can I earn?", ladder: "What are the next steps after training?", done: "Finish",
        demo: "Demo data — for testing only.", summary: "Family Summary", together: "Together on this phone",
        learner: "Learner", parent: "Parent", saveBoth: "Save both", values: ["Earning soon", "Staying near home", "Respect in the community", "Studying further", "Safety"] }
    : { start: /ಒಟ್ಟಿಗೆ ಪ್ರಾರಂಭಿಸಿ/, agree: "ಒಪ್ಪುತ್ತೇನೆ, ಮುಂದುವರಿಸಿ", district: "ಮೈಸೂರು", edu: "10ನೇ ತರಗತಿ (SSLC)", interest: "ವಿದ್ಯುತ್",
        concern: "ಆದಾಯ", next: "ಮುಂದೆ", skip: "ಬಿಟ್ಟುಬಿಡಿ", helperNo: "ಇಲ್ಲ, ನಾವೇ ಬಳಸುತ್ತಿದ್ದೇವೆ", finish: "ಮುಂದುವರಿಸಿ",
        save: "ನನ್ನ ಕ್ರಮ ಉಳಿಸಿ", cont: "ಮಾತುಕತೆಗೆ ಮುಂದುವರಿಸಿ", face: "ಭರವಸೆ ಇದೆ", moodCont: "ಮುಂದುವರಿಸಿ",
        starter: "ಎಷ್ಟು ಸಂಪಾದಿಸಬಹುದು?", ladder: "ತರಬೇತಿಯ ನಂತರ ಮುಂದಿನ ಹಂತಗಳೇನು?", done: "ಮುಗಿಸಿ",
        demo: "ಡೆಮೊ ಮಾಹಿತಿ — ಪರೀಕ್ಷೆಗೆ ಮಾತ್ರ.", summary: "ಕುಟುಂಬದ ಸಾರಾಂಶ", together: "ಈ ಫೋನ್‌ನಲ್ಲಿ ಒಟ್ಟಿಗೆ",
        learner: "ಕಲಿಯುವವರು", parent: "ಪೋಷಕರು", saveBoth: "ಎರಡನ್ನೂ ಉಳಿಸಿ", values: ["ಬೇಗ ಸಂಪಾದನೆ", "ಮನೆಯ ಹತ್ತಿರ ಇರುವುದು", "ಊರಿನಲ್ಲಿ ಗೌರವ", "ಮುಂದೆ ಓದುವುದು", "ಸುರಕ್ಷತೆ"] };

  await page.addInitScript(() => {
    sessionStorage.setItem("samvaad.readAloud", "false");
    localStorage.setItem("samvaad.lite", "1");
  });
  await page.goto("/");
  await page.getByRole("button", { name: lang === "kn" ? "ಕನ್ನಡ" : "English", exact: true }).click();
  await shot(page, `${lang}-01-landing`);
  await page.getByRole("button", { name: L.start }).click();

  // onboarding
  await page.getByRole("radio", { name: lang === "kn" ? "ಕನ್ನಡ" : "English" }).click();
  await page.getByRole("button", { name: L.agree }).click();
  await page.getByRole("radio", { name: new RegExp(L.together) }).click();
  await page.getByRole("radio", { name: L.district }).click();
  await page.getByRole("radio", { name: L.edu }).click();
  await page.getByRole("checkbox", { name: L.interest }).click();
  await page.getByRole("button", { name: L.next }).click();
  await page.getByRole("checkbox", { name: L.concern, exact: true }).click();
  await shot(page, `${lang}-02-concerns`);
  await page.getByRole("button", { name: L.next }).click();
  await page.getByRole("button", { name: L.skip }).click();
  await page.getByRole("radio", { name: L.helperNo }).click();
  await page.getByRole("button", { name: L.finish }).click();

  // alignment "together": both rows on one screen, saved together (no passing the phone)
  for (const [who, order] of [[L.learner, L.values], [L.parent, [...L.values].reverse()]] as const) {
    const row = page.getByRole("region", { name: who, exact: true });
    for (const v of order) await row.getByRole("checkbox", { name: v }).click();
  }
  await page.getByRole("button", { name: L.saveBoth }).click();
  await shot(page, `${lang}-03-alignment`);
  await page.getByRole("button", { name: L.cont }).click();

  // pre mood
  await page.getByRole("radio", { name: L.face }).first().click();
  await page.getByRole("button", { name: L.moodCont }).click();

  // chat via quick replies only
  await page.getByRole("button", { name: L.starter }).click();
  await expect(page.getByText(L.demo).first()).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("article").first()).toContainText("₹");
  await page.getByRole("button", { name: L.ladder }).click();
  await expect(page.locator("ol[aria-label]").last()).toBeVisible({ timeout: 15_000 });
  await shot(page, `${lang}-04-chat`);
  await page.getByRole("button", { name: L.done }).click();

  // post mood → summary
  await page.getByRole("radio", { name: L.face }).last().click();
  await page.getByRole("button", { name: L.moodCont }).click();
  await expect(page.getByRole("heading", { name: L.summary })).toBeVisible({ timeout: 15_000 });
  await expect(page.locator("img[alt]").first()).toBeVisible(); // QR code
  await shot(page, `${lang}-05-summary`);
}

test("full journey in English without typing", async ({ page }) => {
  await journey(page, "en");
});

test("full journey in Kannada without typing", async ({ page }) => {
  await journey(page, "kn");
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
