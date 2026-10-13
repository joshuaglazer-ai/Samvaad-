import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Automated WCAG 2.1 A/AA scan of key screens (catches labels, roles, contrast, names).
async function scan(page: import("@playwright/test").Page) {
  const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const serious = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  if (serious.length) console.log(JSON.stringify(serious.map((v) => ({ id: v.id, nodes: v.nodes.slice(0, 3).map((n) => n.target) })), null, 1));
  expect(serious).toEqual([]);
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { sessionStorage.setItem("samvaad.readAloud", "false"); localStorage.setItem("samvaad.lite", "1"); });
});

test("landing has no serious a11y violations", async ({ page }) => {
  await page.goto("/");
  await scan(page);
});

test("onboarding (Kannada) has no serious a11y violations", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("radio", { name: "ಕನ್ನಡ", exact: true }).click();
  await page.getByRole("button", { name: /ಒಟ್ಟಿಗೆ ಪ್ರಾರಂಭಿಸಿ/ }).click();
  await scan(page);
});

test("chat with cards has no serious a11y violations", async ({ page }) => {
  const res = await page.request.post("http://localhost:8000/api/session", { data: { language: "en", district: "Mysuru",
    learner_education: "class_10", learner_interests: ["electricity"], top_concerns: ["income"], helper_mode: false, consent_given: true } });
  const { session_id } = await res.json();
  await page.addInitScript((id) => sessionStorage.setItem("samvaad.session", JSON.stringify(id)), session_id);
  await page.goto("/chat");
  await page.getByRole("button", { name: "How much can I earn?" }).click();
  await page.getByRole("button", { name: "What are the next steps after training?" }).click();
  await page.waitForTimeout(1500);
  await scan(page);
});
