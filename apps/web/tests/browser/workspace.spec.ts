// Purpose: Verify the served workspace, real media, responsive layout, and run controls.
import { expect, test } from '@playwright/test';

test('long API errors stay readable without overflowing the workspace', async ({ page }) => {
  await page.route('**/api/runs', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'SelectedObjectCouldNotBeTrackedReliably'.repeat(20) }),
      });
    } else await route.continue();
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Confirm Mapping' }).click();
  const start = page.getByRole('button', { name: 'Run Demo', exact: true });
  await expect(start).toBeEnabled();
  await start.click();
  await expect(page.getByRole('alert')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Dismiss error' }).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
});

test('runs the supplied demonstration and shows the measured robot result', async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== 'desktop',
    'One real execution is sufficient; both viewports are checked separately.',
  );
  test.setTimeout(420000);
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Can pickup right to left 1' })).toBeVisible();
  await page.getByRole('button', { name: 'Can pickup right to left 1' }).click();
  await page.getByRole('button', { name: 'Confirm Mapping' }).click();
  const start = page.getByRole('button', { name: 'Run Demo', exact: true });
  await expect(start).toBeEnabled();
  const responsePromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/runs') && response.request().method() === 'POST',
  );
  await start.click();
  expect((await responsePromise).status()).toBe(202);
  await expect(page.locator('.run-detail .run-status')).toHaveText('running');
  await expect(page.locator('.run-detail .run-status')).toHaveText('completed', {
    timeout: 360000,
  });
  await expect(page.getByText('Verified', { exact: true })).toHaveCount(2);
  await expect(page.getByRole('tabpanel')).toContainText('Physical result verified');
  await page.getByRole('tab', { name: 'Skill', exact: true }).click();
  await expect(page.getByRole('tabpanel')).toContainText('operator_planar');
  await page.getByRole('tab', { name: 'Observations', exact: true }).click();
  await expect(page.getByRole('tabpanel')).toContainText('329 tracked frames');
  await expect(page.locator('tbody tr')).toHaveCount(329);
  await expect(page.getByRole('tabpanel')).toContainText('Acquisition: YOLO');
  await expect(page.getByLabel('Tracked object', { exact: true })).toBeVisible();
  const initialBounds = await page
    .getByLabel('Tracked object', { exact: true })
    .getAttribute('style');
  await page.locator('.tracked-video video').evaluate((element) => {
    (element as HTMLVideoElement).currentTime = 7;
  });
  await expect
    .poll(() => page.getByLabel('Tracked object', { exact: true }).getAttribute('style'))
    .not.toBe(initialBounds);
  expect(
    await page
      .getByLabel('Tracked object', { exact: true })
      .evaluate((element) => parseFloat((element as HTMLElement).style.left)),
  ).toBeLessThan(10);
  const robot = page.locator('video').last();
  await expect
    .poll(() => robot.evaluate((element) => (element as HTMLVideoElement).readyState))
    .toBeGreaterThanOrEqual(2);
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reset', exact: true })).toBeEnabled();
});

test('workspace renders media and controls without horizontal overflow', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'skill-to-bot', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Can pickup right to left 1' })).toBeVisible();
  await page.getByRole('button', { name: 'Can pickup right to left 1' }).click();
  await expect(page.getByText('Connected', { exact: true })).toBeVisible();
  const image = page.getByAltText('Selected demonstration first frame with object selection');
  await expect(image).toBeVisible();
  await expect
    .poll(() => image.evaluate((element) => (element as HTMLImageElement).naturalWidth), {
      timeout: 15000,
    })
    .toBeGreaterThan(0);
  const variance = await image.evaluate((element) => {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 36;
    const context = canvas.getContext('2d')!;
    context.drawImage(element as HTMLImageElement, 0, 0, 64, 36);
    const pixels = context.getImageData(0, 0, 64, 36).data;
    return new Set(Array.from(pixels).filter((_, index) => index % 4 !== 3)).size;
  });
  expect(variance).toBeGreaterThan(30);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Confirm Mapping' }).click();
  await expect(page.getByRole('button', { name: 'Run Demo', exact: true })).toBeEnabled();
  await page.getByLabel('Width', { exact: true }).fill('16');
  await expect(page.getByRole('button', { name: 'Confirm Mapping' })).toBeVisible();
  await page.screenshot({
    path: `../../data/runs/mapping-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByLabel('Width', { exact: true }).fill('100');
  await expect(page.getByRole('button', { name: 'Confirm Mapping' })).toBeDisabled();
  await page.getByLabel('Width', { exact: true }).fill('17');
  await page.getByRole('button', { name: 'Confirm Mapping' }).click();
  const simulation = page.locator('video').first();
  await expect
    .poll(() => simulation.evaluate((element) => (element as HTMLVideoElement).readyState), {
      timeout: 15000,
    })
    .toBeGreaterThanOrEqual(2);
  await simulation.evaluate(async (element) => {
    const video = element as HTMLVideoElement;
    video.muted = true;
    await video.play();
  });
  await expect
    .poll(() => simulation.evaluate((element) => (element as HTMLVideoElement).currentTime))
    .toBeGreaterThan(0.5);
  await simulation.evaluate((element) => (element as HTMLVideoElement).pause());
  const videoPixels = await simulation.evaluate((element) => {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 48;
    const context = canvas.getContext('2d')!;
    context.drawImage(element as HTMLVideoElement, 0, 0, 64, 48);
    return new Set(context.getImageData(0, 0, 64, 48).data).size;
  });
  expect(videoPixels).toBeGreaterThan(30);
  await page.screenshot({
    path: `../../data/runs/workspace-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole('tab', { name: 'Observations', exact: true }).click();
  await expect(page.locator('tbody tr')).toHaveCount(329);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({
    path: `../../data/runs/observations-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole('button', { name: /Run history/ }).click();
  await expect(page.getByRole('heading', { name: 'Run history' })).toBeVisible();
  expect(errors).toEqual([]);
});
