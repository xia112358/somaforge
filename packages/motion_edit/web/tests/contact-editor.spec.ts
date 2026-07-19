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
    const loadResponse = await page.request.post('/api/session/load', { data: { motion_asset_id: e2eAssetId } });
    expect(loadResponse.ok()).toBeTruthy();
    await page.goto('/');
    await expect(page.locator('#motionLabel')).not.toHaveText('No motion', { timeout: 45_000 });
    await expect(page.locator('#recentMotionList .recent-motion-item.active')).toHaveCount(1);
    expect(await page.locator('#recentMotionList .recent-motion-item').count()).toBeGreaterThanOrEqual(2);
    await expect(page.locator('#recentMotionList .recent-motion-copy strong').first()).not.toHaveText('');
    await expect(page.locator('.inspector > .recent-motion-dock')).toHaveCount(1);
    await expect(page.locator('.viewport > .recent-motion-dock')).toHaveCount(0);
    const inspectorBox = await page.locator('.inspector').boundingBox();
    const versionBox = await page.locator('.recent-motion-dock').boundingBox();
    expect(versionBox!.x).toBeGreaterThanOrEqual(inspectorBox!.x);
    expect(versionBox!.y + versionBox!.height).toBeLessThanOrEqual(inspectorBox!.y + inspectorBox!.height + 1);
    const generatedMotion = page.locator('#recentMotionList [data-motion-key^="version:"]').first();
    if (await generatedMotion.count()) {
      await generatedMotion.click();
      await expect(generatedMotion).toHaveClass(/active/, { timeout: 45_000 });
      await expect(page.locator('#motionLabel')).toContainText('edited');
      const sourceMotion = page.locator('#recentMotionList [data-motion-key^="asset:"]').first();
      await sourceMotion.click();
      await expect(sourceMotion).toHaveClass(/active/, { timeout: 45_000 });
      await expect(page.locator('#motionLabel')).not.toContainText('edited', { timeout: 45_000 });
      await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
    }
    await expect(page.locator('#anchorCount')).toHaveText(/^[1-9][0-9]* handles$/);
    await expect(page.locator('#sceneStatus')).toHaveClass(/hidden/, { timeout: 45_000 });
    const canvas = page.locator('#scene');
    await expect(canvas).toBeVisible();
    expect(Number(await canvas.getAttribute('data-robot-meshes'))).toBeGreaterThan(30);
    expect(await canvas.getAttribute('data-contact-marker')).toBe('episode-handle');
    expect(await canvas.getAttribute('data-contact-sample')).toBe('point-force');
    expect(await canvas.getAttribute('data-contact-part-slots')).toBe('8');
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
    await page.locator('#playBtn').click();
    await expect(page.locator('#frameSlider')).toHaveCount(0);
    const timeline = page.locator('#timeline');
    const timelineBox = await timeline.boundingBox();
    await page.mouse.move(timelineBox!.x + timelineBox!.width * 0.72, timelineBox!.y + timelineBox!.height * 0.55);
    await page.mouse.down();
    await page.mouse.move(timelineBox!.x + timelineBox!.width * 0.79, timelineBox!.y + timelineBox!.height * 0.55);
    await page.mouse.up();
    expect(Number(await page.locator('#frameInput').inputValue())).toBeGreaterThan(0);
    await expect(page.locator('#statusFilter')).toBeVisible();
    await expect(page.locator('#targetU')).toHaveCount(0);
    await expect(page.locator('#moveStep')).toHaveCount(0);
    await expect(page.locator('#applyUv')).toHaveCount(0);
    await expect(page.locator('#positionOffset')).toBeVisible();
    await page.locator('#nextAnchor').click();
    await expect(page.locator('#selection')).not.toHaveClass(/empty/);
    await expect(page.locator('#positionOffset')).not.toHaveClass(/disabled/);
    await expect(page.locator('#offsetU')).toHaveText('+0.000 m');
    await expect(page.locator('#offsetV')).toHaveText('+0.000 m');
    await expect(canvas).not.toHaveAttribute('data-selected-contact-body', '');
    if (viewport.width === 1440) {
      await expect(canvas).toHaveAttribute('data-selected-handle-x');
      await expect(canvas).toHaveAttribute('data-selected-handle-y');
      const selectedMarker = {
        x: Number(await canvas.getAttribute('data-selected-handle-x')),
        y: Number(await canvas.getAttribute('data-selected-handle-y')),
      };
      expect(selectedMarker.x).toBeGreaterThan(0);
      expect(selectedMarker.x).toBeLessThan(1);
      expect(selectedMarker.y).toBeGreaterThan(0);
      expect(selectedMarker.y).toBeLessThan(1);
      const sceneRect = await canvas.evaluate(element => {
        const rect = element.getBoundingClientRect();
        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
      });
      const dragX = sceneRect.x + selectedMarker.x * sceneRect.width;
      const dragY = sceneRect.y + selectedMarker.y * sceneRect.height;
      let moveRequestCount = 0;
      page.on('request', request => { if (request.url().endsWith('/api/session/move-handle')) moveRequestCount++; });
      await canvas.evaluate(element => {
        const target = element as HTMLCanvasElement & { testSetPointerCapture?: typeof element.setPointerCapture; testReleasePointerCapture?: typeof element.releasePointerCapture };
        target.testSetPointerCapture = target.setPointerCapture;
        target.testReleasePointerCapture = target.releasePointerCapture;
        target.setPointerCapture = () => {};
        target.releasePointerCapture = () => {};
      });
      await canvas.dispatchEvent('pointerdown', { pointerId: 6, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, clientX: dragX, clientY: dragY });
      await expect(canvas).toHaveAttribute('data-drag-state', 'armed');
      await canvas.dispatchEvent('pointermove', { pointerId: 6, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, clientX: dragX + 4, clientY: dragY });
      await expect(canvas).toHaveAttribute('data-drag-state', 'armed');
      await canvas.dispatchEvent('pointerup', { pointerId: 6, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 0, clientX: dragX + 4, clientY: dragY });
      await expect(canvas).toHaveAttribute('data-drag-state', 'selected');
      await page.waitForTimeout(150);
      expect(moveRequestCount).toBe(0);

      await page.locator('#modeSelect').selectOption('clamp');
      const moveResponse = page.waitForResponse(response => response.url().endsWith('/api/session/move-handle'));
      await canvas.dispatchEvent('pointerdown', { pointerId: 7, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, clientX: dragX, clientY: dragY });
      await expect(canvas).toHaveAttribute('data-drag-state', 'armed');
      await canvas.dispatchEvent('pointermove', { pointerId: 7, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, clientX: dragX + 12, clientY: dragY });
      await expect(canvas).toHaveAttribute('data-drag-state', 'preview');
      await expect(page.locator('#positionOffset')).toHaveClass(/edited/);
      await canvas.dispatchEvent('pointerup', { pointerId: 7, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 0, clientX: dragX + 12, clientY: dragY });
      expect((await moveResponse).ok()).toBeTruthy();
      expect(moveRequestCount).toBe(1);
      await expect(page.locator('#editCount')).toHaveText(/^[1-9][0-9]* edits$/);
      await expect(canvas).toHaveAttribute('data-restore-ghost-count', /^[1-9][0-9]*$/);
      await expect(canvas).toHaveAttribute('data-selected-restore-ghost-x');
      await expect(canvas).toHaveAttribute('data-selected-restore-ghost-y');
      const ghostX = sceneRect.x + Number(await canvas.getAttribute('data-selected-restore-ghost-x')) * sceneRect.width;
      const ghostY = sceneRect.y + Number(await canvas.getAttribute('data-selected-restore-ghost-y')) * sceneRect.height;
      const restoreResponse = page.waitForResponse(response => response.url().endsWith('/api/session/restore-handle'));
      await canvas.dispatchEvent('pointerdown', { pointerId: 8, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1, clientX: ghostX, clientY: ghostY });
      await expect(canvas).toHaveAttribute('data-drag-state', 'restore-armed');
      await canvas.dispatchEvent('pointerup', { pointerId: 8, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 0, clientX: ghostX, clientY: ghostY });
      expect((await restoreResponse).ok()).toBeTruthy();
      await expect(canvas).toHaveAttribute('data-restore-ghost-count', '0');
      await expect(page.locator('#editCount')).toHaveText('0 edits');
      await expect(page.locator('#offsetU')).toHaveText('+0.000 m');
      await expect(page.locator('#offsetV')).toHaveText('+0.000 m');
      await canvas.evaluate(element => {
        const target = element as HTMLCanvasElement & { testSetPointerCapture?: typeof element.setPointerCapture; testReleasePointerCapture?: typeof element.releasePointerCapture };
        if (target.testSetPointerCapture) target.setPointerCapture = target.testSetPointerCapture;
        if (target.testReleasePointerCapture) target.releasePointerCapture = target.testReleasePointerCapture;
        delete target.testSetPointerCapture;
        delete target.testReleasePointerCapture;
      });

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
    await page.locator('.output-settings summary').click();
    await expect(page.locator('#planPath')).toHaveValue(/\.json$/);
    await expect(page.locator('#outputMotion')).toHaveValue(/\.npz$/);
    await expect(page.locator('#generateBtn')).toBeVisible();
    await expect(page.locator('#generationStatus')).toContainText('Ready');
    await page.screenshot({ path: testInfo.outputPath(`motion-edit-output-${viewport.width}.png`), fullPage: true });
    await page.locator('[data-tab="contact"]').click();
    await page.screenshot({ path: testInfo.outputPath(`motion-edit-${viewport.width}.png`), fullPage: true });
  });
}
