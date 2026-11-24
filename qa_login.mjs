export default async function run(page, ui) {
  await page.goto("http://127.0.0.1:5000/login");
  await page.fill('input[name="username"]', "admin");
  await page.fill('input[name="password"]', "Admin@12345");

  // Use Enter key submit to avoid any intercept weirdness with the button click
  await Promise.all([
    page
      .waitForNavigation({ waitUntil: "networkidle", timeout: 15000 })
      .catch(() => null),
    page.press('input[name="password"]', "Enter"),
  ]);

  await page.waitForLoadState("networkidle");
  const url = page.url();
  const bodyText = await page.evaluate(() =>
    document.body.innerText.slice(0, 400),
  );
  const flashes = await page
    .locator(".flash-data")
    .evaluateAll((els) => els.map((e) => e.dataset.message));

  return { url, bodyText, flashes };
}
