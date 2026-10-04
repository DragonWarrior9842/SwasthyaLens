// Local acceptance run. Output contains named checks only, never credentials or HTTP bodies.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const path = require('node:path');
assert.equal(process.env.RUN_SUPABASE_INTEGRATION, '1');
assert.equal(process.env.RUN_AI_INTEGRATION, undefined);
const root = path.resolve(__dirname, '../..');
const output=path.join(root,'.cache/qa/phase2'); fs.mkdirSync(output,{recursive:true});
const config = JSON.parse(execFileSync((process.env.QA_PYTHON || path.join(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python')), ['-c', 'import json; from dotenv import dotenv_values; print(json.dumps(dotenv_values(".env.integration")))'], { cwd: path.join(root, 'backend'), encoding: 'utf8' }));
assert.equal(config.DISPOSABLE_TEST_ACCOUNTS_CONFIRMED, '1');
const origin = config.TEST_APP_ORIGIN || 'http://127.0.0.1:5173';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const checks = [];
let stage = 'launch';
let browser;
let contexts = [];
let originals;
let restorePage;
function passed(name) { checks.push(name); console.log('PASS: ' + name); }
async function visible(page, text) { await page.getByText(text, { exact: true }).waitFor({ state: 'visible', timeout: 20000 }); }
async function login(page, account, bad = false) {
  await page.getByLabel('Email address', { exact: true }).fill(config[`TEST_USER_${account}_EMAIL`]);
  await page.getByLabel('Password', { exact: true }).fill(bad ? 'Incorrect-' + Date.now() : config[`TEST_USER_${account}_PASSWORD`]);
  const reply = page.waitForResponse(r => new URL(r.url()).pathname === '/api/auth/login');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  const response = await reply;
  assert.equal(response.status(), bad ? 401 : 200);
  if (!bad) await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor({ timeout: 20000 });
}
async function read(page, route) {
  return page.evaluate(async route => { const r = await fetch('/api' + route, { credentials: 'include' }); return { status: r.status, body: await r.json() }; }, route);
}
async function restore(page) {
  if (!originals) return;
  await page.evaluate(async original => {
    const { csrf_token } = await (await fetch('/api/auth/csrf')).json();
    for (const [route, body] of [['/profile', { display_name: original.profile.display_name }], ['/settings', { preferred_language: original.settings.preferred_language, timezone: original.settings.timezone }]]) {
      const r = await fetch('/api' + route, { method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf_token }, body: JSON.stringify(body) });
      if (r.status !== 200) throw new Error('restore failed');
    }
  }, originals);
  originals = undefined;
}
(async () => {
  browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const otherContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  contexts = [context, otherContext];
  const page = await context.newPage();
  const other = await otherContext.newPage();
  restorePage = page;
  let pageErrors = 0;
  let providerRequests = 0;
  for (const c of contexts) {
    c.on('page', p => p.on('pageerror', () => pageErrors++));
    c.on('request', r => { if (new URL(r.url()).hostname.endsWith('.supabase.co')) providerRequests++; });
  }
  page.on('pageerror', () => pageErrors++);
  other.on('pageerror', () => pageErrors++);
  stage = 'anonymous protected routes';
  for (const route of ['/', '/reports', '/trends', '/assistant', '/settings']) {
    await page.goto(origin + route);
    await page.waitForURL('**/auth/sign-in');
    await visible(page, 'Welcome back');
  }
  passed(stage);
  stage = 'signup and verification form validation';
  await page.getByRole('link', { name: 'Create an account', exact: true }).click();
  await visible(page, 'Your health story starts here');
  assert.equal(await page.locator('#auth-password').getAttribute('minlength'), '12');
  await page.goto(origin + '/auth/verify-email');
  await visible(page, 'Check your email');
  await page.getByLabel('Confirmation code', { exact: true }).fill('12a345');
  assert.equal(await page.locator('#auth-code').inputValue(), '12345');
  await page.getByLabel('Confirmation code', { exact: true }).fill('123456');
  assert.equal(await page.locator('#auth-code').inputValue(), '123456');
  await page.goto(origin + '/auth/sign-in');
  await visible(page, 'Welcome back');
  await page.screenshot({ path: path.join(output, 'sign-in-desktop.png'), fullPage: true });
  passed(stage);
  stage = 'real invalid password';
  await login(page, 'A', true);
  await visible(page, 'The email or password is incorrect.');
  assert.equal(await page.locator('#auth-password').inputValue(), '');
  passed(stage);
  stage = 'real sign-in and original destination';
  await page.goto(origin + '/settings');
  await page.waitForURL('**/auth/sign-in');
  await login(page, 'A');
  await page.waitForURL('**/settings');
  await page.locator('#profile-name').waitFor();
  const aProfile = await read(page, '/profile');
  const aSettings = await read(page, '/settings');
  assert.equal(aProfile.status, 200); assert.equal(aSettings.status, 200);
  originals = { profile: aProfile.body, settings: aSettings.body };
  passed(stage);
  stage = 'cookie and browser credential boundaries';
  const cookies = await context.cookies();
  for (const name of ['sl_access', 'sl_refresh', 'sl_csrf']) {
    const cookie = cookies.find(c => c.name === name);
    assert.ok(cookie && cookie.httpOnly && cookie.sameSite === 'Lax' && cookie.path === '/');
  }
  assert.ok(cookies.find(c => c.name === 'sl_refresh').expires <= Date.now() / 1000 + 28801);
  assert.equal(await page.evaluate(() => document.cookie), '');
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
  passed(stage);
  stage = 'profile and preferences persist after browser reload';
  await page.locator('#profile-name').fill('Browser acceptance');
  await page.getByRole('button', { name: 'Save profile', exact: true }).click();
  await visible(page, 'Your profile has been saved.');
  await page.getByLabel('Interface language').selectOption('hi');
  await page.getByLabel('Time zone', { exact: true }).fill('Asia/Kolkata');
  await page.getByRole('button', { name: 'Save preferences', exact: true }).click();
  await visible(page, 'आपकी पसंद सहेज ली गई हैं।');
  await page.reload();
  await page.locator('#profile-name').waitFor();
  assert.equal(await page.locator('#profile-name').inputValue(), 'Browser acceptance');
  assert.equal(await page.locator('#preferred-language').inputValue(), 'hi');
  assert.equal(await page.locator('#account-timezone').inputValue(), 'Asia/Kolkata');
  await page.screenshot({ path: path.join(output, 'settings-desktop.png'), fullPage: true, mask: [page.locator('.account-email'), page.locator('.account-bar__identity')] });
  passed(stage);
  stage = 'separate browser user isolation';
  await other.goto(origin + '/settings');
  await other.waitForURL('**/auth/sign-in');
  await login(other, 'B');
  await other.locator('#profile-name').waitFor();
  const bProfile = await read(other, '/profile');
  assert.equal(bProfile.status, 200);
  assert.notEqual(bProfile.body.id, aProfile.body.id);
  assert.notEqual(bProfile.body.display_name, 'Browser acceptance');
  passed(stage);
  await page.locator('#preferred-language').selectOption('en');
  await page.locator('section[aria-labelledby="preferences-heading"]').getByRole('button', { name: 'पसंद सहेजें', exact: true }).click();
  await visible(page, 'Your preferences have been saved.');
  stage = 'Phase 1 navigation and truthful owned-data states';
  for (const [route, heading, empty] of [['/', 'Your health overview', 'No health observations yet.'], ['/reports', 'Your reports, together', 'No reports uploaded yet.'], ['/trends', 'The picture over time', 'Every trend starts with observations.'], ['/assistant', 'More understanding, less jargon', 'Your health story comes first.']]) {
    stage = 'Owned-data navigation ' + route;
    await page.goto(origin + route);
    await page.getByRole('heading', { name: heading, exact: true }).waitFor();
    if (route === '/reports') {
      const owned = await read(page, '/reports');
      assert.equal(owned.status, 200);
      console.log('INFO: owned report state ' + JSON.stringify({ count: owned.body.reports.length, statuses: owned.body.reports.map(r => r.status) }));
      if (owned.body.reports.length) {
        await page.locator('.report-row').first().waitFor();
        assert.equal(await page.locator('.report-row').count(), owned.body.reports.length);
        for (const report of owned.body.reports) await page.getByRole('heading', { name: report.original_filename, exact: true }).first().waitFor();
        assert.equal(await page.getByText(empty, { exact: true }).count(), 0);
      } else await visible(page, empty);
    } else if (route === '/') {
      const owned = await read(page, '/dashboard');
      assert.equal(owned.status, 200);
      await visible(page, owned.body.active_observations ? 'Recent health observations' : empty);
    } else if (route === '/trends') {
      const owned = await read(page, '/trends/catalog');
      assert.equal(owned.status, 200);
      if (owned.body.series.length) await page.locator('#trend-metric-label').waitFor();
      else await visible(page, empty);
    } else if (route === '/assistant') {
      const owned = await read(page, '/assistant/conversations');
      assert.equal(owned.status, 200);
      if (owned.body.conversations.length) await page.locator('.assistant-conversations li').first().waitFor();
      else await visible(page, empty);
    } else await visible(page, empty);
    await visible(page, 'Local API connected');
    assert.equal(await page.getByRole('navigation', { name: 'Primary navigation' }).locator('[aria-current="page"]').count(), 1);
    assert.equal(await page.locator('input[type="file"], textarea').count(), route === '/reports' ? 1 : 0);
  }
  await page.goBack(); await page.waitForURL('**/trends');
  await page.goForward(); await page.waitForURL('**/assistant');
  passed(stage);
  stage = 'Phase 1 health liveness and failure recovery';
  const health = await read(page, '/health');
  assert.deepEqual(health, { status: 200, body: { status: 'ok', service: 'swasthyalens-api' } });
  const healthPost = await page.evaluate(async () => (await fetch('/api/health', { method: 'POST' })).status);
  assert.equal(healthPost, 405);
  await page.route('**/api/health', r => r.abort());
  await page.reload();
  await visible(page, 'Local API unavailable');
  await page.unroute('**/api/health');
  await page.getByRole('button', { name: 'Retry connection' }).click();
  await visible(page, 'Local API connected');
  passed(stage);
  stage = 'mobile navigation and responsive layout';
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('button', { name: 'Open navigation', exact: true }).getAttribute('aria-expanded'), 'false');
  await page.getByRole('button', { name: 'Open navigation', exact: true }).click();
  await page.getByRole('navigation').getByRole('link', { name: 'Reports', exact: true }).click();
  await page.waitForURL('**/reports');
  assert.equal(await page.getByRole('button', { name: 'Open navigation', exact: true }).getAttribute('aria-expanded'), 'false');
  for (const route of ['/', '/reports', '/trends', '/assistant', '/settings']) {
    await page.goto(origin + route);
    await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
    if (route === '/settings') await page.locator('#profile-name').waitFor();
    else await page.getByRole('heading', { level: 1 }).waitFor();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  }
  await page.screenshot({ path: path.join(output, 'settings-mobile.png'), fullPage: true, mask: [page.locator('.account-email'), page.locator('.account-bar__identity')] });
  passed(stage);
  stage = 'real refresh after access cookie expiry';
  await context.clearCookies({ name: 'sl_access' });
  const refresh = page.waitForResponse(r => new URL(r.url()).pathname === '/api/auth/refresh');
  await page.reload();
  assert.equal((await refresh).status(), 200);
  await page.locator('#profile-name').waitFor();
  assert.equal((await read(page, '/profile')).body.id, aProfile.body.id);
  passed(stage);
  stage = 'session service failure and retry';
  await page.route('**/api/auth/me', r => r.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ code: 'service_unavailable', message: 'Test failure' }) }));
  await page.reload();
  await visible(page, 'Unable to check your session');
  assert.equal(await page.locator('#profile-name').count(), 0);
  await page.unroute('**/api/auth/me');
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await page.locator('#profile-name').waitFor();
  passed(stage);
  stage = 'restore original test data';
  await restore(page);
  passed(stage);
  stage = 'cross-tab logout and independent-user session';
  const tab = await context.newPage();
  await tab.goto(origin + '/settings');
  await tab.locator('#profile-name').waitFor();
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await page.waitForURL('**/auth/sign-in');
  await tab.waitForURL('**/auth/sign-in');
  assert.equal((await read(other, '/auth/me')).status, 200);
  assert.ok(!(await context.cookies()).some(c => ['sl_access', 'sl_refresh'].includes(c.name)));
  await page.reload(); await visible(page, 'Welcome back');
  await other.getByRole('button', { name: 'Sign out', exact: true }).click();
  await other.waitForURL('**/auth/sign-in');
  passed(stage);
  stage = 'browser runtime and provider isolation';
  assert.equal(pageErrors, 0); assert.equal(providerRequests, 0);
  passed(stage);
  fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify({ checks, emailDeliveryVerified: false, runtimeErrors: pageErrors, directProviderRequests: providerRequests }, null, 2));
})().catch(error => { console.error('FAIL: ' + stage + ' (' + error.name + ')'); console.error((error.message || '').split('\n').find(line => line.includes('waiting for')) || 'No locator diagnostic'); process.exitCode = 1; }).finally(async () => {
  if (originals && restorePage) { try { await restore(restorePage); } catch { console.error('Cleanup: original data restore requires retry'); process.exitCode = 1; } }
  for (const context of contexts) {
    try {
      const page = context.pages()[0];
      await page.evaluate(async () => { const r = await fetch('/api/auth/csrf'); const { csrf_token } = await r.json(); await fetch('/api/auth/logout', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf_token }, body: '{}' }); });
    } catch { /* no credentials or response bodies logged */ }
  }
  await browser?.close();
});

