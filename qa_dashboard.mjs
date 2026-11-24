export default async function run(page, ui) {
  // Login
  await page.goto("http://127.0.0.1:5000/login");
  await page.fill('input[name="username"]', "qa_temp_admin");
  await page.fill('input[name="password"]', "QaTest@12345");
  await page.click('button[type="submit"]');
  await page.waitForLoadState("networkidle");

  const url = page.url();

  // Dashboard loaded?
  const title = await page.title();
  const banner = await page.locator(".welcome-banner").count();
  const statCards = await page.locator(".stat-card").count();
  const chartCanvas = await page.locator("#requestChart").count();
  const quickActions = await page.locator(".quick-action").count();
  const notifItems = await page.locator(".notif-item").count();
  const recentRows = await page.locator(".recent-table tbody tr").count();
  const accountItems = await page.locator(".account-item").count();
  const sidebarLinks = await page.locator(".sidebar-link").count();
  const searchInput = await page.locator(".topbar-search input").count();
  const bell = await page.locator(".topbar-bell").count();
  const profileDropdown = await page.locator(".topbar-profile").count();

  // Screenshot
  await page.screenshot({ path: "dashboard_check.png", fullPage: true });

  return {
    url,
    title,
    banner,
    statCards,
    chartCanvas,
    quickActions,
    notifItems,
    recentRows,
    accountItems,
    sidebarLinks,
    searchInput,
    bell,
    profileDropdown,
  };
}
