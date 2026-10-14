import { expect, test } from '@playwright/test';

const motionId = (globalThis as any).process?.env?.MOTION_EDIT_E2E_MOTION_ID as string | undefined;
test.skip(!motionId, 'requires a real contact-editor server and registered motion');

async function openEpisodes(page: any, cuts = true) {
  const response = await page.request.post('/api/session/load', { data: { motion_id: motionId } });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  expect(payload.edit_handles.length).toBeGreaterThan(0);
  expect(payload.qpos.length).toBeGreaterThan(80);
  const base = payload.edit_handles[0];
  payload.edit_handles = [
    { ...base, handle_id: 'episode_A', start_frame: 0, end_frame: 10, metadata: { ...base.metadata, surface_editor_status: 'bound' } },
    { ...base, handle_id: 'episode_B', start_frame: 0, end_frame: 20, metadata: { ...base.metadata, surface_editor_status: 'edited' } },
    { ...base, handle_id: 'episode_C', start_frame: 30, end_frame: 50, metadata: { ...base.metadata, surface_editor_status: 'bound' } },
  ];
  payload.graph.transitions = cuts ? [{ start_frame: 12, end_frame: 22, metadata: { stable_anchor_frames: [12, 18, 21, -1, payload.qpos.length] } }] : [];
  await page.route('**/api/session', (route: any) => route.fulfill({ json: payload }));
  await page.goto('/');
  await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
}

async function relativeEpisode(page: any, direction = 1) {
  await page.evaluate(() => (document.activeElement as HTMLElement)?.blur());
  await page.keyboard.press(direction > 0 ? 'BracketRight' : 'BracketLeft');
}

async function frame(page: any, value: number) {
  await page.locator('#frameInput').fill(String(value));
  await page.locator('#frameInput').dispatchEvent('change');
}

for (const width of [1440, 390]) {
  test(`cut buttons jump between cut points and pause playback at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 960 });
    await openEpisodes(page);
    await expect(page.getByRole('button', { name: '下一切分点' })).toBeVisible();
    await page.locator('#nextCut').click();
    await expect(page.locator('#frameInput')).toHaveValue('12');
    await page.locator('#nextCut').click();
    await expect(page.locator('#frameInput')).toHaveValue('18');
    await page.locator('#prevCut').click();
    await expect(page.locator('#frameInput')).toHaveValue('12');
    await page.locator('#prevCut').click();
    await expect(page.locator('#frameInput')).toHaveValue('21');
    await page.locator('#playBtn').click();
    await page.locator('#nextCut').click();
    await expect(page.locator('#frameInput')).toHaveValue('12');
    await page.waitForTimeout(200);
    await expect(page.locator('#frameInput')).toHaveValue('12');
    await expect(page.locator('#episodeSelect')).toHaveValue('');
    await page.locator('#episodeSelect').selectOption('episode_C');
    await expect(page.locator('#frameInput')).toHaveValue('30');
  });

  test(`episode navigation reaches future intervals at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 960 });
    const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
    await openEpisodes(page);
    await expect(page.locator('#currentOnly')).toBeChecked();
    await relativeEpisode(page);
    await expect(page.locator('#selection')).toContainText('episode_A');
    await relativeEpisode(page);
    await expect(page.locator('#selection')).toContainText('episode_B');
    await page.locator('#episodeSelect').selectOption('episode_C');
    await expect(page.locator('#selection')).toContainText('episode_C');
    await expect(page.locator('#frameInput')).toHaveValue('30');
    await expect(page.locator('#episodeBrowseStatus')).toContainText('3 matched · 1 shown · Selected 3/3');
    await relativeEpisode(page);
    await expect(page.locator('#selection')).toContainText('episode_A');
    await relativeEpisode(page, -1);
    await expect(page.locator('#selection')).toContainText('episode_C');
    await frame(page, 25);
    await expect(page.locator('#selection')).toHaveText('None');
    await expect(page.locator('#episodeSelect')).toBeEnabled();
    await relativeEpisode(page);
    await expect(page.locator('#selection')).toContainText('episode_C');
    await frame(page, 25);
    await relativeEpisode(page, -1);
    await expect(page.locator('#selection')).toContainText('episode_B');
    const bounds = await page.locator('#episodeSelect').boundingBox();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
    expect(errors).toEqual([]);
  });
}

