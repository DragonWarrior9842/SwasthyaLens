/* Opt-in synthetic Phase 11 acceptance against real A/B accounts. No AI calls. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..'), python = path.join(root, 'backend/.venv/Scripts/python.exe');
assert.equal(process.env.RUN_AI_INTEGRATION, undefined);
const config = JSON.parse(execFileSync(python, ['-c', 'import json; from dotenv import dotenv_values; print(json.dumps(dotenv_values(".env.integration")))'], { cwd: path.join(root, 'backend'), encoding: 'utf8' }));
assert.equal(config.DISPOSABLE_TEST_ACCOUNTS_CONFIRMED, '1');
const fixture = execFileSync(python, ['-c', 'import sys; from tests import extraction_fixtures as f; from tests.parameter_fixtures import NATIVE_LINES; f.LINES=NATIVE_LINES; sys.stdout.buffer.write(f.document(("native",)))'], { cwd: path.join(root, 'backend') });
const catalog = fs.readFileSync(path.join(root, 'frontend/src/i18n/hindi.ts'), 'utf8');
const hi = JSON.parse(catalog.slice(catalog.indexOf('{'), catalog.lastIndexOf('}') + 1).replace(/,\s*}/g, '}'));
const origin = 'http://127.0.0.1:5173', output = path.join(root, '.cache/qa/phase11');
fs.mkdirSync(output, { recursive: true });
let browser, page, other, stage = 'launch', errors = 0, ai = 0, exportsSent = 0;
const originals = [], reports = [], manuals = [], checks = [];
const pass = () => { checks.push(stage); console.log('PASS: ' + stage); };
async function read(p, route) { return p.evaluate(async route => { const r = await fetch('/api' + route); return { status: r.status, body: await r.json() }; }, route); }
async function write(p, method, route, body) {
  return p.evaluate(async ({ method, route, body }) => {
    const csrf = (await (await fetch('/api/auth/csrf')).json()).csrf_token;
    const r = await fetch('/api' + route, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify(body) });
    return { status: r.status, body: await r.json() };
  }, { method, route, body });
}
async function login(p, account) {
  await p.goto(origin + '/settings');
  await p.getByLabel('Email address', { exact: true }).fill(config[`TEST_USER_${account}_EMAIL`]);
  await p.getByLabel('Password', { exact: true }).fill(config[`TEST_USER_${account}_PASSWORD`]);
  await p.getByRole('button', { name: 'Sign in', exact: true }).click();
  await p.locator('#preferred-language').waitFor();
  const settings = (await read(p, '/settings')).body;
  originals.push([p, { preferred_language: settings.preferred_language, assistant_language: settings.assistant_language, timezone: settings.timezone, in_app_notifications: settings.in_app_notifications }]);
  assert.equal((await write(p, 'PATCH', '/settings', { preferred_language: 'en', in_app_notifications: true })).status, 200);
  await p.reload(); await p.getByLabel('Interface language', { exact: true }).waitFor();
}
async function screenshot(name) {
  await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
  await page.screenshot({ path: path.join(output, name), fullPage: true, mask: [page.locator('.account-bar__identity')] });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'horizontal overflow');
}
async function exportForm(p) {
  await p.goto(origin + '/exports');
  await p.getByLabel('Measurement from', { exact: true }).fill('2020-01-01');
  await p.getByLabel('Measurement through', { exact: true }).fill('2020-12-31');
  await p.getByLabel('Source', { exact: true }).selectOption('manual');
}
async function download(p, label) {
  const event = p.waitForEvent('download');
  await p.getByRole('button', { name: label, exact: true }).click();
  const artifact = await event;
  assert.equal(await artifact.failure(), null);
  return { name: artifact.suggestedFilename(), text: fs.readFileSync(await artifact.path(), 'utf8') };
}
(async () => {
  browser = await chromium.launch({ channel: 'chrome', headless: true });
  const contexts = await Promise.all([browser.newContext({ viewport: { width: 1440, height: 1000 } }), browser.newContext()]);
  for (const c of contexts) {
    c.on('page', p => p.on('pageerror', () => errors++));
    await c.route(/^https:\/\/(api\.openai\.com|generativelanguage\.googleapis\.com)\//, route => { ai++; return route.abort(); });
    c.on('request', request => {
      if (new URL(request.url()).pathname === '/api/exports' && request.method() === 'POST') exportsSent++;
    });
  }
  page = await contexts[0].newPage(); other = await contexts[1].newPage();
  stage = 'real A/B settings preserve existing preferences and enable future notices';
  await login(page, 'A'); await login(other, 'B');
  await page.getByLabel('Receive in-app operational notifications', { exact: true }).waitFor(); pass();
  stage = 'real synthetic manual observations for two owners';
  for (const [p, value] of [[page, '13.20'], [other, '14.30']]) {
    const r = await write(p, 'POST', '/observations/manual', { idempotency_key: crypto.randomUUID(), metric: 'weight', raw_value: value, unit: 'kg', measured_at: '2020-07-11T12:00:00Z' });
    assert.equal(r.status, 200); manuals.push([p, r.body.id]);
  }
  pass();
  stage = 'English export labels and keyboard selectors; no generation on page load';
  await exportForm(page); assert.equal(exportsSent, 0);
  await page.getByLabel('Source', { exact: true }).focus(); await page.keyboard.press('Tab');
  assert.equal(await page.getByLabel('Measurement from', { exact: true }).evaluate(e => document.activeElement === e), true);
  await screenshot('exports-en-desktop.png'); pass();
  stage = 'explicit generation status and exact private JSON download';
  let release; const delayed = new Promise(resolve => { release = resolve; });
  await page.route('**/api/exports', async route => { await delayed; await route.continue(); }, { times: 1 });
  const pending = download(page, 'Generate and download');
  await page.getByRole('status').filter({ hasText: 'Generating export…' }).waitFor();
  release(); const json = await pending;
  assert.equal(json.name, 'swasthyalens-health.json');
  const aRows = JSON.parse(json.text).observations;
  assert.ok(aRows.some(r => r.raw_value === '13.20' && r.original_unit === 'kg'));
  assert.ok(!aRows.some(r => r.raw_value === '14.30'));
  assert.ok(aRows.every(r => !Object.hasOwn(r, 'id') && !Object.hasOwn(r, 'user_id')));
  await page.getByText('Export ready. Download started; your browser controls where the file is saved.', { exact: true }).waitFor(); pass();
  stage = 'B download contains B synthetic data and excludes A';
  await exportForm(other); const bRows = JSON.parse((await download(other, 'Generate and download')).text).observations;
  assert.ok(bRows.some(r => r.raw_value === '14.30')); assert.ok(!bRows.some(r => r.raw_value === '13.20')); pass();
  stage = 'invalid export period fails explicitly without automatic retry';
  await page.getByLabel('Measurement through', { exact: true }).fill('2022-01-01');
  const invalid = page.waitForResponse(r => new URL(r.url()).pathname === '/api/exports' && r.request().method() === 'POST');
  const before = exportsSent;
  await page.getByRole('button', { name: 'Generate and download', exact: true }).click();
  assert.equal((await invalid).status(), 422); await page.getByRole('alert').waitFor(); assert.equal(exportsSent, before + 1); pass();
  stage = 'real report uploads generate owner-only generic notices';
  for (const p of [page, other]) {
    const name = 'synthetic-phase11-' + crypto.randomUUID() + '.pdf';
    await p.goto(origin + '/reports'); await p.locator('#report-file').setInputFiles({ name, mimeType: 'application/pdf', buffer: fixture });
    await p.getByRole('checkbox').check();
    const created = p.waitForResponse(r => new URL(r.url()).pathname === '/api/reports' && r.request().method() === 'POST');
    await p.getByRole('button', { name: 'Upload report', exact: true }).click();
    const response = await created; assert.equal(response.status(), 201); const id = (await response.json()).id; reports.push([p, id]);
    const row = p.locator('.report-row').filter({ has: p.getByRole('heading', { name, exact: true }) });
    await row.getByText('Uploaded', { exact: true }).waitFor();
    if (p === page) {
      await row.getByRole('button', { name: 'Text extraction', exact: true }).click();
      await row.getByRole('button', { name: 'Extract text', exact: true }).click();
      await row.getByRole('button', { name: 'View extracted text · Attempt 1', exact: true }).waitFor({ timeout: 45000 });
      await row.getByRole('button', { name: 'Parameter candidates', exact: true }).click();
      await row.getByRole('button', { name: 'Extract parameters', exact: true }).click();
      await row.locator('.parameter-candidate').first().waitFor();
    }
  }
  const notices = (await read(page, '/notifications')).body;
  const selected = notices.items.filter(n => n.report_id === reports[0][1]);
  assert.deepEqual(selected.map(n => n.event_type).sort(), ['extraction_completed', 'parameters_ready', 'upload_completed']);
  assert.ok(!(await read(other, '/notifications')).body.items.some(n => n.report_id === reports[0][1]));
  assert.equal((await write(other, 'PATCH', '/notifications/' + selected[0].id, {})).status, 404); pass();
  stage = 'notification center has truthful copy, unread text and keyboard read actions';
  await page.goto(origin + '/notifications'); await page.locator('.notification-item').first().waitFor();
  await page.getByText('Your report upload completed.', { exact: true }).first().waitFor();
  await page.getByText('Unread', { exact: true }).first().waitFor();
  assert.ok(!(await page.locator('.notification-list').textContent()).includes('13.20'));
  const readButton = page.getByRole('button', { name: 'Mark read', exact: true }).first();
  await readButton.focus(); await page.keyboard.press('Enter');
  await page.getByText('Read', { exact: true }).first().waitFor();
  await page.getByRole('button', { name: 'Mark all read', exact: true }).click();
  await page.getByText('0 unread notifications', { exact: true }).waitFor();
  await page.getByRole('link', { name: 'Notifications · 0 unread', exact: true }).waitFor(); pass();
  stage = 'notification refresh preserves read state and dismiss removes an event';
  await page.reload(); await page.getByText('0 unread notifications', { exact: true }).waitFor();
  const beforeDismiss = await page.locator('.notification-item').count();
  await page.getByRole('button', { name: 'Dismiss', exact: true }).first().click();
  await page.waitForFunction(count => document.querySelectorAll('.notification-item').length === count - 1, beforeDismiss);
  await page.getByRole('button', { name: 'Refresh notifications', exact: true }).click();
  await page.getByText('0 unread notifications', { exact: true }).waitFor();
  await screenshot('notifications-en-desktop.png'); pass();
  stage = 'Hindi settings switch localizes operational events without rewriting facts';
  const beforeLocale = (await read(page, '/notifications')).body.items;
  await page.goto(origin + '/settings'); await page.locator('#preferred-language').selectOption('hi');
  const saved = page.waitForResponse(r => new URL(r.url()).pathname === '/api/settings' && r.request().method() === 'PATCH');
  await page.locator('section[aria-labelledby="preferences-heading"] button[type="submit"]').click(); assert.equal((await saved).status(), 200);
  await page.waitForFunction(() => document.documentElement.lang === 'hi');
  await page.goto(origin + '/notifications'); await page.getByRole('heading', { name: hi['Notifications'], exact: true }).waitFor();
  await page.getByText(hi['Your report upload completed.'], { exact: true }).first().waitFor();
  assert.deepEqual((await read(page, '/notifications')).body.items, beforeLocale);
  await page.setViewportSize({ width: 375, height: 812 }); await screenshot('notifications-hi-mobile.png'); pass();
  stage = 'Hindi export controls and CSV preserve exact source string and unit';
  await page.goto(origin + '/exports');
  await page.getByLabel(hi['Measurement from'], { exact: true }).fill('2020-01-01');
  await page.getByLabel(hi['Measurement through'], { exact: true }).fill('2020-12-31');
  await page.getByLabel(hi['Source'], { exact: true }).selectOption('manual');
  await page.getByLabel(hi['File format'], { exact: true }).selectOption('csv');
  const csv = await download(page, hi['Generate and download']);
  assert.equal(csv.name, 'swasthyalens-health.csv'); assert.ok(csv.text.startsWith('\ufeff')); assert.ok(csv.text.includes('"13.20","kg"')); assert.ok(csv.text.includes('मूल मान'));
  await screenshot('exports-hi-mobile.png'); pass();
  stage = 'source deletion removes facts on regeneration and no retained export URL exists';
  assert.equal((await write(page, 'DELETE', '/observations/' + manuals[0][1], { expected_revision: 1 })).status, 200); manuals.shift();
  await page.getByLabel(hi['File format'], { exact: true }).selectOption('json');
  const regenerated = JSON.parse((await download(page, hi['Generate and download'])).text);
  assert.ok(!regenerated.observations.some(r => r.raw_value === '13.20'));
  assert.equal((await read(page, '/exports/' + crypto.randomUUID() + '/download')).status, 404);
  assert.equal((await write(page, 'DELETE', '/reports/' + reports[0][1], {})).status, 200);
  const deleted = reports.shift()[1]; assert.ok(!(await read(page, '/notifications')).body.items.some(n => n.report_id === deleted)); pass();
  stage = 'restore settings and logout clears protected exports and notifications';
  for (const [p, body] of originals) assert.equal((await write(p, 'PATCH', '/settings', body)).status, 200);
  originals.length = 0;
  for (const [p, id] of manuals) assert.equal((await write(p, 'DELETE', '/observations/' + id, { expected_revision: 1 })).status, 200);
  manuals.length = 0;
  for (const [p, id] of reports) assert.equal((await write(p, 'DELETE', '/reports/' + id, {})).status, 200);
  reports.length = 0;
  await page.getByRole('button', { name: new RegExp('^(Sign out|' + hi['Sign out'] + ')$') }).click(); await page.waitForURL('**/auth/sign-in');
  assert.equal((await read(page, '/notifications')).status, 401);
  await page.goto(origin + '/exports'); await page.waitForURL(url => url.pathname === '/auth/sign-in'); assert.equal(await page.locator('.export-controls').count(), 0); pass();
  stage = 'zero browser errors, zero AI requests and explicit downloads only';
  assert.equal(errors, 0); assert.equal(ai, 0); assert.equal(exportsSent, 5); pass();
  fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify({ checks, errors, ai, exportsSent, syntheticOnly: true }, null, 2));
})().catch(error => { console.error('FAIL: ' + stage + ' (' + error.name + ')'); process.exitCode = 1; }).finally(async () => {
  for (const [p, id] of reports) { try { assert.equal((await write(p, 'DELETE', '/reports/' + id, {})).status, 200); } catch { console.error('Cleanup: synthetic report needs removal'); process.exitCode = 1; } }
  for (const [p, id] of manuals) { try { assert.equal((await write(p, 'DELETE', '/observations/' + id, { expected_revision: 1 })).status, 200); } catch { console.error('Cleanup: synthetic manual needs removal'); process.exitCode = 1; } }
  for (const [p, body] of originals) { try { assert.equal((await write(p, 'PATCH', '/settings', body)).status, 200); } catch { console.error('Cleanup: preferences need restoration'); process.exitCode = 1; } }
  for (const p of [page, other]) { try { await write(p, 'POST', '/auth/logout', {}); } catch { /* Do not log credentials or account data. */ } }
  await browser?.close();
});
