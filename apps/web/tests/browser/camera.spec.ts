// Purpose: Verify camera capture with a synthetic stream and execute its saved recording under physics.
import { expect, test, type Page } from '@playwright/test';

type CameraWindow = Window & {
  cameraTestRestart: () => void;
  cameraTestDone: boolean;
  cameraTestStream: MediaStream;
};

async function syntheticCamera(page: Page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      value: async () => {
        const image = new Image();
        image.src = '/api/demonstrations/pop-can-pick-up-1.mp4/preview';
        await image.decode();
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 360;
        const context = canvas.getContext('2d')!;
        const stream = canvas.captureStream(25);
        let started = performance.now();
        const state = window as unknown as CameraWindow;
        state.cameraTestStream = stream;
        state.cameraTestRestart = () => {
          started = performance.now();
          state.cameraTestDone = false;
        };
        function frame() {
          if (!stream.active) return;
          const seconds = (performance.now() - started) / 1000;
          const lift =
            Math.max(0, Math.min(1, seconds - 2)) - Math.max(0, Math.min(1, seconds - 5));
          const travel = Math.max(0, Math.min(1, (seconds - 3) / 2));
          context.fillStyle = '#e5e7eb';
          context.fillRect(0, 0, 640, 360);
          context.fillStyle = '#9ca3af';
          context.fillRect(0, 280, 640, 80);
          context.drawImage(
            image,
            image.width * 0.68,
            image.height * 0.23,
            image.width * 0.17,
            image.height * 0.52,
            640 * (0.68 - travel * 0.35),
            360 * (0.23 - lift * 0.16),
            640 * 0.17,
            360 * 0.52,
          );
          state.cameraTestDone = seconds >= 7;
          requestAnimationFrame(frame);
        }
        frame();
        return stream;
      },
    });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Live Camera' }).click();
  const feed = page.getByLabel('Live camera feed', { exact: true });
  await expect
    .poll(() => feed.evaluate((element) => (element as HTMLVideoElement).readyState), {
      timeout: 15000,
    })
    .toBeGreaterThanOrEqual(2);
  await page.getByRole('button', { name: 'Confirm Mapping' }).click();
  await expect(page.getByRole('button', { name: 'Start Recording' })).toBeEnabled();
}

async function shortRecording(page: Page) {
  await page.getByRole('button', { name: 'Start Recording' }).click();
  await expect(page.locator('.recording-controls [role="status"]')).toHaveText(
    /^[1-9]\d* \/ 59 s$/,
  );
  await page.getByRole('button', { name: 'Stop Recording' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
}

test('camera permission failure leaves the video library usable', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
      value: async () => {
        throw new DOMException('Denied', 'NotAllowedError');
      },
    });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Live Camera' }).click();
  await expect(page.getByRole('alert')).toContainText('Camera permission was denied');
  await expect(page.getByRole('button', { name: 'Start Recording' })).toBeDisabled();
  await page.getByRole('button', { name: 'Can pickup 1' }).click();
  await expect(
    page.getByAltText('Selected demonstration first frame with object selection'),
  ).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.evaluate(() => Object.defineProperty(window, 'MediaRecorder', { value: undefined }));
  await page.getByRole('button', { name: 'Live Camera' }).click();
  await expect(page.getByRole('alert')).toContainText('Camera recording needs a supported browser');
  await expect(page.getByRole('button', { name: 'Start Recording' })).toBeDisabled();
});

