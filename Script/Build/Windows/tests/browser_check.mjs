// Build-host browser check. Only GET requests to local services are permitted.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const toolRoot = process.env.PLAYWRIGHT_TOOLS || '/tmp/mongsv-training-ui-tools';
const { chromium } = await import(pathToFileURL(path.join(toolRoot, 'node_modules/playwright/index.mjs')));
const output = path.resolve('Temp/WinBuild/browser');
await fs.mkdir(output, {recursive: true});
const browser = await chromium.launch({headless: true,
  executablePath: process.env.CHROMIUM_PATH || '/home/manager/.cache/ms-playwright/chromium-1187/chrome-linux/chrome',
  args: ['--no-sandbox']});
const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
const external = [], mutations = [], errors = [], requests = [], views = [];
await context.route('**/*', async route => {
  const request = route.request(), url = new URL(request.url());
  if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
    external.push(request.url());
    return route.abort();
  }
  if (request.method() !== 'GET') {
    mutations.push({method: request.method(), url: request.url()});
    return route.abort();
  }
  requests.push(request.url());
  return route.continue();
});
const page = await context.newPage();
page.on('pageerror', error => errors.push(error.message));
try {
  await page.goto('http://127.0.0.1:40831/', {waitUntil: 'networkidle'});
  const runtime = await page.evaluate(() => window.__MON_GSV_RUNTIME__);
  if (runtime?.backendPort !== 40302) throw new Error('Runtime API configuration missing');
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({width, height: 1000});
    for (const label of ['语音合成', '模型训练', '情感配置', '后端测试', '资源管理', '个人配置', '系统设置']) {
      await page.getByRole('navigation', {name: '主导航'}).getByRole('button', {name: label, exact: true}).click();
      await page.waitForTimeout(220);
      const layout = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: innerWidth,
        background: getComputedStyle(document.body).backgroundColor,
        sidebarDisplay: getComputedStyle(document.querySelector('aside')).display,
      }));
      if (layout.documentWidth > width + 1) throw new Error(`Document overflow: ${label} at ${width}`);
      views.push({label, width, ...layout});
      if (width === 1440 && ['语音合成', '模型训练'].includes(label)) {
        await page.screenshot({path: path.join(output, `${label}.png`)});
      }
    }
  }
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`);
  if (external.length) throw new Error(`External requests: ${external.join('; ')}`);
  // Verify a custom launcher port wins over a stale setting from the server edition.
  const relocatedContext = await browser.newContext();
  const relocatedRequests = [];
  await relocatedContext.addInitScript(() => localStorage.setItem('apiConfig', JSON.stringify({baseUrl: 'old-server.invalid', port: 40302})));
  await relocatedContext.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/mon-config.js') return route.fulfill({contentType: 'application/javascript', body: 'window.__MON_GSV_RUNTIME__={backendHost:"127.0.0.1",backendPort:54321};'});
    if (url.port === '54321') {
      relocatedRequests.push(route.request().url());
      return route.fulfill({status: 503, contentType: 'application/json', body: '{"detail":"test service unavailable"}'});
    }
    if (url.port !== '40831' || url.hostname !== '127.0.0.1') throw new Error(`Stale API destination: ${url}`);
    return route.continue();
  });
  const relocatedPage = await relocatedContext.newPage();
  await relocatedPage.goto('http://127.0.0.1:40831/', {waitUntil: 'networkidle'});
  if (relocatedRequests.length === 0) throw new Error('Custom backend port was ignored');
  await relocatedContext.close();
  const report = {success: true, runtime, views, errors, externalRequests: external,
    blockedMutations: mutations, localRequestCount: requests.length, customBackendPortVerified: true};
  await fs.writeFile(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({success: true, viewChecks: views.length, externalRequests: external.length, errors}));
} finally {
  await browser.close();
}
