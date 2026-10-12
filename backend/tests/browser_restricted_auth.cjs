// Offline release-build UI acceptance. Every API request is intercepted; no backend needed.
const assert = require('node:assert/strict')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
let stage = 'browser_launch'

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  let checks = 0
  try {
    for (const policy of [false, true, 'unavailable', 'malformed']) {
      stage = `policy_${policy}`
      const context = await browser.newContext()
      let policyRequests = 0
      const unexpected = []
      try {
        await context.route('**/*', async route => {
          const url = new URL(route.request().url())
          if (url.origin !== 'http://127.0.0.1:5173') {
            unexpected.push('non-loopback request')
            return route.abort()
          }
          if (!url.pathname.startsWith('/api/')) return route.continue()
          if (url.pathname === '/api/auth/policy') {
            policyRequests++
            return route.fulfill({ status: policy === 'unavailable' ? 503 : 200,
              json: policy === 'malformed' ? {} : { public_signup_enabled: policy, public_recovery_enabled: false } })
          }
          if (url.pathname === '/api/auth/csrf') return route.fulfill({ json: { csrf_token: 'synthetic-csrf' } })
          if (['/api/auth/me', '/api/auth/refresh'].includes(url.pathname)) {
            return route.fulfill({ status: 401, json: { code: 'unauthenticated' } })
          }
          unexpected.push('unexpected API request')
          return route.abort()
        })
        const page = await context.newPage()
        await page.goto('http://127.0.0.1:5173/auth/sign-in')
        await page.getByLabel('Password', { exact: true }).waitFor()
        await page.waitForLoadState('networkidle')
        assert.equal(await page.getByRole('button', { name: 'Sign in', exact: true }).isEnabled(), true)
        assert.equal(await page.getByRole('link', { name: 'Create an account', exact: true }).count(), policy === true ? 1 : 0)
        assert.equal(policyRequests, 1)
        checks++
        for (const path of ['sign-up', 'verify-email']) {
          await page.goto(`http://127.0.0.1:5173/auth/${path}`)
          await page.waitForLoadState('networkidle')
          if (policy === true) {
            await page.getByLabel(path === 'sign-up' ? 'Password' : 'Confirmation code', { exact: true }).waitFor()
          } else {
            await page.getByRole('heading', { name: 'Registration unavailable', exact: true }).waitFor()
            assert.equal(await page.locator('input').count(), 0)
            assert.equal(await page.getByRole('link', { name: 'Sign in', exact: true }).count(), 1)
          }
          checks++
        }
        assert.equal(policyRequests, 3)
        assert.deepEqual(unexpected, [])
      } finally {
        await context.close()
      }
    }
    console.log(JSON.stringify({ restricted_auth_ui: 'PASS', checks, live_requests: 0 }))
  } finally {
    await browser.close()
  }
}

main().catch(() => { console.error(`Restricted auth UI acceptance FAILED at ${stage} (synthetic only).`); process.exitCode = 1 })
