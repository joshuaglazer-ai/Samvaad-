import { expect, test } from "@playwright/test";

const PIN = process.env.E2E_ADMIN_PIN ?? "change-me";

test("admin dashboard renders every panel from the database", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
  const page = await ctx.newPage();
  await page.addInitScript(() => localStorage.setItem("samvaad.lite", "1"));
  await page.goto("/admin");
  await page.getByLabel("Enter admin PIN").fill(PIN);
  await page.getByRole("button", { name: "Open dashboard" }).click();
  await expect(page.getByText(/Includes simulated demo data/)).toBeVisible({ timeout: 15_000 });
  for (const h of ["Where parental resistance is concentrated", "Concerns by district", "Alignment gaps", "Engagement funnel",
                   "Evidence Gap Radar", "Data quality"]) {
    await expect(page.getByRole("heading", { name: h })).toBeVisible();
  }
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await expect(page.locator(".recharts-surface").first()).toBeVisible();
  // table view toggle
  await page.getByRole("button", { name: "Show table" }).first().click();
  await expect(page.getByRole("columnheader", { name: "Negative parent msgs" })).toBeVisible();
  await page.getByRole("button", { name: "Show chart" }).first().click();
  // filter changes data
  await page.getByLabel("District").selectOption("Kalaburagi");
  await expect(page.getByText(/data requests answered/)).toBeVisible();
  const href = await page.getByRole("link", { name: "Export CSV" }).getAttribute("href");
  expect(href).toContain("district=Kalaburagi");
  const csv = await page.request.get(href!);
  expect(await csv.text()).toContain("district,sessions");
  await page.getByLabel("District").selectOption("");
  await page.waitForTimeout(1500);
  if (process.env.E2E_SHOTS) await page.screenshot({ path: `${process.env.E2E_SHOTS}/admin.png`, fullPage: true });
  await ctx.close();
});