test('discard and save failure return safely to recording without saved input', async ({
  page,
}, testInfo) => {
  const before = await (await page.request.get('/api/demonstrations')).json();
  let uploads = 0;
  await page.route('**/api/live-demonstrations', async (route) => {
    uploads++;
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Recording could not be decoded. Record again.' }),
    });
  });
  await syntheticCamera(page);
  await shortRecording(page);
  await page.getByRole('button', { name: 'No, record again' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Start Recording' })).toBeEnabled();
  expect(uploads).toBe(0);
  await shortRecording(page);
  await page.getByRole('button', { name: 'Yes, save and run' }).click();
  await expect(page.getByRole('dialog')).toContainText('Recording could not be decoded');
  await page.screenshot({
    path: `../../data/runs/camera-review-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole('button', { name: 'No, record again' }).click();
  await expect(page.getByRole('button', { name: 'Start Recording' })).toBeEnabled();
  expect(await (await page.request.get('/api/demonstrations')).json()).toEqual(before);
  await page.evaluate(() => {
    const track = (window as unknown as CameraWindow).cameraTestStream.getVideoTracks()[0];
    track.stop();
    track.dispatchEvent(new Event('ended'));
  });
  await expect(page.getByRole('alert')).toContainText('Camera disconnected');
  await page.getByRole('button', { name: 'Reconnect' }).click();
  await expect(page.getByRole('button', { name: 'Confirm Mapping' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Start Recording' })).toBeDisabled();
  await page.getByRole('button', { name: 'Can pickup 1' }).click();
  expect(
    await page.evaluate(() =>
      (window as unknown as CameraWindow).cameraTestStream
        .getTracks()
        .every((track) => track.readyState === 'ended'),
    ),
  ).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('confirmed camera recording is saved before the complete robot pipeline', async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== 'desktop',
    'Capture controls are covered on both viewports; execute physics once.',
  );
  test.setTimeout(420000);
  await syntheticCamera(page);
  for (const [label, value] of [
    ['X', '69'],
    ['Y', '27'],
    ['Width', '14'],
    ['Height', '43'],
  ]) {
    await page.getByLabel(label, { exact: true }).fill(value);
  }
  await page.getByRole('button', { name: 'Confirm Mapping' }).click();
  await page.evaluate(() => (window as unknown as CameraWindow).cameraTestRestart());
  await page.getByRole('button', { name: 'Start Recording' }).click();
  await page.waitForFunction(() => (window as unknown as CameraWindow).cameraTestDone, undefined, {
    timeout: 15000,
  });
  await page.getByRole('button', { name: 'Stop Recording' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const savedPromise = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/live-demonstrations') && response.request().method() === 'POST',
  );
  const runPromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/runs') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Yes, save and run' }).click();
  const savedResponse = await savedPromise;
  expect(savedResponse.status()).toBe(201);
  const saved = await savedResponse.json();
  expect(saved.name).toMatch(/^live_demo_\d{8}T\d{12}Z_[a-f0-9]{8}\.mp4$/);
  expect((await page.request.get('/api' + saved.url)).status()).toBe(200);
  const runResponse = await runPromise;
  expect(runResponse.status()).toBe(202);
  const run = await runResponse.json();
  expect(run.video).toBe(saved.name);
  await expect
    .poll(async () => (await (await page.request.get(`/api/runs/${run.run_id}`)).json()).status, {
      timeout: 360000,
    })
    .not.toBe('running');
  const finished = await (await page.request.get(`/api/runs/${run.run_id}`)).json();
  expect(finished.status, finished.error || 'Physics result').toBe('completed');
  await expect(page.locator('.run-detail .run-status')).toHaveText('completed');
  await expect(page.getByText('Verified', { exact: true })).toHaveCount(2);
  await expect(page.getByRole('tabpanel')).toContainText('Physical result verified');
  await page.getByRole('tab', { name: 'Skill', exact: true }).click();
  await expect(page.getByRole('tabpanel')).toContainText(saved.name);
  const robot = page.locator('video').last();
  await expect
    .poll(() => robot.evaluate((element) => (element as HTMLVideoElement).readyState), {
      timeout: 15000,
    })
    .toBeGreaterThanOrEqual(2);
  await robot.evaluate(async (element) => {
    const video = element as HTMLVideoElement;
    video.muted = true;
    await video.play();
  });
  await expect
    .poll(() => robot.evaluate((element) => (element as HTMLVideoElement).currentTime))
    .toBeGreaterThan(0.5);
  await robot.evaluate((element) => (element as HTMLVideoElement).pause());
  await page.screenshot({ path: '../../data/runs/camera-pipeline.png', fullPage: true });
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reset', exact: true })).toBeEnabled();
});
