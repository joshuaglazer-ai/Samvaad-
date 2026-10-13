import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

const load = (l: string) => JSON.parse(readFileSync(new URL(`../src/i18n/${l}.json`, import.meta.url), "utf-8"));
const [en, kn] = ["en", "kn"].map(load);

const SHOTS = process.env.E2E_SHOTS;

/** "Parent joins on their own phone": the learner's phone shows a code, the parent joins on a second phone in a
 * different language, both arrange cards on their own phones, and each phone's questions are tagged by device. */
test("two-phone family session: join with code, own language, shared result", async ({ browser }) => {
  const learnerCtx = await browser.newContext();
  const learner = await learnerCtx.newPage();
  await learner.addInitScript(() => { sessionStorage.setItem("samvaad.readAloud", "false"); localStorage.setItem("samvaad.lite", "1"); localStorage.setItem("samvaad.lang", "en"); });
  await learner.goto("/");
  await learner.getByRole("button", { name: /Start together/ }).click();
  await learner.getByRole("radio", { name: "English" }).click();
  await learner.getByRole("button", { name: "I agree, continue" }).click();
  await learner.getByRole("radio", { name: /Parent joins on their own phone/ }).click();
  await learner.getByRole("radio", { name: "Kalaburagi" }).click();
  await learner.getByRole("radio", { name: "Class 10 (SSLC)" }).click();
  // Learner's goal, typed in their own words; the closest database trade is confirmed.
  await learner.getByRole("radio", { name: new RegExp(en.goal.say) }).click();
  await learner.getByLabel(en.goal.inputLabel).fill("bike mechanic");
  await learner.getByRole("button", { name: en.goal.check }).click();
  await learner.getByRole("button", { name: en.goal.yesRight }).click();
  // No parent hope here: on two phones the parent answers on their own phone.
  await expect(learner.getByTestId("goal-parent")).toHaveCount(0);
  await learner.getByRole("checkbox", { name: "Safety", exact: true }).click();
  await learner.getByRole("button", { name: "Next" }).click();
  await learner.getByRole("button", { name: "Skip" }).click();
  await learner.getByRole("button", { name: "Continue" }).click();

  // The learner's phone shows the family code, and only the learner's row of cards.
  const codeText = (await learner.getByTestId("family-code").textContent())!.trim();
  expect(codeText).toMatch(/^\d{4}$/);
  await expect(learner.getByRole("region", { name: "Parent", exact: true })).toHaveCount(0);
  if (SHOTS) await learner.screenshot({ path: `${SHOTS}/family-learner-code.png`, fullPage: true });

  // Parent's own phone: opens the QR link (code prefilled), picks Kannada.
  const parentCtx = await browser.newContext();
  const parent = await parentCtx.newPage();
  await parent.addInitScript(() => { sessionStorage.setItem("samvaad.readAloud", "false"); localStorage.setItem("samvaad.lite", "1"); });
  await parent.goto(`/join?code=${codeText}`);
  await parent.getByRole("radio", { name: "ಕನ್ನಡ" }).click();
  if (SHOTS) await parent.screenshot({ path: `${SHOTS}/family-parent-join.png`, fullPage: true });
  await parent.getByRole("button", { name: "ಸೇರಿ" }).click();
  await expect(learner.getByText("The parent has joined.")).toBeVisible({ timeout: 10_000 });

  // The parent's own hope for the child, asked on their phone in their language, before the cards.
  await expect(parent.getByText(kn.goal.parentQuestion)).toBeVisible();
  await parent.getByRole("radio", { name: new RegExp(kn.goal.say) }).click();
  await parent.getByLabel(kn.goal.inputLabel).fill("ಡಾಕ್ಟರ್");
  await parent.getByRole("button", { name: kn.goal.check }).click();
  await expect(parent.getByText(kn.goal.degreeMsg)).toBeVisible();
  await parent.getByRole("button", { name: kn.goal.saveGoal }).click();

  // Each arranges their own cards.
  const values = ["Earning soon", "Staying near home", "Respect in the community", "Studying further", "Safety"];
  for (const v of values) await learner.getByRole("checkbox", { name: v }).click();
  await learner.getByRole("button", { name: "Save my order" }).click();
  await expect(learner.getByText("Waiting for the parent to arrange their cards…")).toBeVisible();
  for (const v of ["ಸುರಕ್ಷತೆ", "ಮನೆಯ ಹತ್ತಿರ ಇರುವುದು", "ಊರಿನಲ್ಲಿ ಗೌರವ", "ಮುಂದೆ ಓದುವುದು", "ಬೇಗ ಸಂಪಾದನೆ"]) {
    await parent.getByRole("checkbox", { name: v }).click();
  }
  await parent.getByRole("button", { name: "ನನ್ನ ಕ್ರಮ ಉಳಿಸಿ" }).click();
  await expect(parent.getByText("ನೀವಿಬ್ಬರೂ ಉತ್ತಮವಾದದ್ದನ್ನೇ ಬಯಸುತ್ತೀರಿ.")).toBeVisible();
  await expect(learner.getByText("You both want what is best.")).toBeVisible({ timeout: 10_000 });
  // Learner goal vs parent hope, side by side on both phones, each in its own language.
  await expect(learner.getByTestId("goal-learner-label")).toHaveText("Two-Wheeler Service Technician");
  await expect(learner.getByTestId("goal-parent-label")).toHaveText("ಡಾಕ್ಟರ್");
  await expect(learner.getByTestId("goal-compare")).toContainText(en.goal.lookAtBoth);
  await expect(parent.getByTestId("goal-compare")).toContainText(kn.goal.lookAtBoth);

  // Parent's mood: only the parent is asked on the parent's phone.
  await parent.getByRole("button", { name: "ಮಾತುಕತೆಗೆ ಮುಂದುವರಿಸಿ" }).click();
  await expect(parent.getByRole("radiogroup", { name: "ಕಲಿಯುವವರು" })).toHaveCount(0);
  await parent.getByRole("radio", { name: "ಸ್ವಲ್ಪ ಚಿಂತೆ" }).click();
  await parent.getByRole("button", { name: "ಮುಂದುವರಿಸಿ" }).click();

  // Parent chat: fixed speaker, voice prompt shown, asks in Kannada.
  await expect(parent.getByText("ಪೋಷಕರೇ, ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಮಾತನಾಡಿ ಹೇಳಬಹುದು.")).toBeVisible();
  await expect(parent.getByRole("radio", { name: "ಕಲಿಯುವವರು" })).toHaveCount(0);
  await parent.getByRole("button", { name: "ಎಷ್ಟು ಸಂಪಾದಿಸಬಹುದು?" }).click();
  await expect(parent.getByText("ಡೆಮೊ ಮಾಹಿತಿ — ಪರೀಕ್ಷೆಗೆ ಮಾತ್ರ.").first()).toBeVisible({ timeout: 15_000 });
  if (SHOTS) await parent.screenshot({ path: `${SHOTS}/family-parent-chat.png`, fullPage: true });

  // The learner's phone picks up the parent's question (shared conversation).
  await learner.getByRole("button", { name: "Continue to the conversation" }).click();
  await learner.getByRole("radio", { name: "Hopeful" }).click();
  await learner.getByRole("button", { name: "Continue" }).click();
  await expect(learner.getByText("ಎಷ್ಟು ಸಂಪಾದಿಸಬಹುದು?")).toBeVisible({ timeout: 15_000 });

  await learnerCtx.close();
  await parentCtx.close();
});

test("a wrong family code is refused kindly", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("samvaad.lite", "1"));
  await page.goto("/join");
  for (const d of ["9", "9", "9", "9"]) await page.getByRole("button", { name: d, exact: true }).click();
  await page.getByRole("button", { name: /Join|ಸೇರಿ/ }).click();
  await expect(page.getByRole("alert")).toBeVisible();
});
