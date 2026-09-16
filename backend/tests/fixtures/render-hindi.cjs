// Synthetic fixture only. Requires Playwright and installed Chrome for script shaping.
// From repository root: node backend/tests/fixtures/render-hindi.cjs
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1800, height: 1500}});
    const input = path.resolve('.cache/qa/phase4/evaluation/fixtures/english.png');
    await page.setContent('<body style="margin:0"><canvas width="1800" height="1500"></canvas></body>');
    await page.evaluate(async data => {
      const canvas = document.querySelector('canvas');
      const context = canvas.getContext('2d');
      const image = new Image(); image.src = data; await image.decode();
      context.drawImage(image, 0, 0);
      context.font = '48px "Nirmala UI"'; context.fillStyle = 'black';
      context.fillText('हिंदी परीक्षण रिपोर्ट', 80, 1238);
      context.fillText('नमूना 13.2 g/dL', 80, 1348);
    }, 'data:image/png;base64,' + fs.readFileSync(input).toString('base64'));
    await page.locator('canvas').screenshot({path: path.join(__dirname, 'hindi-mixed.png')});
  } finally { await browser.close(); }
})().catch(() => { console.error('Synthetic Hindi fixture rendering failed'); process.exitCode = 1; });
