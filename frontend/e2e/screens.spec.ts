import { test } from "@playwright/test";

// Review screenshots of key screens in light and dark mode (runs only when E2E_SHOTS is set).
const SHOTS = process.env.E2E_SHOTS;
const API = "http://localhost:8000";

for (const scheme of ["light", "dark"] as const) {
  test(`screens in ${scheme} mode`, async ({ browser }) => {
    test.skip(!SHOTS, "screenshots only");
    const ctx = await browser.newContext({ colorScheme: scheme });
    const page = await ctx.newPage();
    for (const mode of ["together", "two_devices"]) {
      const res = await page.request.post(`${API}/api/session`, { data: { language: "en", district: "Mysuru",
        learner_education: "class_10", learner_interests: [], top_concerns: [], helper_mode: false, consent_given: true,
        participation_mode: mode } });
      const { session_id, family_code } = await res.json();
      await page.addInitScript(([id, m, code]) => {
        sessionStorage.setItem("samvaad.session", JSON.stringify(id));
        sessionStorage.setItem("samvaad.profile", JSON.stringify({ language: "en", participation_mode: m, role: "learner",
          family_code: code, learner_interests: [], top_concerns: [], helper_mode: false }));
        sessionStorage.setItem("samvaad.readAloud", "false");
        localStorage.setItem("samvaad.lite", "1");
      }, [session_id, mode, family_code]);
      await page.goto("/alignment");
      await page.waitForTimeout(800);
      if (mode === "together") {
        for (const v of ["Earning soon", "Safety"]) await page.getByRole("region", { name: "Learner", exact: true }).getByRole("checkbox", { name: v }).click();
        await page.getByRole("region", { name: "Parent", exact: true }).getByRole("checkbox", { name: "Safety" }).click();
      }
      await page.screenshot({ path: `${SHOTS}/align-${mode}-${scheme}.png`, fullPage: true });
    }
    await page.goto("/join?code=12");
    await page.screenshot({ path: `${SHOTS}/join-${scheme}.png`, fullPage: true });
    await ctx.close();
  });
}
