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
                   "Evidence Gap Radar", "Data quality", "Top aspirations", "Unmatched aspirations",
                   "Learner goal vs parent hope"]) {
    await expect(page.getByRole("heading", { name: h })).toBeVisible();
  }
  await expect(page.locator(".leaflet-container")).toBeVisible();
  // Update 3 panels: words only when 5+ families used them; unmatched goals also show up in the gap radar.
  await expect(page.getByTestId("panel-unmatched").getByRole("row").nth(1)).toBeVisible();
  await expect(page.getByText(/“.+” \(goal\)/).first()).toBeVisible();
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

test("admin trades: manage everyday words without code changes", async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
  const page = await ctx.newPage();
  await page.addInitScript(() => localStorage.setItem("samvaad.lite", "1"));
  await page.goto("/admin");
  await page.getByLabel("Enter admin PIN").fill(PIN);
  await page.getByRole("button", { name: "Open dashboard" }).click();
  await page.getByRole("tab", { name: "Trades" }).click();
  const admin = page.getByTestId("trades-admin");
  await expect(admin.getByRole("row")).toHaveCount(9); // header + 8 seeded trades
  await admin.getByRole("row", { name: /wireman/ }).getByRole("button", { name: "Edit" }).click();
  const editor = page.getByTestId("trade-editor");
  await expect(editor.getByRole("heading", { name: /Edit: Wireman/ })).toBeVisible();
  // Verified/historical stay unavailable in the menu until a source is attached (seed trades have the demo source).
  await expect(editor.getByLabel("Data status")).toHaveValue("demo");

  const word = `e2e wiring word ${Date.now()}`;
  await editor.getByLabel("Word", { exact: true }).fill(word);
  await editor.getByRole("button", { name: "Add word" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();
  await expect(editor.getByText(word)).toBeVisible();
  // Families' words now match it straight away.
  const m = await (await page.request.post("http://localhost:8000/api/aspiration/match", { data: { text: word, language: "en" } })).json();
  expect(m.candidates[0].slug).toBe("wireman");
  if (process.env.E2E_SHOTS) await page.screenshot({ path: `${process.env.E2E_SHOTS}/admin-trades.png`, fullPage: true });
  await editor.getByRole("listitem").filter({ hasText: word }).getByRole("button", { name: "Remove" }).click();
  await expect(editor.getByText(word)).toHaveCount(0);
  await ctx.close();
});

for (const theme of ["light", "dark"] as const) {
  test(`admin trades tab has no serious a11y violations (${theme})`, async ({ browser }) => {
    const { default: AxeBuilder } = await import("@axe-core/playwright");
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
    const page = await ctx.newPage();
    await page.addInitScript((t) => { localStorage.setItem("samvaad.lite", "1"); localStorage.setItem("samvaad.theme", t); }, theme);
    await page.goto("/admin");
    await page.getByLabel("Enter admin PIN").fill(PIN);
    await page.getByRole("button", { name: "Open dashboard" }).click();
    await page.getByRole("tab", { name: "Trades" }).click();
    await page.getByTestId("trades-admin").getByRole("row", { name: /electrician/ }).getByRole("button", { name: "Edit" }).click();
    await expect(page.getByTestId("trade-editor")).toBeVisible();
    const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    const serious = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    if (serious.length) console.log(JSON.stringify(serious.map((v) => ({ id: v.id, nodes: v.nodes.slice(0, 3).map((n) => n.target) }))));
    expect(serious.map((v) => v.id)).toEqual([]);
    await ctx.close();
  });
}
