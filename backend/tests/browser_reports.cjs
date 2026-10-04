// Development acceptance: dedicated users and neutral fixtures; never log credentials.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
assert.equal(process.env.RUN_SUPABASE_INTEGRATION, '1');
assert.equal(process.env.RUN_AI_INTEGRATION, undefined);
const root = path.resolve(__dirname, '../..');
const python = (process.env.QA_PYTHON || path.join(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python'));
const output=path.join(root,'.cache/qa/phase3'); fs.mkdirSync(output,{recursive:true});
const config = JSON.parse(execFileSync(python, ['-c', 'import json; from dotenv import dotenv_values; print(json.dumps(dotenv_values(".env.integration")))'], { cwd: path.join(root, 'backend'), encoding: 'utf8' }));
assert.equal(config.DISPOSABLE_TEST_ACCOUNTS_CONFIRMED, '1');
const origin = config.TEST_APP_ORIGIN || 'http://127.0.0.1:5173';
assert.equal(new URL(origin).hostname, '127.0.0.1');
const fixtures = JSON.parse(execFileSync(python, ['-c', 'import json,base64; from tests.report_fixtures import valid_pdf,valid_png,valid_jpeg; print(json.dumps({"pdf":base64.b64encode(valid_pdf()).decode(),"png":base64.b64encode(valid_png()).decode(),"jpeg":base64.b64encode(valid_jpeg()).decode()}))'], { cwd: path.join(root,'backend'), encoding:'utf8' }));
const prefix = 'browser-' + Date.now() + '-';
const checks = [];
let stage = 'launch', checkpoint = '', browser, page, context, otherContext;
const created = new Set();
let errors = 0, providerRequests = 0;
function passed() { checks.push(stage); console.log('PASS: ' + stage); }
async function login(p, account) {
  await p.goto(origin + '/reports');
  await p.getByLabel('Email address', {exact:true}).fill(config[`TEST_USER_${account}_EMAIL`]);
  await p.getByLabel('Password', {exact:true}).fill(config[`TEST_USER_${account}_PASSWORD`]);
  await p.getByRole('button',{name:'Sign in',exact:true}).click();
  await p.getByRole('heading',{name:'Upload a report',exact:true}).waitFor({timeout:30000});
}
async function read(p, route) { return p.evaluate(async route => { const r=await fetch('/api'+route); return {status:r.status,body:await r.json()}; },route); }
async function write(p, method, route) { return p.evaluate(async ([method,route]) => { const c=await (await fetch('/api/auth/csrf')).json(); const r=await fetch('/api'+route,{method,headers:{'Content-Type':'application/json','X-CSRF-Token':c.csrf_token},body:'{}'}); return {status:r.status,body:await r.json()}; },[method,route]); }
async function select(name, mimeType, buffer) { await page.locator('#report-file').setInputFiles({name,mimeType,buffer}); }
function row(name) { return page.locator('.report-row').filter({has:page.getByRole('heading',{name,exact:true})}); }
async function upload(ext,mime) {
  const name=prefix+'neutral.'+ext, buffer=Buffer.from(fixtures[ext],'base64');
  await select(name,mime,buffer);
  await page.getByRole('checkbox').check();
  const reply=page.waitForResponse(r=>r.request().method()==='PUT' && new URL(r.url()).pathname.endsWith('/file'));
  await page.getByRole('button',{name:'Upload report',exact:true}).click();
  assert.equal((await reply).status(),200);
  await row(name).getByText('Uploaded',{exact:true}).waitFor({timeout:30000});
  return {name,buffer};
}
(async()=>{
  browser=await chromium.launch({channel:'chrome',headless:true});
  context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});
  otherContext=await browser.newContext({viewport:{width:1440,height:1100}});
  for (const c of [context,otherContext]) {
    c.on('page',p=>p.on('pageerror',()=>errors++));
    c.on('request',r=>{if(new URL(r.url()).hostname.endsWith('.supabase.co'))providerRequests++;});
  }
  page=await context.newPage(); const other=await otherContext.newPage();
  page.on('response',async r=>{
    if(r.request().method()==='POST' && new URL(r.url()).pathname==='/api/reports' && r.status()===201){
      const data=await r.json().catch(()=>null); if(data?.original_filename?.startsWith(prefix))created.add(data.id);
    }
  });
  stage='real browser login and Reports navigation'; await login(page,'A'); await login(other,'B'); passed();
  stage='PDF upload persists and downloads exact bytes';
  const pdf=await upload('pdf','application/pdf');
  const event=page.waitForEvent('download'); await row(pdf.name).getByRole('button',{name:'Download',exact:true}).click();
  const download=await event; assert.equal(download.suggestedFilename(),pdf.name);
  assert.deepEqual(fs.readFileSync(await download.path()),pdf.buffer); passed();
  stage='PNG and JPEG real uploads'; const png=await upload('png','image/png'); const jpeg=await upload('jpeg','image/jpeg'); passed();
  stage='history survives reload and isolates the other user';
  checkpoint='owner reload'; await page.reload(); await row(pdf.name).waitFor({timeout:30000});
  checkpoint='other reload'; await other.reload(); await other.getByRole('heading',{name:'Upload a report',exact:true}).waitFor({timeout:30000});
  checkpoint='owner exclusion';
  assert.equal(await other.getByText(pdf.name,{exact:true}).count(),0);
  checkpoint='foreign identifier checks';
  for(const id of created) { const status=(await read(other,'/reports/'+id)).status; if(status!==404) console.error('Foreign report HTTP status: '+status); assert.equal(status,404); } checkpoint=''; passed();
  stage='invalid extension and spoofed PDF rejected truthfully';
  await select(prefix+'invalid.exe','application/octet-stream',Buffer.from('safe test'));
  await page.getByText('Choose a PDF, JPEG or PNG with a matching filename and file type.',{exact:true}).waitFor();
  await select(prefix+'fake.pdf','application/pdf',Buffer.from('MZ safe synthetic fixture'));
  await page.getByRole('checkbox').check();
  const bad=page.waitForResponse(r=>r.request().method()==='PUT' && new URL(r.url()).pathname.endsWith('/file'));
  await page.getByRole('button',{name:'Upload report',exact:true}).click(); assert.equal((await bad).status(),422);
  await page.getByRole('button',{name:'Retry cancellation',exact:true}).click();
  await page.getByText('The upload was cancelled and its stored data was deleted.',{exact:true}).waitFor({timeout:30000}); passed();
  stage='cancel selected file without upload';
  await select(prefix+'clear.pdf','application/pdf',pdf.buffer);
  await page.getByRole('button',{name:'Clear selection',exact:true}).click();
  await page.getByText('File selection cleared. Nothing was uploaded.',{exact:true}).waitFor(); passed();
  stage='cancel in-progress browser transfer and clean reserved metadata';
  let release; const held=new Promise(resolve=>release=resolve); let intercepted;
  const reached=new Promise(resolve=>intercepted=resolve);
  const handler=async route=>{if(route.request().method()==='PUT'){intercepted();await held;await route.abort().catch(()=>{});}else await route.continue();};
  await page.route('**/api/reports/*/file',handler);
  await select(prefix+'cancel.pdf','application/pdf',pdf.buffer); await page.getByRole('checkbox').check();
  await page.getByRole('button',{name:'Upload report',exact:true}).click(); await reached;
  await page.getByRole('button',{name:'Cancel upload',exact:true}).click(); release();
  await page.getByText('The upload was cancelled and its stored data was deleted.',{exact:true}).waitFor({timeout:30000});
  await page.unroute('**/api/reports/*/file',handler); passed();
  stage='history refresh keeps selected file and mobile layout usable';
  await select(prefix+'selected.pdf','application/pdf',pdf.buffer);
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await page.getByRole('heading',{name:prefix+'selected.pdf',exact:true}).waitFor();
  await page.setViewportSize({width:375,height:900});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(output,'reports-mobile.png'),fullPage:true,mask:[page.locator('.account-bar__identity')]});
  await page.getByRole('button',{name:'Clear selection',exact:true}).click();
  await page.setViewportSize({width:1440,height:1100});
  await page.screenshot({path:path.join(output,'reports-desktop.png'),fullPage:true,mask:[page.locator('.account-bar__identity')]}); passed();
  stage='report deletion confirmation removes real files';
  for(const name of [pdf.name,png.name,jpeg.name]) {
    await row(name).getByRole('button',{name:'Delete report',exact:true}).click();
    await row(name).getByRole('button',{name:'Confirm delete',exact:true}).click();
    await row(name).waitFor({state:'detached',timeout:30000});
  } passed();
  stage='no browser provider credentials or errors';
  assert.equal(providerRequests,0); assert.equal(errors,0);
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  assert.equal(await page.evaluate(()=>document.cookie),''); passed();
  stage='logout protects Reports'; await page.getByRole('button',{name:'Sign out',exact:true}).click();
  await page.waitForURL('**/auth/sign-in'); await page.goto(origin+'/reports'); await page.waitForURL('**/auth/sign-in'); passed();
  await write(other,'POST','/auth/logout');
  fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({checks,passed:checks.length},null,2));
})().catch(error=>{console.error('FAIL: '+stage+' / '+checkpoint+' ('+error.name+'; contents suppressed)');process.exitCode=1;}).finally(async()=>{
  if(page && !page.isClosed() && created.size) {
    const me=await read(page,'/auth/me').catch(()=>null);
    if(me?.status===200) for(const id of created) await write(page,'DELETE','/reports/'+id).catch(()=>{});
  }
  if(browser)await browser.close();
});
