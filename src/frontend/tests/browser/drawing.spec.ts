// Purpose: Verify real pointer capture, drawing controls, responsive layout and one complete Panda run.
import { expect, test } from '@playwright/test';

test('pointer drawing, undo, clear and responsive workspace', async ({ page }, testInfo) => {
  const response = await page.goto('/');
  expect(response?.headers()['content-security-policy']).toContain("default-src 'self'");
  expect(response?.headers()['cache-control']).toBe('no-cache');
  await expect(page.getByRole('button', { name: 'Home', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await expect(page.getByRole('heading', { name: 'skill-to-bot', level: 1 })).toBeVisible();
  await expect(page.locator('.home-description')).toContainText('simulated Panda');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  expect(
    await page
      .locator('.home-intro')
      .evaluate((element) => getComputedStyle(element).animationName),
  ).toBe('none');
  await expect(page.locator('.overview dd').first()).not.toHaveText('-');
  await expect(page.locator('.overview dd').last()).not.toHaveText('-');
  await expect
    .poll(() =>
      page
        .locator('.run-preview img')
        .evaluateAll((images) =>
          images.every(
            (image) =>
              (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0,
          ),
        ),
    )
    .toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({
    path: `../../data/runs/home-${testInfo.project.name}.png`,
    fullPage: true,
  });
  const history = await (await page.request.get('/api/runs?summary=true')).json();
  const completed = history.filter(
    (run: { status: string; thumbnail_available: boolean; video_available: boolean }) =>
      run.status === 'completed' && run.thumbnail_available && run.video_available,
  );
  expect(completed.length).toBeGreaterThanOrEqual(4);
  const [latest, duplicate, fixture, second] = completed;
  // Substitute browser metadata only; never persist fabricated human evidence.
  let records = [
    { ...latest, run_id: 'failed-preview', source_type: 'human_capture', status: 'failed' },
    {
      ...latest,
      run_id: 'missing-preview',
      source_type: 'human_capture',
      thumbnail_available: false,
    },
    { ...fixture, source_type: 'synthetic_fixture' },
    { ...latest, source_type: 'human_capture' },
    { ...duplicate, source_type: 'human_capture', demonstration_id: latest.demonstration_id },
    { ...second, source_type: 'human_capture' },
  ];
  const endpoint = '**/api/runs?summary=true';
  await page.route(endpoint, (route) => route.fulfill({ json: records }));
  await page.reload();
  await expect(page.locator('.run-grid .run-item')).toHaveCount(2);
  expect(
    await page
      .locator('.run-grid .run-item')
      .evaluateAll((items) => items.map((item) => item.getAttribute('data-run-id'))),
  ).toEqual([latest.run_id, second.run_id]);
  await page.getByRole('button', { name: 'Watch a run', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Workspace', level: 1 })).toBeVisible();
  await expect(page.getByLabel('Panda drawing simulation')).toHaveAttribute(
    'src',
    `/api/runs/${latest.run_id}/artifacts/simulation.mp4`,
  );
  await page.getByRole('button', { name: 'Home', exact: true }).click();
  records = [];
  await expect(page.getByText('No completed human drawings yet.', { exact: true })).toBeVisible();
  await expect(page.locator('.run-grid .run-item')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Watch a run', exact: true })).toHaveCount(0);
  await page.unroute(endpoint);
  await page.reload();
  await expect(page.locator('.overview dd').first()).not.toHaveText('-');
  await page.getByRole('button', { name: 'New drawing', exact: true }).click();
  const canvas = page.getByLabel('Human drawing surface');
  await page.getByLabel('Brush color').fill('#3173ba');
  await page.getByLabel('Brush size', { exact: true }).fill('8');
  await expect(canvas).toBeVisible();
  await canvas.evaluate((element) => element.scrollIntoView({ block: 'center' }));
  let box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.3);
  await page.mouse.down();
  await expect(page.getByRole('button', { name: 'Save & Run', exact: true })).toBeDisabled();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5, { steps: 16 });
  await page.mouse.up();
  await expect(page.getByText('1 stroke', { exact: true })).toBeVisible();
  const ink = await canvas.evaluate((element) => {
    const c = element as HTMLCanvasElement;
    return c
      .getContext('2d')!
      .getImageData(0, 0, c.width, c.height)
      .data.some((value, index) => index % 4 === 3 && value > 0);
  });
  expect(ink).toBe(true);
  await expect(page.getByText('Constant pressure', { exact: true })).toBeVisible();
  await page.mouse.down();
  await expect(page.getByRole('button', { name: 'Save & Run', exact: true })).toBeDisabled();
  await page.mouse.up();
  await page.getByRole('button', { name: 'Undo last stroke' }).click();
  await expect(page.getByText('0 strokes', { exact: true })).toBeVisible();
  await canvas.evaluate((element) => element.scrollIntoView({ block: 'center' }));
  box = (await canvas.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.3);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5, { steps: 8 });
  await page.mouse.up();
  await expect(page.getByText('1 stroke', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Clear drawing', exact: true }).click();
  await expect(page.getByText('0 strokes', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({
    path: `../../data/runs/drawing-${testInfo.project.name}.png`,
    fullPage: true,
  });
});

test('captured drawing saves and executes with trace, video and history', async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name === 'mobile',
    'One representative browser physics execution; root suite covers every fixture.',
  );
  test.setTimeout(240000);
  const historyButton = page
    .getByRole('navigation', { name: 'Views' })
    .getByRole('button', { name: 'History', exact: true });
  await page.goto('/');
  await page.getByRole('button', { name: 'Workspace', exact: true }).click();
  await expect(page.getByText('Simulation ready', { exact: true })).toBeVisible({ timeout: 30000 });
  const canvas = page.getByLabel('Human drawing surface');
  const box = (await canvas.boundingBox())!;
  await page.getByLabel('Brush color').fill('#3173ba');
  await page.getByLabel('Brush size', { exact: true }).fill('8');
  await page.mouse.move(box.x + box.width * 0.35, box.y + box.height * 0.35);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.35, { steps: 20 });
  await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.6, { steps: 20 });
  await page.mouse.up();
  await page.getByLabel('Brush color').fill('#dc5278');
  await page.getByLabel('Brush size', { exact: true }).fill('20');
  // Synthetic stylus events exercise capture without claiming physical Surface Pen validation.
  const pen = await page.context().newCDPSession(page);
  for (let i = 0; i <= 20; i++) {
    await pen.send('Input.dispatchMouseEvent', {
      type: i === 0 ? 'mousePressed' : i === 20 ? 'mouseReleased' : 'mouseMoved',
      pointerType: 'pen',
      button: 'left',
      buttons: i === 20 ? 0 : 1,
      clickCount: 1,
      x: box.x + box.width * (0.25 + i * 0.02),
      y: box.y + box.height * 0.7,
      force: i === 20 ? 0 : 0.2 + i * 0.03,
      tiltX: 10,
      tiltY: 5,
    });
  }
  await pen.detach();
  await expect(page.getByText('Variable pressure', { exact: true })).toBeVisible();
  // Mark automated pointer data honestly while retaining the actual capture/persistence path.
  await page.route('**/api/demonstrations', async (route) => {
    if (route.request().method() === 'POST') {
      const raw = route.request().postDataJSON();
      raw.source.type = 'synthetic_fixture';
      await route.continue({ postData: JSON.stringify(raw) });
    } else await route.continue();
  });
  await page.getByRole('button', { name: 'Save & Run', exact: true }).click();
  await expect(page.getByText('Panda: draw', { exact: false }).first()).toBeVisible({
    timeout: 180000,
  });
  await expect(page.getByText('Paper proximity', { exact: true })).toBeVisible({
    timeout: 180000,
  });
  await expect(page.locator('.status.completed')).toBeVisible();
  await expect(page.getByText('Physical contact', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Brush color')).toHaveValue('#dc5278');
  await expect(page.getByLabel('Brush size', { exact: true })).toHaveValue('20');
  const video = page.getByLabel('Panda drawing simulation');
  await expect(video).toBeVisible();
  await expect
    .poll(() => video.evaluate((e) => (e as HTMLVideoElement).readyState), { timeout: 30000 })
    .toBeGreaterThanOrEqual(2);
  expect(await video.evaluate((e) => (e as HTMLVideoElement).videoWidth)).toBeGreaterThan(100);
  for (const rate of [2, 5, 10, 1]) {
    await page.getByRole('button', { name: `${rate}x`, exact: true }).click();
    expect(await video.evaluate((e) => (e as HTMLVideoElement).playbackRate)).toBe(rate);
  }
  const runId = (await video.getAttribute('src'))!.match(/runs\/([^/]+)/)![1];
  const response = await page.request.get(`/api/runs/${runId}`);
  const run = await response.json();
  const summary = await (await page.request.get(`/api/runs/${runId}?summary=true`)).json();
  expect(summary.skill_available).toBe(true);
  expect(summary.thumbnail_available).toBe(true);
  expect(summary).not.toHaveProperty('skill');
  const saved = await page.request.get(`/api/demonstrations/${run.demonstration_id}`);
  const capture = await saved.json();
  expect(capture.strokes[0].color).toBe('#3173ba');
  expect(
    capture.strokes[0].points.every((p: { pressure?: number }) => p.pressure === undefined),
  ).toBe(true);
  expect(capture.strokes[1].color).toBe('#dc5278');
  expect(
    capture.strokes[1].points.some((p: { pressure?: number }) => (p.pressure ?? 0) > 0.6),
  ).toBe(true);
  await video.evaluate((element) => {
    const clip = element as HTMLVideoElement;
    clip.pause();
    clip.currentTime = Math.max(0, clip.duration - 0.2);
  });
  await expect
    .poll(() =>
      video.evaluate((element) => {
        const clip = element as HTMLVideoElement;
        return !clip.seeking && clip.readyState >= 2;
      }),
    )
    .toBe(true);
  for (const name of ['Raw Input', 'Skill', 'Trace']) {
    await page.getByRole('tab', { name, exact: true }).click();
    await expect(page.getByRole('tabpanel', { name })).toContainText(
      name === 'Trace'
        ? 'actual_local'
        : name === 'Skill'
          ? 'paper_normalized'
          : 'normalized_screen',
    );
  }
  await page.getByRole('tab', { name: 'Logs', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Raw Input', exact: true })).toBeFocused();
  await page.screenshot({
    path: '../../data/runs/drawing-result-desktop.png',
    fullPage: true,
  });
  await historyButton.click();
  const row = page.locator(`[data-run-id="${runId}"]`);
  await expect(row).toBeVisible();
  await row.locator('.run-open').click();
  await expect(video).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run on shifted paper' })).toBeEnabled();
  await historyButton.click();
  await page.screenshot({ path: '../../data/runs/history-desktop.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  await row.getByRole('button', { name: /Delete .* from history/ }).click();
  const dialog = page.getByRole('dialog', { name: 'Delete from history?' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: '../../data/runs/delete-mobile.png' });
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(row.getByRole('button', { name: /Delete .* from history/ })).toBeFocused();
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: /Delete .* from history/ }).click();
  const endpoint = `**/api/runs/${runId}`;
  await page.route(endpoint, (route) =>
    route.request().method() === 'DELETE'
      ? route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'History temporarily unavailable.' }),
        })
      : route.continue(),
  );
  await dialog.getByRole('button', { name: 'Delete from history', exact: true }).click();
  await expect(dialog.getByRole('alert')).toHaveText('History temporarily unavailable.');
  await expect(row).toHaveCount(1);
  await page.unroute(endpoint);
  await dialog.getByRole('button', { name: 'Delete from history', exact: true }).click();
  await expect(dialog).not.toBeVisible();
  await expect(row).toHaveCount(0);
  await page.reload();
  await historyButton.click();
  await expect(row).toHaveCount(0);
  expect((await page.request.get(`/api/demonstrations/${run.demonstration_id}`)).ok()).toBe(true);
  expect((await page.request.get(`/api/runs/${runId}/artifacts/trace.json`)).ok()).toBe(true);
});
