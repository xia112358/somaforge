import { expect, test } from '@playwright/test';

const env = (globalThis as any).process?.env ?? {};
const motionId = env.MOTION_EDIT_E2E_MOTION_ID as string | undefined;
test.skip(!motionId, 'requires a real contact-editor server and registered motion');

async function openEditor(page: any) {
  const response = await page.request.post('/api/session/load', { data: { motion_id: motionId } });
  expect(response.ok()).toBeTruthy();
  await page.goto('/');
  await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
}

test('display layers remain independent, frames are bounded, playback reuses geometry', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await openEditor(page);
  await page.locator('[data-tab="display"]').click();
  await page.locator('#surfaceToggle').check();
  await page.locator('#terrainToggle').uncheck();
  await expect(page.locator('#scene')).toHaveAttribute('data-surfaces-visible', 'true');
  await expect(page.locator('#scene')).toHaveAttribute('data-terrain-visible', 'false');
  await page.locator('#terrainToggle').check();
  await page.locator('#surfaceToggle').uncheck();
  await expect(page.locator('#scene')).toHaveAttribute('data-surfaces-visible', 'false');
  await expect(page.locator('#scene')).toHaveAttribute('data-terrain-visible', 'true');
  await page.locator('[data-tab="contact"]').click();
  await page.locator('#episodeOptions summary').click();
  await page.locator('#currentOnly').uncheck();
  await page.waitForTimeout(150);
  const before = Number(await page.locator('#scene').getAttribute('data-geometry-count'));
  for (let frame = 0; frame < 80; frame++) {
    await page.locator('#frameInput').fill(String(frame));
    await page.locator('#frameInput').dispatchEvent('change');
  }
  await page.waitForTimeout(150);
  expect(Number(await page.locator('#scene').getAttribute('data-geometry-count'))).toBe(before);
  await page.locator('#frameInput').fill('999999');
  await page.locator('#frameInput').dispatchEvent('change');
  expect(await page.locator('#frameInput').inputValue()).toBe(await page.locator('#frameInput').getAttribute('max'));
  await page.locator('#fpsInput').fill('');
  await page.locator('#fpsInput').dispatchEvent('change');
  expect(Number(await page.locator('#fpsInput').inputValue())).toBeGreaterThan(0);
  await page.locator('#fpsInput').fill('999');
  await page.locator('#fpsInput').dispatchEvent('change');
  await expect(page.locator('#fpsInput')).toHaveValue('240');
  await page.locator('#playBtn').click();
  await page.waitForTimeout(200);
  await page.locator('#playBtn').click();
  await page.locator('#episodeSelect').selectOption({ index: 1 });
  const marker = await page.locator('#scene').evaluate((canvas: HTMLCanvasElement) => {
    const rect = canvas.getBoundingClientRect();
    return { x: rect.left + Number(canvas.dataset.selectedHandleX) * rect.width, y: rect.top + Number(canvas.dataset.selectedHandleY) * rect.height };
  });
  await page.locator('[data-tab="display"]').click();
  await page.locator('#handleToggle').uncheck();
  await page.mouse.move(marker.x, marker.y);
  await page.mouse.down();
  await page.mouse.up();
  await expect(page.locator('#scene')).toHaveAttribute('data-drag-state', 'miss');
  expect(errors).toEqual([]);
});

test('registered motion picker searches the same motion identities', async ({ page }) => {
  await openEditor(page);
  await page.locator('#openMotionBtn').click();
  await expect(page.locator('#motionPicker')).toBeVisible();
  await page.locator('#motionSearch').fill('nonexistent-motion-xyz');
  await expect(page.locator('#motionPickerList')).toHaveText('没有匹配的轨迹');
  await page.locator('#motionSearch').fill(motionId!);
  await expect(page.locator('.motion-picker-item').first()).toContainText(motionId!);
  await page.locator('.motion-picker-item').first().click();
  await expect(page.locator('#motionPicker')).not.toBeVisible();
  await expect(page.locator('#motionLabel')).toHaveText(motionId!);
});

test('session load errors persist and do not silently open a different motion', async ({ page }) => {
  let loads = 0;
  page.on('request', request => { if (request.url().endsWith('/api/session/load')) loads++; });
  await page.route('**/api/session', route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'session load failed for acceptance' }) }));
  await page.goto('/');
  await expect(page.locator('#sceneStatus')).toContainText('session load failed for acceptance');
  await page.waitForTimeout(3200);
  await expect(page.locator('#sceneStatus')).toBeVisible();
  await expect(page.locator('#retryLoad')).toBeVisible();
  expect(loads).toBe(0);
  await page.unroute('**/api/session');
  await page.locator('#retryLoad').click();
  await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
});

test('generate sends the strict current contract once, then opens a read-only real candidate', async ({ page }, testInfo) => {
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await openEditor(page);
  const current = await (await page.request.get('/api/session')).json();
  const handle = current.edit_handles[0];
  const requested = handle.world_position.map((v: number, i: number) => v + .004 * handle.surface_tangent_u[i]);
  const moved = await page.request.post('/api/session/move-handle', { data: { handle_id: handle.handle_id, requested_world_position: requested, mode: 'clamp' } });
  expect(moved.ok()).toBeTruthy();
  await page.reload();
  await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
  await page.locator('[data-tab="output"]').click();
  await page.locator('.output-settings summary').click();
  await page.locator('#overwriteOutput').check();
  const bodies: unknown[] = [];
  await page.route('**/api/session/generate', async route => {
    bodies.push(route.request().postDataJSON());
    await new Promise(resolve => setTimeout(resolve, 300));
    const response = await route.fetch();
    await route.fulfill({ response });
  });
  const response = page.waitForResponse(response => response.url().endsWith('/api/session/generate'));
  await page.locator('#generateBtn').evaluate((button: HTMLButtonElement) => { button.click(); button.click(); });
  expect((await response).ok()).toBeTruthy();
  expect(bodies).toEqual([{}]);
  await expect(page.locator('#generateBtn')).toBeDisabled();
  await page.locator('[data-tab="display"]').click();
  await expect(page.locator('#terrainToggle')).toBeEnabled();
  await page.locator('#terrainToggle').uncheck();
  await expect(page.locator('#motionLabel')).not.toHaveText(motionId!, { timeout: 180_000 });
  await expect(page.locator('#sceneStatus')).toContainText('Generated candidate opened', { timeout: 45_000 });
  await expect(page.locator('#scene')).toHaveAttribute('data-terrain-visible', 'false');
  expect(Number(await page.locator('#scene').getAttribute('data-robot-meshes'))).toBeGreaterThan(30);
  await expect(page.locator('#saveBtn')).toBeDisabled();
  await page.locator('[data-tab="contact"]').click();
  await expect(page.locator('#playbackNotice')).toBeVisible();
  await expect(page.locator('.anchor-browser')).not.toBeVisible();
  await page.locator('#playBtn').click();
  await page.waitForTimeout(200);
  expect(Number(await page.locator('#frameInput').inputValue())).toBeGreaterThan(0);
  await page.locator('#playBtn').click();
  await page.locator('[data-tab="display"]').click();
  await page.locator('#terrainToggle').check();
  await page.screenshot({ path: testInfo.outputPath('generated-candidate.png'), fullPage: true });
  await page.locator('#openMotionBtn').click();
  await page.locator('#motionSearch').fill(motionId!);
  await page.locator('.motion-picker-item').first().click();
  await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
  await expect(page.locator('#saveBtn')).toBeEnabled();
  expect(errors).toEqual([]);
});
