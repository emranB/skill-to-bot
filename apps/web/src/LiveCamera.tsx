// Purpose: Preview the camera, record a bounded clip, and confirm saving before execution.
import { useEffect, useRef, useState } from 'react';
import { Camera, Circle, LoaderCircle, Square } from 'lucide-react';

export type Roi = [number, number, number, number];

export function clickHint(point: [number, number]): Roi {
  const width = 0.18;
  const height = 0.28;
  return [
    Math.min(1 - width, Math.max(0, point[0] - width / 2)),
    Math.min(1 - height, Math.max(0, point[1] - height / 2)),
    width,
    height,
  ];
}
type Props = {
  roi: Roi;
  confirmed: boolean;
  disabled: boolean;
  onMapping: (roi: Roi) => void;
  onLock: (locked: boolean) => void;
  onSave: (clip: Blob) => Promise<void>;
};

export default function LiveCamera({ roi, confirmed, disabled, onMapping, onLock, onSave }: Props) {
  const [ready, setReady] = useState(false);
  const [recording, setRecording] = useState(false);
  const [saving, setSaving] = useState(false);
  const [clip, setClip] = useState<Blob | null>(null);
  const [preview, setPreview] = useState('');
  const [error, setError] = useState('');
  const [seconds, setSeconds] = useState(0);
  const [ratio, setRatio] = useState(16 / 9);
  const [attempt, setAttempt] = useState(0);
  const video = useRef<HTMLVideoElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const drag = useRef<[number, number] | null>(null);

  useEffect(() => {
    let stopped = false;
    setError('');
    setReady(false);
    async function connect() {
      try {
        if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
          throw new Error('Camera recording needs a supported browser on localhost or HTTPS.');
        }
        const camera = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            width: { ideal: 1280, max: 1920 },
            height: { ideal: 720, max: 1080 },
            frameRate: { ideal: 25, max: 30 },
          },
        });
        if (stopped) {
          camera.getTracks().forEach((track) => track.stop());
          return;
        }
        stream.current = camera;
        if (video.current) video.current.srcObject = camera;
        camera.getVideoTracks()[0].onended = () => {
          setReady(false);
          setError('Camera disconnected. Reconnect to record again.');
          if (recorder.current?.state === 'recording') recorder.current.stop();
        };
      } catch (problem) {
        if (!stopped)
          setError(
            (problem as Error).name === 'NotAllowedError'
              ? 'Camera permission was denied. Allow camera access to record.'
              : (problem as Error).message,
          );
      }
    }
    void connect();
    return () => {
      stopped = true;
      if (recorder.current) {
        recorder.current.onstop = null;
        recorder.current.ondataavailable = null;
        recorder.current.onerror = null;
        if (recorder.current.state === 'recording') recorder.current.stop();
      }
      stream.current?.getTracks().forEach((track) => {
        track.onended = null;
        track.stop();
      });
      stream.current = null;
      onLock(false);
    };
  }, [attempt, onLock]);

  useEffect(() => {
    if (!clip) {
      if (video.current && stream.current) video.current.srcObject = stream.current;
      return;
    }
    const url = URL.createObjectURL(clip);
    setPreview(url);
    if (video.current) video.current.srcObject = null;
    dialog.current?.showModal();
    return () => URL.revokeObjectURL(url);
  }, [clip]);

  useEffect(() => {
    if (!recording) return;
    const started = performance.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((performance.now() - started) / 1000);
      setSeconds(elapsed);
      if (elapsed >= 59 && recorder.current?.state === 'recording') recorder.current.stop();
    }, 250);
    return () => clearInterval(timer);
  }, [recording]);

  function start() {
    if (!stream.current || !ready || !confirmed || disabled || clip || recording) return;
    try {
      setError('');
      const mimeType = ['video/webm;codecs=vp8', 'video/webm;codecs=vp9', 'video/mp4'].find(
        (type) => MediaRecorder.isTypeSupported(type),
      );
      if (!mimeType) throw new Error('This browser cannot record WebM or MP4 video.');
      const capture = new MediaRecorder(stream.current, { mimeType, videoBitsPerSecond: 4000000 });
      const chunks: Blob[] = [];
      let bytes = 0;
      recorder.current = capture;
      capture.ondataavailable = (event) => {
        if (!event.data.size) return;
        bytes += event.data.size;
        chunks.push(event.data);
        if (bytes >= 100 * 1024 * 1024 && capture.state === 'recording') capture.stop();
      };
      capture.onstop = () => {
        setRecording(false);
        const recorded = new Blob(chunks, { type: capture.mimeType });
        chunks.length = 0;
        if (!recorded.size || recorded.size > 100 * 1024 * 1024) {
          setError('Recording was empty or exceeded 100 MB. Record again.');
          onLock(false);
          return;
        }
        setClip(recorded);
      };
      capture.onerror = () => {
        chunks.length = 0;
        capture.onstop = null;
        setRecording(false);
        onLock(false);
        setError('Recording failed. Record again.');
      };
      capture.start(1000);
      setSeconds(0);
      setRecording(true);
      onLock(true);
    } catch (problem) {
      setError((problem as Error).message);
    }
  }

  function discard() {
    dialog.current?.close();
    setClip(null);
    setPreview('');
    setSeconds(0);
    setError(stream.current?.active ? '' : 'Camera disconnected. Reconnect to record again.');
    onLock(false);
  }

  async function save() {
    if (!clip || saving || disabled) return;
    setSaving(true);
    setError('');
    try {
      await onSave(clip);
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function point(event: React.PointerEvent<HTMLDivElement>): [number, number] {
    const bounds = event.currentTarget.getBoundingClientRect();
    return [
      Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)),
      Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height)),
    ];
  }

  return (
    <>
      <div
        className="object-frame camera-frame"
        style={{ aspectRatio: ratio }}
        onPointerDown={(event) => {
          if (recording || clip || disabled) return;
          drag.current = point(event);
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!drag.current || recording || clip || disabled) return;
          const [x, y] = point(event);
          onMapping([
            Math.min(x, drag.current[0]),
            Math.min(y, drag.current[1]),
            Math.abs(x - drag.current[0]),
            Math.abs(y - drag.current[1]),
          ]);
        }}
        onPointerUp={(event) => {
          if (!drag.current) return;
          const origin = drag.current;
          const [x, y] = point(event);
          drag.current = null;
          const width = Math.abs(x - origin[0]);
          const height = Math.abs(y - origin[1]);
          onMapping(
            width < 0.03 && height < 0.03
              ? clickHint(origin)
              : [Math.min(x, origin[0]), Math.min(y, origin[1]), width, height],
          );
        }}
      >
        <video
          ref={video}
          aria-label={clip ? 'Recorded demonstration' : 'Live camera feed'}
          src={clip ? preview : undefined}
          autoPlay={!clip}
          controls={Boolean(clip)}
          muted
          playsInline
          onLoadedData={(event) => {
            const element = event.currentTarget;
            setRatio(element.videoWidth / element.videoHeight);
            if (!clip) setReady(true);
          }}
        />
        {!clip && ready && (
          <div
            className="roi"
            style={{
              left: `${roi[0] * 100}%`,
              top: `${roi[1] * 100}%`,
              width: `${roi[2] * 100}%`,
              height: `${roi[3] * 100}%`,
            }}
          >
            <span>Hint</span>
          </div>
        )}
        {!ready && !error && (
          <span className="camera-loading">
            <LoaderCircle size={20} className="spin" /> Opening camera
          </span>
        )}
      </div>
      <div className="recording-controls">
        <button
          className="primary"
          onClick={start}
          disabled={!ready || !confirmed || disabled || recording || Boolean(clip)}
        >
          <Circle size={16} /> Start Recording
        </button>
        <button
          className="secondary"
          onClick={() => {
            if (recorder.current?.state === 'recording') recorder.current.stop();
          }}
          disabled={!recording}
        >
          <Square size={16} /> Stop Recording
        </button>
        <span role="status">{recording ? `${seconds} / 59 s` : 'Camera'}</span>
      </div>
      {error && !clip && (
        <div className="camera-error" role="alert">
          <span>{error}</span>
          <button
            className="secondary"
            onClick={() => {
              onMapping(roi);
              setAttempt((value) => value + 1);
            }}
          >
            <Camera size={16} /> Reconnect
          </button>
        </div>
      )}
      <dialog
        ref={dialog}
        className="recording-dialog"
        aria-labelledby="recording-title"
        onCancel={(event) => {
          event.preventDefault();
          if (!saving) discard();
        }}
      >
        <h3 id="recording-title">Save recording and run?</h3>
        <p>{seconds} s recorded</p>
        {error && (
          <p role="alert" className="run-error">
            {error}
          </p>
        )}
        <div className="actions">
          <button className="secondary" onClick={discard} disabled={saving}>
            No, record again
          </button>
          <button className="primary" onClick={() => void save()} disabled={saving || disabled}>
            {saving && <LoaderCircle size={16} className="spin" />}
            {saving ? 'Saving' : 'Yes, save and run'}
          </button>
        </div>
      </dialog>
    </>
  );
}
