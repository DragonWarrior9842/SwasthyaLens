/* Real Phase 8 browser acceptance. Dedicated accounts, synthetic values, zero AI. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const python = path.join(root, 'backend/.venv/Scripts/python.exe');
const config = JSON.parse(execFileSync(python, ['-c', 'import json; from dotenv import dotenv_values; print(json.dumps(dotenv_values(".env.integration")))'], { cwd: path.join(root, 'backend'), encoding: 'utf8' }));
assert.equal(config.DISPOSABLE_TEST_ACCOUNTS_CONFIRMED, '1');
assert.notEqual(process.env.RUN_AI_INTEGRATION, '1');
const fixture = execFileSync(python, ['-c', 'import sys; from tests import extraction_fixtures as f; from tests.parameter_fixtures import NATIVE_LINES; f.LINES=NATIVE_LINES; sys.stdout.buffer.write(f.document(("native",)))'], { cwd: path.join(root, 'backend') });
const output = path.join(root, '.cache/qa/phase8');
fs.mkdirSync(output, { recursive: true });
const endDate = new Date(); endDate.setUTCDate(endDate.getUTCDate() - 1);
const end = endDate.toISOString().slice(0, 10);
function day(index) { const d = new Date(end + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() - 13 + index); return d.toISOString().slice(0, 10); }
let browser, page, editor, stage = 'launch', originalTimezone, errors = 0, aiRequests = 0;
const manuals = new Set(), reports = new Set(), checks = [];
function pass() { checks.push(stage); console.log('PASS: ' + stage); }
async function write(target, method, route, body) {
  return target.evaluate(async ({ method, route, body }) => {
    const csrf = (await (await fetch('/api/auth/csrf')).json()).csrf_token;
    const response = await fetch('/api' + route, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  }, { method, route, body });
}
function watch(target) {
  target.on('pageerror', () => errors++);
  target.on('response', async r => {
    if (r.status() >= 400 && new URL(r.url()).pathname.startsWith('/api/trends')) console.log('Trend HTTP status: ' + r.status());
    if (r.request().method() === 'POST' && r.status() === 200 && new URL(r.url()).pathname === '/api/observations/manual') manuals.add((await r.json()).id);
    if (r.request().method() === 'POST' && r.status() === 201 && new URL(r.url()).pathname === '/api/reports') reports.add((await r.json()).id);
  });
}
async function choose(metric, unit) {
  const previousStage = stage;
  stage = previousStage + ': metric selector';
  await page.getByLabel('Metric and unit', { exact: true }).selectOption(JSON.stringify([metric, unit]));
  stage = previousStage + ': end-day selector';
  await page.getByLabel('Period ending (blank for today)', { exact: true }).fill(end);
  stage = previousStage + ': refresh control';
  await page.getByRole('button', { name: 'Refresh trends', exact: true }).waitFor();
  stage = previousStage;
}
(async () => {
  browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (['api.openai.com', 'generativelanguage.googleapis.com'].includes(url.hostname) || (url.pathname.endsWith('/explanations') && route.request().method() === 'POST')) { aiRequests++; return route.abort(); }
    return route.continue();
  });
  page = await context.newPage(); watch(page);
  stage = 'sign in and real empty Trends state';
  await page.goto('http://127.0.0.1:5173/trends');
  await page.getByLabel('Email address', { exact: true }).fill(config.TEST_USER_A_EMAIL);
  await page.getByLabel('Password', { exact: true }).fill(config.TEST_USER_A_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByText('Every trend starts with observations.', { exact: true }).waitFor({ timeout: 30000 });
  originalTimezone = await page.evaluate(async () => (await (await fetch('/api/settings')).json()).timezone);
  assert.equal((await write(page, 'PATCH', '/settings', { timezone: 'UTC' })).status, 200); pass();

  stage = 'manual UI entry appears as sparse real data';
  await page.goto('http://127.0.0.1:5173/history');
  const form = page.getByRole('form', { name: 'Add manual measurement', exact: true });
  await form.getByLabel('Measured value (kg)', { exact: true }).fill('70.250');
  await form.getByLabel('Measurement time (UTC)', { exact: true }).fill(day(0) + 'T12:00');
  await form.getByRole('button', { name: 'Save measurement', exact: true }).click();
  stage = 'manual UI: await new history card';
  await page.getByRole('article', { name: 'Observation Weight', exact: true }).waitFor();
  stage = 'manual UI: select bounded trend';
  await page.goto('http://127.0.0.1:5173/trends'); await choose('weight', 'kg');
  stage = 'manual UI: await insufficient result';
  await page.getByText('Insufficient data for a period trend', { exact: true }).waitFor();
  stage = 'manual UI: verify one real point';
  await page.getByText('Exact measurement table (1 observations)', { exact: true }).waitFor(); pass();

  stage = 'seven-day and preceding-period real synthetic calculation';
  for (let index = 1; index < 14; index++) {
    const result = await write(page, 'POST', '/observations/manual', { metric: 'weight', unit: 'kg', raw_value: index < 7 ? '70.250' : '72.750', measured_at: day(index) + 'T12:00:00Z', idempotency_key: crypto.randomUUID() });
    assert.equal(result.status, 200); manuals.add(result.body.id);
  }
  const hr = await write(page, 'POST', '/observations/manual', { metric: 'heart_rate', unit: 'bpm', raw_value: '60', measured_at: end + 'T12:00:00Z', idempotency_key: crypto.randomUUID() });
  assert.equal(hr.status, 200); manuals.add(hr.body.id);
  await page.reload(); await choose('weight', 'kg');
  await page.getByText('Increasing', { exact: true }).waitFor();
  await page.getByText('Median of daily medians: 72.750 kg', { exact: true }).waitFor();
  await page.getByText('Median of daily medians: 70.250 kg', { exact: true }).waitFor();
  await page.getByRole('img', { name: /^7 real measurement points/ }).waitFor();
  await page.getByText('Exact measurement table (14 observations)', { exact: true }).click();
  assert.equal(await page.locator('.trend-data tbody tr').count(), 14); pass();

  stage = 'thirty-day insufficiency and metric switching';
  await page.getByLabel('Period', { exact: true }).selectOption('30d');
  await page.getByText('Insufficient data for a period trend', { exact: true }).waitFor();
  await choose('heart_rate', 'bpm');
  await page.getByText('Exact measurement table (1 observations)', { exact: true }).waitFor();
  await choose('weight', 'kg'); await page.getByLabel('Period', { exact: true }).selectOption('7d');
  await page.getByText('Increasing', { exact: true }).waitFor(); pass();

  stage = 'accessible exact table and mobile chart layout';
  await page.locator('.trend-data summary').click();
  await page.screenshot({ path: path.join(output, 'trends-desktop.png'), fullPage: true, mask: [page.locator('.account-bar__identity')] });
  await page.setViewportSize({ width: 375, height: 900 });
  await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth);
  await page.getByRole('region', { name: 'Scrollable exact measurement table' }).focus();
  await page.screenshot({ path: path.join(output, 'trends-mobile.png'), fullPage: true, mask: [page.locator('.account-bar__identity')] });
  await page.setViewportSize({ width: 1440, height: 1100 }); pass();

  stage = 'cross-tab manual correction clears and replaces active input';
  editor = await context.newPage(); watch(editor);
  await editor.goto('http://127.0.0.1:5173/history?metric=weight');
  const entry = editor.getByRole('article', { name: 'Observation Weight', exact: true }).first();
  await entry.getByRole('button', { name: 'Edit measurement', exact: true }).click();
  const edit = entry.getByRole('form', { name: 'Edit manual measurement', exact: true });
  await edit.getByLabel('Measured value (kg)', { exact: true }).fill('73.125');
  await edit.getByRole('button', { name: 'Save measurement correction', exact: true }).click();
  await page.getByText('73.125 kg', { exact: true }).first().waitFor({ timeout: 30000 });
  await page.getByText('Exact measurement table (14 observations)', { exact: true }).waitFor(); pass();

  stage = 'cross-tab manual deletion recalculates without duplicate revisions';
  await entry.getByRole('button', { name: 'Delete measurement', exact: true }).click();
  await entry.getByRole('button', { name: 'Confirm delete measurement', exact: true }).click();
  await page.getByText('Exact measurement table (13 observations)', { exact: true }).waitFor({ timeout: 30000 });
  assert.equal(await page.getByText('73.125 kg', { exact: true }).count(), 0); pass();

  stage = 'report extraction review and explicit publication reaches Trends';
  await editor.goto('http://127.0.0.1:5173/reports');
  await editor.locator('#report-file').setInputFiles({ name: 'synthetic-trends-browser.pdf', mimeType: 'application/pdf', buffer: fixture });
  await editor.getByRole('checkbox').check(); await editor.getByRole('button', { name: 'Upload report', exact: true }).click();
  const report = editor.locator('.report-row').filter({ has: editor.getByRole('heading', { name: 'synthetic-trends-browser.pdf', exact: true }) });
  await report.getByText('Uploaded', { exact: true }).waitFor({ timeout: 30000 });
  await report.getByRole('button', { name: 'Text extraction', exact: true }).click();
  await report.getByRole('button', { name: 'Extract text', exact: true }).click();
  await report.getByRole('button', { name: 'View extracted text · Attempt 1', exact: true }).waitFor({ timeout: 45000 });
  await report.getByRole('button', { name: 'Parameter candidates', exact: true }).click();
  await report.getByRole('button', { name: 'Extract parameters', exact: true }).click();
  const candidate = report.getByRole('article', { name: 'Candidate Hemoglobin', exact: true });
  await candidate.getByRole('button', { name: 'Confirm reviewed', exact: true }).click();
  await candidate.getByText('Confirmed by you', { exact: true }).waitFor();
  await candidate.getByLabel('Measurement date (optional, confirmed by you)').fill(end);
  await candidate.getByRole('button', { name: 'Publish to health history', exact: true }).click();
  await candidate.getByRole('button', { name: 'Published to health history', exact: true }).waitFor();
  await page.getByRole('option', { name: 'Hemoglobin · g/dL', exact: true }).waitFor({ state: 'attached', timeout: 30000 });
  await choose('hemoglobin', 'g/dL'); await page.getByText('13.20 g/dL', { exact: true }).first().waitFor(); pass();

  stage = 'source correction removes stale trend until republication';
  await candidate.getByRole('button', { name: 'Correct fields', exact: true }).click();
  await candidate.getByLabel('Value', { exact: true }).fill('13.21');
  await candidate.getByRole('button', { name: 'Save correction', exact: true }).click();
  await candidate.getByText('Corrected by you', { exact: true }).waitFor();
  await page.getByRole('option', { name: 'Hemoglobin · g/dL', exact: true }).waitFor({ state: 'detached', timeout: 30000 });
  assert.equal(await page.getByText('13.20 g/dL', { exact: true }).count(), 0);
  await candidate.getByLabel('Measurement date (optional, confirmed by you)').fill(end);
  await candidate.getByRole('button', { name: 'Publish to health history', exact: true }).click();
  await candidate.getByRole('button', { name: 'Published to health history', exact: true }).waitFor();
  await page.getByRole('option', { name: 'Hemoglobin · g/dL', exact: true }).waitFor({ state: 'attached', timeout: 30000 });
  await choose('hemoglobin', 'g/dL'); await page.getByText('13.21 g/dL', { exact: true }).first().waitFor(); pass();

  stage = 'report deletion removes derived points and preserves manual history';
  await report.getByRole('button', { name: 'Delete report', exact: true }).click();
  await report.getByRole('button', { name: 'Confirm delete', exact: true }).click();
  await report.waitFor({ state: 'detached', timeout: 30000 });
  await page.getByRole('option', { name: 'Hemoglobin · g/dL', exact: true }).waitFor({ state: 'detached', timeout: 30000 });
  await choose('weight', 'kg'); await page.getByText('Exact measurement table (13 observations)', { exact: true }).waitFor();
  assert.equal(await page.getByText('13.21 g/dL', { exact: true }).count(), 0); pass();

  stage = 'safe read failure clears result and explicit refresh recovers';
  await page.route('**/api/trends/weight?*', route => route.fulfill({ status: 503, json: { code: 'trend_unavailable' } }));
  await page.getByRole('button', { name: 'Refresh trends', exact: true }).click();
  await page.getByRole('alert').waitFor(); assert.equal(await page.locator('canvas').count(), 0);
  await page.unroute('**/api/trends/weight?*'); await page.getByRole('button', { name: 'Refresh trends', exact: true }).click();
  await page.getByText('Exact measurement table (13 observations)', { exact: true }).waitFor(); pass();

  // The dense browser scenario can exhaust the intentional 30 reads/minute limit.
  // Wait for its window before testing reload/dashboard persistence.
  await page.waitForTimeout(61000);
  stage = 'unsupported correlation is explicit and refresh persists real data';
  await page.getByText('Correlation describes an association in the available measurements and does not establish cause and effect.', { exact: true }).waitFor();
  await page.reload(); await choose('weight', 'kg'); await page.getByText('Exact measurement table (13 observations)', { exact: true }).waitFor();
  await editor.close(); editor = null;
  await page.goto('http://127.0.0.1:5173/'); await page.getByRole('heading', { name: 'Weight · seven-day comparison', exact: true }).waitFor(); pass();

  stage = 'fixture cleanup logout and zero AI requests';
  for (const id of manuals) { const response = await page.evaluate(async id => { const r = await fetch('/api/observations/' + id); return { status: r.status, body: await r.json() } }, id); if (response.status === 200) assert.equal((await write(page, 'DELETE', '/observations/' + id, { expected_revision: response.body.current.revision })).status, 200); }
  manuals.clear();
  assert.equal((await write(page, 'PATCH', '/settings', { timezone: originalTimezone })).status, 200); originalTimezone = null;
  assert.equal(errors, 0); assert.equal(aiRequests, 0);
  await page.getByRole('button', { name: 'Sign out', exact: true }).click(); await page.waitForURL('**/auth/sign-in');
  await page.goto('http://127.0.0.1:5173/trends'); await page.waitForURL('**/auth/sign-in*'); pass();
  fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify({ checks, passed: checks.length, aiRequests }, null, 2));
})().catch(async error => { console.error('FAIL: ' + stage + ' ' + error.name + ' (account details suppressed)'); if (page) { console.error('Visible safe error: ' + JSON.stringify(await page.getByRole('alert').allTextContents().catch(() => []))); await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true, mask: [page.locator('.account-bar__identity')] }).catch(() => {}); } process.exitCode = 1; }).finally(async () => {
  if (page && !page.isClosed()) {
    for (const id of reports) await write(page, 'DELETE', '/reports/' + id, {}).catch(() => {});
    for (const id of manuals) { const response = await page.evaluate(async id => { const r = await fetch('/api/observations/' + id); return { status: r.status, body: await r.json() } }, id).catch(() => null); if (response?.status === 200) await write(page, 'DELETE', '/observations/' + id, { expected_revision: response.body.current.revision }).catch(() => {}); }
    if (originalTimezone) await write(page, 'PATCH', '/settings', { timezone: originalTimezone }).catch(() => {});
  }
  await browser?.close();
});

