import { expect, test } from '@playwright/test';

const e2eAssetId = (globalThis as any).process?.env?.MOTION_EDIT_E2E_ASSET_ID as string | undefined;
test.skip(!e2eAssetId, 'set MOTION_EDIT_E2E_ASSET_ID to run the real-asset browser test');

for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
  test(`renders real contact editor at ${viewport.width}px`, async ({ page }, testInfo) => {
    page.on('console', message => { if (message.type() === 'error') console.log(`browser console: ${message.text()}`); });
    page.on('pageerror', error => console.log(`browser error: ${error.message}`));
    page.on('requestfailed', request => console.log(`request failed: ${request.url()} ${request.failure()?.errorText}`));
    page.on('response', response => { if (response.status() >= 400) console.log(`response ${response.status()}: ${response.url()}`); });
    await page.setViewportSize(viewport);
    await page.goto('/');
    await page.locator('#assetSelect').selectOption(e2eAssetId!);
    await page.locator('#loadBtn').click();
    await expect(page.locator('#motionLabel')).not.toHaveText('No motion', { timeout: 45_000 });
    await expect(page.locator('#anchorCount')).toHaveText(/^[1-9][0-9]* anchors$/);
    await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
    const canvas = page.locator('#scene');
    await expect(canvas).toBeVisible();
    expect(Number(await canvas.getAttribute('data-robot-meshes'))).toBeGreaterThan(30);
    expect(await canvas.getAttribute('data-contact-marker')).toBe('surface-disk');
    const box = await canvas.boundingBox();
    expect(box?.width).toBeGreaterThan(300);
    expect(box?.height).toBeGreaterThan(250);
    const pixels = await canvas.evaluate((element: HTMLCanvasElement) => {
      const gl = element.getContext('webgl2') || element.getContext('webgl');
      if (!gl) return { nonzero: 0, total: 0 };
      const width = gl.drawingBufferWidth;
      const height = gl.drawingBufferHeight;
      const data = new Uint8Array(width * height * 4);
      gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, data);
      let nonzero = 0;
      for (let i = 0; i < data.length; i += 4) if (data[i] || data[i + 1] || data[i + 2]) nonzero++;
      return { nonzero, total: width * height };
    });
    expect(pixels.total).toBeGreaterThan(0);
    expect(pixels.nonzero / pixels.total).toBeGreaterThan(0.2);
    const before = await page.locator('#frameInput').inputValue();
    await page.locator('#playBtn').click();
    await page.waitForTimeout(500);
    expect(await page.locator('#frameInput').inputValue()).not.toBe(before);
    await expect(page.locator('#statusFilter')).toBeVisible();
    await expect(page.locator('#targetU')).toBeVisible();
    await page.locator('#nextAnchor').click();
    await expect(page.locator('#selection')).not.toHaveClass(/empty/);
    await expect(page.locator('#precisionEditor')).not.toHaveClass(/disabled/);
    if (viewport.width === 1440) {
      const panel = page.locator('.timeline-panel');
      const beforeHeight = (await panel.boundingBox())!.height;
      const handle = page.locator('#timelineResizer');
      const handleBox = await handle.boundingBox();
      await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y + 4);
      await page.mouse.down();
      await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y - 36);
      await page.mouse.up();
      expect((await panel.boundingBox())!.height).toBeGreaterThan(beforeHeight + 25);
    }
    await page.locator('[data-tab="display"]').click();
    await expect(page.locator('#forceScale')).toBeVisible();
    await page.locator('[data-tab="output"]').click();
    await expect(page.locator('#planPath')).toHaveValue(/contact_edit_plan\.json$/);
    await page.locator('[data-tab="contact"]').click();
    await page.screenshot({ path: testInfo.outputPath(`motion-edit-${viewport.width}.png`), fullPage: true });
  });
}
