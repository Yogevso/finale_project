import { chromium } from 'playwright'

async function run() {
  const token = process.argv[2]
  if (!token) {
    console.error('Usage: node scripts/smoke_accept_invitation.mjs <invitation-token>')
    process.exit(2)
  }

  const baseUrl = process.env.BASE_URL || 'http://localhost:3000'
  const inviteUrl = `${baseUrl}/accept-invitation?token=${encodeURIComponent(token)}`
  const unique = Date.now()
  const username = `smoke_user_${unique}`

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()

  try {
    await page.goto(inviteUrl, { waitUntil: 'networkidle' })
    await page.getByRole('heading', { name: 'Accept Invitation' }).waitFor({ timeout: 20000 })

    await page.getByPlaceholder('Choose a username').fill(username)
    await page.getByPlaceholder('Enter your full name').fill('Smoke Invite User')
    await page.getByPlaceholder('Create a password').fill('SmokePass123!')
    await page.getByPlaceholder('Confirm your password').fill('SmokePass123!')

    await page.getByRole('button', { name: 'Create Account' }).click()

    await page
      .waitForURL(/\/(portal|dashboard|documents)(\/|$)|http:\/\/localhost:3000\/$/, {
        timeout: 30000,
      })
      .catch(() => undefined)

    const finalUrl = page.url()
    const isAuthenticatedRedirect =
      finalUrl.includes('/portal') ||
      finalUrl.includes('/dashboard') ||
      finalUrl.includes('/documents') ||
      finalUrl === `${baseUrl}/`

    const hasAccessToken = await page.evaluate(() => !!localStorage.getItem('token'))
    const hasRefreshToken = await page.evaluate(() => !!localStorage.getItem('refreshToken'))

    if (!isAuthenticatedRedirect || !hasAccessToken) {
      console.error(`INVITE_SMOKE_FAIL finalUrl=${finalUrl} token=${hasAccessToken}`)
      process.exit(1)
    }

    console.log(`INVITE_SMOKE_OK finalUrl=${finalUrl} token=${hasAccessToken} refresh=${hasRefreshToken}`)
  } finally {
    await browser.close()
  }
}

run().catch((error) => {
  console.error('INVITE_SMOKE_ERROR', error)
  process.exit(1)
})
