export default async function run(page, ui) {
  await page.goto("http://127.0.0.1:5000/login");
  await page.fill('input[name="username"]', "qa_temp_admin");
  await page.fill('input[name="password"]', "QaTest@12345");
  await Promise.all([
    page
      .waitForNavigation({ waitUntil: "networkidle", timeout: 15000 })
      .catch(() => null),
    page.press('input[name="password"]', "Enter"),
  ]);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(2000);

  // Dismiss any SweetAlert popup from the login flash
  const okButton = page.locator(".swal2-confirm");
  if (await okButton.count()) {
    await okButton.click();
    await page.waitForTimeout(400);
  }

  await page.screenshot({ path: "dashboard_clean.png", fullPage: true });
  return { url: page.url() };
}
