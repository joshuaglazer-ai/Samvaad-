import { expect, test } from "@playwright/test";

const PIN = process.env.E2E_COUNSELLOR_PIN ?? "change-me";
const API = "http://localhost:8000";

/** A sensitive question in chat creates a case that appears in the console with its summary,
 * and family ↔ counsellor live chat works across two browser tabs. */
test("escalation reaches the counsellor console and live chat works", async ({ browser }) => {
  // Counsellor tab (online first, so the family sees "A counsellor will join shortly")
  const cCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const counsellor = await cCtx.newPage();
  await counsellor.goto("/counsellor");
  await counsellor.getByLabel("Enter counsellor PIN").fill(PIN);
  await counsellor.getByRole("button", { name: "Open console" }).click();
  await expect(counsellor.getByRole("heading", { name: /Waiting families/ })).toBeVisible();

  // Family tab
  const fCtx = await browser.newContext();
  const family = await fCtx.newPage();
  const res = await family.request.post(`${API}/api/session`, { data: { language: "en", district: "Kalaburagi",
    learner_education: "class_10", learner_interests: ["helping"], top_concerns: ["safety"], helper_mode: false, consent_given: true } });
  const { session_id } = await res.json();
  await family.addInitScript((id) => {
    sessionStorage.setItem("samvaad.session", JSON.stringify(id));
    sessionStorage.setItem("samvaad.readAloud", "false");
    localStorage.setItem("samvaad.lite", "1");
  }, session_id);
  await family.goto("/chat");
  await family.getByLabel("Type your question (optional)").fill("Is night duty safe for my daughter in a hospital?");
  await family.getByRole("button", { name: "Send" }).click();
  await expect(family.getByText("A counsellor will join shortly.").last()).toBeVisible({ timeout: 15_000 });
  await family.getByRole("button", { name: "Wait for live chat" }).click();

  // Case appears in the console with trigger and summary
  const caseBtn = counsellor.getByRole("button", { name: /sensitive topic/ }).last();
  await expect(caseBtn).toBeVisible({ timeout: 10_000 });
  await caseBtn.click();
  await expect(counsellor.getByText(/District: Kalaburagi/)).toBeVisible();
  await expect(counsellor.getByText(/Escalated because: A sensitive topic/)).toBeVisible();
  await counsellor.getByRole("button", { name: "Assign to me" }).click();

  // Counsellor → family
  await counsellor.getByLabel("Write a reply").fill("Namaskara. I am a counsellor. I am here to help.");
  await counsellor.getByRole("button", { name: "Send" }).click();
  await expect(family.getByText("Namaskara. I am a counsellor. I am here to help.")).toBeVisible({ timeout: 10_000 });
  await expect(family.getByText("A counsellor has joined.")).toBeVisible({ timeout: 10_000 });

  // Family → counsellor
  await family.locator("#esc-draft").fill("Thank you. We worry about night shifts.");
  await family.getByRole("button", { name: "Send" }).last().click();
  await expect(counsellor.getByText("Thank you. We worry about night shifts.").first()).toBeVisible({ timeout: 10_000 });

  if (process.env.E2E_SHOTS) {
    await counsellor.screenshot({ path: `${process.env.E2E_SHOTS}/counsellor.png`, fullPage: true });
    await family.screenshot({ path: `${process.env.E2E_SHOTS}/family-live.png`, fullPage: true });
  }

  await counsellor.getByRole("button", { name: "Mark resolved" }).click();
  await cCtx.close();
  await fCtx.close();
});

test("offline: callback is offered first and stored", async ({ page }) => {
  const res = await page.request.post(`${API}/api/session`, { data: { language: "kn", district: "Mysuru",
    learner_education: "class_10", learner_interests: [], top_concerns: ["cost"], helper_mode: false, consent_given: true } });
  const { session_id } = await res.json();
  await page.addInitScript((id) => {
    sessionStorage.setItem("samvaad.session", JSON.stringify(id));
    sessionStorage.setItem("samvaad.readAloud", "false");
    localStorage.setItem("samvaad.lite", "1");
    localStorage.setItem("samvaad.lang", "kn");
  }, session_id);
  await page.goto("/chat");
  await page.getByRole("button", { name: "ಸಲಹೆಗಾರರೊಂದಿಗೆ ಮಾತನಾಡಿ" }).click();
  await expect(page.getByText("ಈಗ ಯಾವ ಸಲಹೆಗಾರರೂ ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ಇಲ್ಲ", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "ಮರಳಿ ಕರೆ ಕೇಳಿ" }).click();
  await page.getByLabel("ಫೋನ್ ಸಂಖ್ಯೆ").fill("9876543210");
  await page.getByRole("button", { name: /ಸಂಜೆ/ }).click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "ಕರೆ ಕೇಳಿ" }).click();
  await expect(page.getByText("ಧನ್ಯವಾದ. ಸಲಹೆಗಾರರು ನಿಮಗೆ ಕರೆ ಮಾಡುತ್ತಾರೆ.")).toBeVisible();
});
