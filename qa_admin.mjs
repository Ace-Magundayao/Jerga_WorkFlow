export default async function run(page, ui) {
  const results = {};

  // Login via the restyled page
  await page.goto("http://127.0.0.1:5000/login");
  await page.fill('input[name="username"]', "qa_temp_admin");
  await page.fill('input[name="password"]', "QaTest@12345");
  await Promise.all([
    page
      .waitForNavigation({ waitUntil: "networkidle", timeout: 15000 })
      .catch(() => null),
    page.press('input[name="password"]', "Enter"),
  ]);
  await page.waitForTimeout(1200);
  const ok = page.locator(".swal2-confirm");
  if (await ok.count()) {
    await ok.click();
    await page.waitForTimeout(300);
  }

  // Screenshot login page (logged out state later; first do pages)
  // Employees page
  await page.goto("http://127.0.0.1:5000/employees/");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
  results.employeesUrl = page.url();
  results.employeesChips = await page.locator(".admin-chip-card").count();
  results.employeesRows = await page.locator(".recent-table tbody tr").count();
  await page.screenshot({ path: "check_employees.png", fullPage: true });

  // ID Verifications page
  await page.goto("http://127.0.0.1:5000/notifications/");
  await page
    .goto("http://127.0.0.1:5000/id-verifications", {
      waitUntil: "domcontentloaded",
    })
    .catch(() => null);
  // Find the real endpoint from the sidebar link
  const href = await page.evaluate(() => {
    const link = Array.from(document.querySelectorAll(".sidebar-link")).find(
      (a) => a.textContent.includes("ID Verifications"),
    );
    return link ? link.getAttribute("href") : null;
  });
  results.verifHref = href;
  if (href) {
    await page.goto("http://127.0.0.1:5000" + href);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(600);
    results.verifCards = await page.locator(".panel-card").count();
    results.verifItems = await page.locator(".verification-item").count();
    await page.screenshot({ path: "check_verifications.png", fullPage: true });
  }

  // Logout then screenshot the login page
  await page.goto("http://127.0.0.1:5000/logout");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(500);
  const ok2 = page.locator(".swal2-confirm");
  if (await ok2.count()) {
    await ok2.click();
    await page.waitForTimeout(300);
  }
  results.loginUrl = page.url();
  await page.screenshot({ path: "check_login.png", fullPage: true });

  return results;
}
