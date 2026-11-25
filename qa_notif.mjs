export default async function run(page, ui) {
  const results = {};

  // Login as admin
  await page.goto("http://127.0.0.1:5000/login");
  await page.fill('input[name="username"]', "qa_temp_admin");
  await page.fill('input[name="password"]', "QaTest@12345");
  await Promise.all([
    page
      .waitForNavigation({ waitUntil: "networkidle", timeout: 15000 })
      .catch(() => null),
    page.press('input[name="password"]', "Enter"),
  ]);
  await page.waitForTimeout(1000);
  const ok = page.locator(".swal2-confirm");
  if (await ok.count()) {
    await ok.click();
    await page.waitForTimeout(300);
  }

  // Go to ID verifications, verify "ace" (user 5)
  await page.goto("http://127.0.0.1:5000/biometrics/admin/verifications");
  await page.waitForLoadState("networkidle");

  // ace is verified already; use the Remove button to trigger unverify notification
  const removeBtn = page.locator("form[action*='unverify']").first();
  results.removeFound = await removeBtn.count();
  if (results.removeFound) {
    await removeBtn.locator("button").click();
    await page.waitForTimeout(800);
    const confirm = page.locator(".swal2-confirm");
    if (await confirm.count()) {
      await confirm.click();
      await page.waitForTimeout(800);
    }
  }

  // Re-verify to trigger verify notification
  const verifyBtn = page.locator("form[action*='/admin/verify/']").first();
  results.verifyFound = await verifyBtn.count();
  if (results.verifyFound) {
    await verifyBtn.locator("button").click();
    await page.waitForTimeout(800);
    const confirm2 = page.locator(".swal2-confirm");
    if (await confirm2.count()) {
      await confirm2.click();
      await page.waitForTimeout(800);
    }
  }

  // Login as ace (password unknown) — instead check notifications as admin is useless.
  // Just report: notifications created for user 5 will be checked via python afterwards.
  return results;
}