test('cut navigation is disabled when no cut points are provided', async ({ page }) => {
  await openEpisodes(page, false);
  await expect(page.locator('#prevCut')).toBeDisabled();
  await expect(page.locator('#nextCut')).toBeDisabled();
  await expect(page.locator('#episodeSelect')).toBeEnabled();
});

test('empty and edited filters reconcile buttons, selection and visible markers', async ({ page }) => {
  await openEpisodes(page);
  await relativeEpisode(page);
  await page.locator('#episodeOptions summary').click();
  await page.locator('#anchorSearch').fill('missing-episode');
  await expect(page.locator('#episodeBrowseStatus')).toHaveText('No matching episodes');
  await expect(page.locator('#episodeSelect')).toBeDisabled();
  await expect(page.locator('#selection')).toHaveText('None');
  await expect(page.locator('#positionOffset')).toHaveClass(/disabled/);
  await expect(page.locator('#scene')).not.toHaveAttribute('data-selected-handle-id');
  await page.locator('#anchorSearch').fill('episode_C');
  await expect(page.locator('#episodeBrowseStatus')).toHaveText('1 matched · 0 shown');
  await expect(page.locator('#episodeSelect')).toBeEnabled();
  await relativeEpisode(page);
  await expect(page.locator('#frameInput')).toHaveValue('30');
  await expect(page.locator('#scene')).toHaveAttribute('data-selected-handle-id', 'episode_C');
  await page.locator('#anchorSearch').fill('');
  await page.locator('#statusFilter').selectOption('edited');
  await expect(page.locator('#selection')).toHaveText('None');
  await relativeEpisode(page);
  await expect(page.locator('#selection')).toContainText('episode_B');
  await expect(page.locator('#episodeBrowseStatus')).toContainText('1 matched · 1 shown');
  // Both controls remain usable even after the matching episode has left the frame.
  await page.locator('#currentOnly').uncheck();
  await frame(page, 25);
  await expect(page.locator('#selection')).toContainText('episode_B');
  await page.locator('#currentOnly').check();
  await expect(page.locator('#selection')).toHaveText('None');
  await expect(page.locator('#episodeSelect')).toBeEnabled();
});

test('episode navigation pauses playback and does not change drag boundary mode', async ({ page }) => {
  await openEpisodes(page);
  await page.locator('#episodeOptions summary').click();
  await page.locator('#modeSelect').selectOption('clamp');
  await page.locator('#playBtn').click();
  await relativeEpisode(page);
  const selectedFrame = await page.locator('#frameInput').inputValue();
  await page.waitForTimeout(200);
  await expect(page.locator('#frameInput')).toHaveValue(selectedFrame);
  await expect(page.locator('#modeSelect')).toHaveValue('clamp');
});

test('Next traverses every actual episode exactly once before wrapping', async ({ page }) => {
  test.setTimeout(120_000);
  const response = await page.request.post('/api/session/load', { data: { motion_id: motionId } });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  expect(payload.edit_handles.length).toBeGreaterThan(2);
  await page.goto('/');
  await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
  await expect(page.locator('#currentOnly')).toBeChecked();
  for (const handle of payload.edit_handles) {
    await relativeEpisode(page);
    await expect(page.locator('#scene')).toHaveAttribute('data-selected-handle-id', handle.handle_id);
    await expect(page.locator('#frameInput')).toHaveValue(String(handle.start_frame));
  }
  await relativeEpisode(page);
  await expect(page.locator('#scene')).toHaveAttribute('data-selected-handle-id', payload.edit_handles[0].handle_id);
  await relativeEpisode(page, -1);
  await expect(page.locator('#scene')).toHaveAttribute('data-selected-handle-id', payload.edit_handles.at(-1).handle_id);
});
