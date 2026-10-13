import { expect, test } from "@playwright/test";

const SHOTS = process.env.E2E_SHOTS;

for (const scheme of ["dark", "light"] as const) {
  test(`live catalogue sky renders in ${scheme} mode (WebGL)`, async ({ browser }) => {
    const ctx = await browser.newContext({ colorScheme: scheme });
    const page = await ctx.newPage();
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    await page.addInitScript(() => localStorage.setItem("samvaad.lite", "0"));
    await page.goto("/");
    await expect(page.locator("canvas")).toHaveCount(1, { timeout: 15_000 });
    await expect(page.locator("html")).toHaveClass(/webgl-sky/);
    await page.waitForTimeout(2500);
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/sky-live-${scheme}.png` });
    expect(errors.filter((e) => /shader|WebGL|THREE/i.test(e))).toEqual([]);
    await ctx.close();
  });

  test(`Lite mode shows the pre-rendered catalogue image (${scheme})`, async ({ browser }) => {
    const ctx = await browser.newContext({ colorScheme: scheme, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    await page.goto("/");
    expect(await page.locator("canvas").count()).toBe(0);
    const bg = await page.locator(".static-stars").evaluate((el) => getComputedStyle(el).backgroundImage);
    expect(bg).toContain(scheme === "dark" ? "stars-dark.png" : "stars-light.png");
    const img = await page.request.get(scheme === "dark" ? "/sky/stars-dark.png" : "/sky/stars-light.png");
    expect(img.status()).toBe(200);
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/sky-lite-${scheme}.png` });
    await ctx.close();
  });
}
