import { expect, test, type Page, type Route } from '@playwright/test'

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

async function mockSignedOut(page: Page) {
  await page.route('**/healthz', (route) => json(route, {
    status: 'ok',
    service: 'GoreeCloud Notify',
    version: '0.2.0',
  }))

  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/meta') {
      return json(route, {
        service: 'GoreeCloud Notify',
        version: '0.2.0',
        build_revision: 'dd22a7ad0765c8ca62b401749265594bb0a06e23',
        milestone: 1,
        development_milestone: 4,
        production: false,
        release_stage: 'release_candidate',
        implemented_engine: ['Glaze UI appearance resilience'],
        next_milestone: 'Production Acceptance',
        next_slice: 'Target deployment and controlled acceptance',
      })
    }
    if (path === '/api/v1/me') return json(route, { detail: 'not authenticated' }, 401)
    return json(route, { detail: `Unhandled Glaze resilience route: ${path}` }, 500)
  })
}

test('Auto appearance uses the light Glaze background on a light operating-system theme', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' })
  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system')

  const appearance = await page.evaluate(() => ({
    background: getComputedStyle(document.body).backgroundImage,
    backgroundToken: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim(),
  }))

  expect(appearance.backgroundToken).toBe('#edf3fa')
  expect(appearance.background).toContain('rgba(255, 255, 255, 0.9)')
  expect(appearance.background).not.toContain('rgba(67, 90, 123, 0.42)')
})

test('Auto appearance follows a dark operating-system theme', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system')

  const appearance = await page.evaluate(() => ({
    background: getComputedStyle(document.body).backgroundImage,
    backgroundToken: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim(),
  }))

  expect(appearance.backgroundToken).toBe('#0e151f')
  expect(appearance.background).toContain('rgba(67, 90, 123, 0.42)')
})

test('blocked browser preference storage does not prevent Notify from opening', async ({ page }) => {
  await page.addInitScript(() => {
    const blocked = () => {
      throw new DOMException('Browser storage blocked for resilience validation', 'SecurityError')
    }
    Storage.prototype.getItem = blocked
    Storage.prototype.setItem = blocked
    Storage.prototype.removeItem = blocked
  })

  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'system')
  await expect(page.getByText('One calm place for operational and GoreeCloud application notifications')).toBeVisible()
})

test('Notify applies its Glaze UI 1.6.0 presentation-only source contract', async ({ page }) => {
  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.locator('html')).toHaveAttribute('data-glaze-ui', '1.6.0')
  await expect(page.locator('html')).toHaveAttribute('data-glaze-ui-target', '1.6.0')
  await expect(page.locator('html')).toHaveAttribute('data-glaze-ui-status', 'source-adoption-candidate')
  await expect(page.locator('html')).toHaveAttribute('data-glaze-authority', 'presentation-only')
  await expect(page.locator('html')).toHaveAttribute('data-glaze-service', 'available')
  await expect(page.locator('html')).toHaveAttribute('data-glaze-realtime', 'disabled')

  const contract = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement)
    const button = document.querySelector<HTMLButtonElement>('button.primary-button')
    return {
      targetMin: root.getPropertyValue('--glaze-target-min').trim(),
      targetTouchAssistance: root.getPropertyValue('--glaze-target-touch-assistance').trim(),
      targetFarView: root.getPropertyValue('--glaze-target-far-view').trim(),
      materialClarity: root.getPropertyValue('--glaze-material-clarity').trim(),
      motionStandard: root.getPropertyValue('--glaze-motion-standard').trim(),
      radiusControl: root.getPropertyValue('--glaze-radius-control').trim(),
      version: root.getPropertyValue('--glaze-ui-version').trim(),
      paneMode: document.documentElement.dataset.glazePaneMode,
      systemAlerts: document.documentElement.dataset.glazeSystemAlerts,
      buttonHeight: button?.getBoundingClientRect().height ?? 0,
      reviewedAnchor: document.documentElement.dataset.glazeReviewedAnchor,
      qualificationAnchor: document.documentElement.dataset.glazeQualificationAnchor,
    }
  })

  expect(contract.targetMin).toBe('48px')
  expect(contract.targetTouchAssistance).toBe('56px')
  expect(contract.targetFarView).toBe('56px')
  expect(contract.materialClarity).toBe('balanced')
  expect(['220ms', '.22s']).toContain(contract.motionStandard)
  expect(contract.radiusControl).toBe('16px')
  expect(contract.version).toBe('"1.6.0"')
  expect(['single', 'stacked', 'split']).toContain(contract.paneMode)
  expect(['permission-required', 'restricted', 'unsupported', 'disabled', 'available']).toContain(contract.systemAlerts)
  expect(contract.buttonHeight).toBeGreaterThanOrEqual(48)
  expect(contract.reviewedAnchor).toBe('ee1032a0822ab8e103f8afe48e5c1859fde65cc9')
  expect(contract.qualificationAnchor).toBe('5b59d0e36950d737dba35b58ae58058684e0831b')
})

test('Glaze UI accessibility precedence reduces motion without granting operational authority', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await mockSignedOut(page)
  await page.goto('/')

  await expect(page.locator('html')).toHaveAttribute('data-glaze-motion', 'reduced')
  await expect(page.locator('html')).toHaveAttribute('data-glaze-authority', 'presentation-only')

  const state = await page.evaluate(() => ({
    motionStandard: getComputedStyle(document.documentElement).getPropertyValue('--glaze-motion-standard').trim(),
    service: document.documentElement.dataset.glazeService,
    realtime: document.documentElement.dataset.glazeRealtime,
  }))
  expect(state.motionStandard).toBe('.01ms')
  expect(state.service).toBe('available')
  expect(state.realtime).toBe('disabled')
})
