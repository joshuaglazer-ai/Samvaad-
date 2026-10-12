import { test } from "@playwright/test";
// Viewport-sized screenshots for visual review (not assertions). Run with E2E_SHOTS set.
test("viewport chat screenshot", async ({ page }) => {
  test.skip(!process.env.E2E_SHOTS, "screenshots only");
  await page.addInitScript(() => { sessionStorage.setItem("samvaad.readAloud", "false"); localStorage.setItem("samvaad.lite", "1"); });
  const res = await page.request.post("http://localhost:8000/api/session", { data: { language: "en", district: "Kalaburagi",
    learner_education: "class_10", learner_interests: ["vehicles"], top_concerns: ["income"], helper_mode: true, consent_given: true } });
  const { session_id } = await res.json();
  await page.addInitScript((id) => sessionStorage.setItem("samvaad.session", JSON.stringify(id)), session_id);
  await page.addInitScript(() => sessionStorage.setItem("samvaad.profile", JSON.stringify({ language: "en", learner_interests: [], top_concerns: [], helper_mode: true })));
  await page.goto("/chat");
  await page.getByRole("button", { name: "How much can I earn?" }).click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${process.env.E2E_SHOTS}/vp-chat.png` });
  await page.getByRole("button", { name: "Talk to a counsellor" }).first().click();
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${process.env.E2E_SHOTS}/vp-escalation.png`, fullPage: true });
  await page.goto("/");
  await page.screenshot({ path: `${process.env.E2E_SHOTS}/vp-landing.png` });
});
