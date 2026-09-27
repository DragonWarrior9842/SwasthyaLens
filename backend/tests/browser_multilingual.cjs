/* Phase 10: real settings/auth, explicitly routed synthetic evidence. No live AI. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const config = JSON.parse(execFileSync(path.join(root, 'backend/.venv/Scripts/python.exe'), ['-c', 'import json; from dotenv import dotenv_values; print(json.dumps(dotenv_values(".env.integration")))'], { cwd: path.join(root, 'backend'), encoding: 'utf8' }));
assert.equal(config.DISPOSABLE_TEST_ACCOUNTS_CONFIRMED, '1');
assert.equal(process.env.RUN_AI_INTEGRATION, undefined);
const catalog = fs.readFileSync(path.join(root, 'frontend/src/i18n/hindi.ts'), 'utf8');
const hi = JSON.parse(catalog.slice(catalog.indexOf('{'), catalog.lastIndexOf('}') + 1).replace(/,\s*}/g, '}'));
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'frontend/src/services/fixtures/multilingual.json'), 'utf8'));
const trend = JSON.parse(fs.readFileSync(path.join(root, 'frontend/src/services/fixtures/trend.json'), 'utf8'));
const origin = 'http://127.0.0.1:5173', output = path.join(root, '.cache/qa/phase10');
fs.mkdirSync(output, { recursive: true });
let browser, page, other, editor, stage = 'launch', errors = 0, ai = 0, sends = 0;
const originals = [], checks = [];
const pass = () => { checks.push(stage); console.log('PASS: ' + stage); };
const visible = (p, key) => p.getByText(hi[key], { exact: true }).first().waitFor();
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
}
async function save(p, ui, assistant) {
  await p.locator('#preferred-language').selectOption(ui);
  await p.locator('#assistant-language').selectOption(assistant);
  const response = p.waitForResponse(r => r.request().method() === 'PATCH' && new URL(r.url()).pathname === '/api/settings');
  await p.locator('section[aria-labelledby="preferences-heading"] button[type="submit"]').click();
  assert.equal((await response).status(), 200);
  await p.waitForFunction(locale => document.documentElement.lang === locale, ui);
}
async function screenshot(name) {
  await page.screenshot({ path: path.join(output, name), fullPage: true, mask: [page.locator('.account-bar__identity'), page.locator('.account-email'), page.locator('#profile-name')] });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile horizontal overflow');
}
(async () => {
  browser = await chromium.launch({ channel: 'chrome', headless: true });
  const aContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const bContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  for (const c of [aContext, bContext]) {
    c.on('page', p => p.on('pageerror', () => errors++));
    await c.route('**/*', route => {
      const url = new URL(route.request().url());
      if (['api.openai.com', 'generativelanguage.googleapis.com'].includes(url.hostname)) { ai++; return route.abort(); }
      if (route.request().method() === 'POST' && url.pathname.endsWith('/messages')) sends++;
      return route.continue();
    });
  }
  page = await aContext.newPage(); other = await bContext.newPage();
  stage = 'English controls and independent saved interface/assistant settings';
  for (const [p, account] of [[page, 'A'], [other, 'B']]) {
    await login(p, account);
    const settings = (await read(p, '/settings')).body;
    originals.push([p, { preferred_language: settings.preferred_language, assistant_language: settings.assistant_language, timezone: settings.timezone }]);
    await save(p, 'en', 'en');
  }
  await page.getByLabel('Interface language', { exact: true }).waitFor();
  await page.getByLabel('Assistant response language', { exact: true }).waitFor(); pass();
  stage = 'Hindi interface and Hinglish preference persist across refresh';
  await save(page, 'hi', 'hinglish');
  await visible(page, 'Your preferences have been saved.');
  const aId = (await read(page, '/auth/me')).body.user.id;
  await page.reload(); await page.getByLabel(hi['Interface language'], { exact: true }).waitFor();
  assert.equal(await page.locator('#assistant-language').inputValue(), 'hinglish');
  assert.equal((await read(page, '/auth/me')).body.user.id, aId); pass();
  stage = 'separate real user keeps English settings and document language';
  await other.reload(); await other.getByLabel('Interface language', { exact: true }).waitFor();
  assert.equal((await read(other, '/settings')).body.assistant_language, 'en');
  assert.equal(await other.locator('html').getAttribute('lang'), 'en'); pass();
  stage = 'keyboard labels, Hindi system font and mobile settings wrapping';
  await page.locator('#preferred-language').focus(); await page.keyboard.press('Tab');
  assert.equal(await page.locator('#assistant-language').evaluate(e => document.activeElement === e), true);
  await page.setViewportSize({ width: 375, height: 812 });
  assert.ok(await page.locator('body').evaluate(e => getComputedStyle(e).fontFamily.includes('Nirmala')));
  await screenshot('settings-hi-mobile.png'); pass();
  stage = 'Hindi validation error without changing preferences';
  await page.locator('#account-timezone').fill('Invalid/Timezone');
  await page.locator('section[aria-labelledby="preferences-heading"] button[type="submit"]').click();
  await visible(page, 'Enter a valid time zone, such as Asia/Kolkata or UTC.');
  assert.equal((await read(page, '/settings')).body.assistant_language, 'hinglish'); pass();
  stage = 'logout/login restores server language preferences';
  await page.getByRole('button', { name: hi['Sign out'], exact: true }).click();
  await page.waitForURL('**/auth/sign-in');
  assert.equal(await page.locator('html').getAttribute('lang'), 'en');
  await login(page, 'A'); await page.getByLabel(hi['Interface language'], { exact: true }).waitFor();
  assert.equal(await page.locator('#assistant-language').inputValue(), 'hinglish'); pass();

  // Only explicitly synthetic or empty data is displayed in screenshots below.
  const emptyCatalog = { rules_version: 'trends-v1', timezone: 'UTC', as_of: '2026-09-25T00:00:00Z', period_end: '2026-09-24', series: [], correlations: { status: 'unsupported_catalog', pairs: [], minimum_pairs: 14, method: 'pearson_same_day_medians', rules_version: 'correlations-v1' } };
  await page.route('**/api/dashboard', route => route.fulfill({ json: { uploaded_reports: 0, reviewed_parameters: 0, active_observations: 0, observations: [], reports: [] } }));
  await page.route('**/api/observations?*', route => route.fulfill({ json: { items: [], next_offset: null } }));
  await page.route('**/api/trends/catalog', route => route.fulfill({ json: emptyCatalog }));
  await page.route('**/api/trends/*?*', route => route.fulfill({ status: 503, json: { code: 'service_unavailable' } }));
  await page.route('**/api/reports', route => route.request().method() === 'GET' ? route.fulfill({ json: { reports: [], next_cursor: null } }) : route.abort());
  stage = 'Hindi dashboard, history, reports and trends empty states';
  for (const [route, key] of [['/', 'No health observations yet.'], ['/history', 'No observations match this view. Upload and review a report or add a supported measurement.'], ['/reports', 'No reports uploaded yet.'], ['/trends', 'Every trend starts with observations.']]) {
    await page.goto(origin + route); await visible(page, key); await screenshot(route === '/' ? 'dashboard-hi.png' : route.slice(1) + '-hi.png');
  }
  pass();
  stage = 'Hindi report validation and safe error/loading states';
  await page.goto(origin + '/reports'); await visible(page, 'Choose a file');
  await page.locator('#report-file').setInputFiles({ name: 'synthetic.txt', mimeType: 'text/plain', buffer: Buffer.from('Synthetic only') });
  await visible(page, 'Choose a PDF, JPEG or PNG with a matching filename and file type.');
  await page.route('**/api/reports', route => route.fulfill({ status: 503, json: { code: 'storage_unavailable' } }));
  await page.reload(); await visible(page, 'Private file storage is temporarily unavailable. Please try again shortly.');
  let release; const delayed = new Promise(resolve => { release = resolve; });
  await page.route('**/api/reports', async route => { await delayed; await route.fulfill({ json: { reports: [], next_cursor: null } }); });
  await page.reload(); await visible(page, 'Loading your reports…'); release(); await visible(page, 'No reports uploaded yet.'); pass();
  stage = 'Hindi report extraction and review preserve original multilingual source text';
  const reportId = crypto.randomUUID(), runId = crypto.randomUUID(), parameterId = crypto.randomUUID();
  const instant = '2026-09-25T00:00:00Z';
  const sourceText = 'Hemoglobin 13.20 g/dL 12–15\nVitamin D 18 ng/mL 30–100\nरिपोर्ट स्रोत <5 >10 0.4–4.0 1:80';
  const run = { id: runId, report_id: reportId, status: 'completed', attempt: 1, created_at: instant, started_at: instant, finished_at: instant, deadline_at: instant, error_category: null, processor: 'synthetic-browser-fixture', page_count: 1 };
  const parameterRun = { ...run, id: parameterId, source_run_id: runId, extractor_version: 'synthetic', rules_version: 'synthetic', candidate_count: 1, warnings: [] };
  const fields = { ...fixture.messages[0].answer.sources[0].fields, original_label: 'Hemoglobin', raw_value: '13.20', numeric_value: '13.20', original_unit: 'g/dL', raw_reference: '12–15', canonical_metric: 'hemoglobin' };
  const quote = 'Hemoglobin 13.20 g/dL 12–15';
  const candidate = { id: crypto.randomUUID(), run_id: parameterId, ordinal: 1, content: { fields, page_number: 1, source_text: quote, source_start: 0, source_end: [...quote].length, source_method: 'native_text', certainty: 'needs_review', warnings: [], ocr_confidence: null }, reviews: [] };
  await page.unroute('**/api/reports');
  await page.route('**/api/reports', route => route.fulfill({ json: { reports: [{ id: reportId, original_filename: 'synthetic-multilingual.pdf', media_type: 'application/pdf', size_bytes: 1000, status: 'uploaded', created_at: instant, updated_at: instant, error_category: null }], next_cursor: null } }));
  await page.route(`**/api/reports/${reportId}/processing`, route => route.fulfill({ json: { runs: [run] } }));
  await page.route(`**/api/reports/${reportId}/extraction?*`, route => route.fulfill({ json: { run, pages: [{ page_number: 1, text: sourceText, method: 'native_text', confidence: null, warnings: [] }] } }));
  await page.route(`**/api/reports/${reportId}/parameter-processing`, route => route.fulfill({ json: { runs: [parameterRun] } }));
  await page.route(`**/api/reports/${reportId}/parameters?*`, route => route.fulfill({ json: { run: parameterRun, candidates: [candidate] } }));
  await page.reload(); await page.getByRole('heading', { name: 'synthetic-multilingual.pdf', exact: true }).waitFor();
  await page.getByRole('button', { name: hi['Text extraction'], exact: true }).click();
  await page.getByRole('button', { name: hi['View extracted text · Attempt'] + ' 1', exact: true }).click();
  assert.equal(await page.locator('.extracted-page pre').textContent(), sourceText);
  await page.getByRole('button', { name: hi['Parameter candidates'], exact: true }).click();
  await page.getByRole('button', { name: hi['Inspect parameter attempt'] + ' 1', exact: true }).click();
  await visible(page, 'Needs review');
  await page.getByText(hi['Inspect source and machine result'], { exact: true }).click();
  assert.equal(await page.locator('.parameter-candidate pre').first().textContent(), quote);
  await page.getByRole('button', { name: hi['Correct fields'], exact: true }).click();
  assert.equal(await page.locator('input[name="raw_value"]').inputValue(), '13.20');
  assert.equal(await page.locator('input[name="original_unit"]').inputValue(), 'g/dL');
  await screenshot('report-source-hi-mobile.png'); pass();
  stage = 'Hindi trend semantics, chart, exact values and non-causation';
  await page.unroute('**/api/trends/*?*');
  await page.route('**/api/trends/*?*', route => route.fulfill({ json: trend }));
  await page.unroute('**/api/trends/catalog');
  await page.route('**/api/trends/catalog', route => route.fulfill({ json: { ...emptyCatalog, series: [{ metric: trend.metric, unit: trend.unit, observation_count: trend.points.length, supported_unit: true }] } }));
  await page.goto(origin + '/trends'); await visible(page, 'Measurement changes');
  await visible(page, 'Correlation describes an association in the available measurements and does not establish cause and effect.');
  await page.locator('.trend-data summary').click();
  await page.getByRole('cell', { name: `${trend.points[0].raw_value} ${trend.unit}`, exact: true }).first().waitFor();
  await screenshot('trends-hi-mobile.png'); pass();
  stage = 'mixed legacy English, Hindi and Hinglish saved answers keep exact evidence';
  await page.route('**/api/assistant/conversations', route => route.fulfill({ json: { conversations: [fixture.conversation], provider_available: true } }));
  await page.route(`**/api/assistant/conversations/${fixture.conversation.id}`, route => route.fulfill({ json: fixture }));
  await page.goto(origin + '/assistant');
  await page.getByRole('button', { name: new RegExp(hi['Health conversation']) }).click();
  for (const m of fixture.messages) await page.getByText(m.answer.text, { exact: true }).first().waitFor();
  const saved = await page.locator('.assistant-message > p[lang]').allTextContents();
  assert.equal(saved.length, 4);
  assert.equal(await page.locator('.assistant-message > p[lang="hi-Latn"]').count(), 1);
  for (const detail of await page.locator('.assistant-evidence').all()) await detail.locator('summary').click();
  await page.getByText(hi['Measurement date unknown'], { exact: false }).first().waitFor();
  assert.equal(await page.getByText(/Synthetic · 18 ng\/mL/).count(), 3);
  assert.equal(await page.getByText(/30–100/).count(), 3);
  await screenshot('assistant-hi-mobile.png'); pass();
  stage = 'cross-tab UI switch preserves conversation, draft and saved answer languages';
  await page.locator('#assistant-question').fill('Unsent synthetic draft 13.20 g/dL');
  editor = await aContext.newPage(); await editor.goto(origin + '/settings'); await editor.locator('#preferred-language').waitFor();
  await save(editor, 'en', 'en');
  await page.waitForFunction(() => document.documentElement.lang === 'en');
  assert.equal(await page.locator('#assistant-question').inputValue(), 'Unsent synthetic draft 13.20 g/dL');
  assert.deepEqual(await page.locator('.assistant-message > p[lang]').allTextContents(), saved);
  assert.equal(sends, 0); pass();
  stage = 'Hindi suggestions only fill the composer and never generate';
  await save(editor, 'hi', 'hi'); await page.waitForFunction(() => document.documentElement.lang === 'hi');
  await page.getByRole('button', { name: hi['Explain my latest report.'], exact: true }).click();
  assert.equal(await page.locator('#assistant-question').inputValue(), hi['Explain my latest report.']);
  assert.equal(sends, 0); pass();
  stage = 'browser runtime, no live provider calls, no implicit generation';
  assert.equal(errors, 0); assert.equal(ai, 0); assert.equal(sends, 0); pass();
  fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify({ checks, errors, ai, sends, syntheticEvidenceOnly: true }, null, 2));
})().catch(error => { console.error('FAIL: ' + stage + ' (' + error.name + ')'); process.exitCode = 1; }).finally(async () => {
  for (const [p, body] of originals) {
    try { assert.equal((await write(p, 'PATCH', '/settings', body)).status, 200); }
    catch { console.error('Cleanup: preferences need restoration'); process.exitCode = 1; }
    try { await write(p, 'POST', '/auth/logout', {}); } catch { /* no secrets or bodies logged */ }
  }
  await browser?.close();
});
