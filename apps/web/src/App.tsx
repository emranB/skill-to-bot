// Purpose: Present demonstration calibration, run control, status, and simulation results.
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  Camera,
  ArrowRight,
  CircleAlert,
  LoaderCircle,
  Play,
  RotateCcw,
  Upload,
  Video,
  XCircle,
} from 'lucide-react';
import config from '../config.json';
import RunStatus, { type Run, type Observation } from './RunStatus';
import LiveCamera, { clickHint, type Roi } from './LiveCamera';

type Demo = { name: string; bytes: number; url: string };
type Services = Record<string, { status: string; detail?: string }>;

function displayName(name: string) {
  const live = name.match(/^live_demo_(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
  if (live) return `Live demo ${live[1]}-${live[2]}-${live[3]} ${live[4]}:${live[5]} UTC`;
  if (/^[a-f0-9]{32}\.mp4$/.test(name)) return `Uploaded video ${name.slice(0, 6)}`;
  return name
    .replace(/(?:\.mp4)+$/i, '')
    .replace(/^pop-can-pick-up-/, 'Can pickup ')
    .replaceAll('-', ' ');
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch('/api' + path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Service could not be reached.' }));
    throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
  }
  return response.json();
}

export default function App() {
  const [demos, setDemos] = useState<Demo[]>([]);
  const [selected, setSelected] = useState('');
  const [services, setServices] = useState<Services>({});
  const [runs, setRuns] = useState<Run[]>([]);
  const [roi, setRoi] = useState<Roi>([0.67, 0.23, 0.17, 0.5]);
  const [span, setSpan] = useState(config.defaultWorkspaceSpanMeters);
  const [plane, setPlane] = useState<'front' | 'table'>('front');
  const [observations, setObservations] = useState<Observation[]>([]);
  const [sourceTime, setSourceTime] = useState(0);
  const [confirmed, setConfirmed] = useState(false);
  const [mode, setMode] = useState<'object' | 'video'>('object');
  const [frameRatio, setFrameRatio] = useState(16 / 9);
  const [tab, setTab] = useState<'workspace' | 'history'>('workspace');
  const [pending, setPending] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState('');
  const [camera, setCamera] = useState(false);
  const [cameraLocked, setCameraLocked] = useState(false);
  const drag = useRef<[number, number] | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const run = camera
    ? undefined
    : runs.find((item) => item.run_id === runId) || runs.find((item) => item.video === selected);
  const busy = runs.some((item) => item.status === 'running');
  const locked = busy || pending || cameraLocked;
  const available =
    services.perception?.status === 'ready' && services.simulation?.status === 'ready';
  const validMapping =
    roi.every(Number.isFinite) &&
    Math.min(...roi) >= 0 &&
    Math.min(roi[2], roi[3]) >= 0.01 &&
    roi[0] + roi[2] <= 1 &&
    roi[1] + roi[3] <= 1;
  const tracked = observations.reduce<Observation | undefined>(
    (latest, sample) => (sample.time <= sourceTime ? sample : latest),
    undefined,
  );

  const refresh = useCallback(async () => {
    try {
      const [library, status, history] = await Promise.all([
        api<Demo[]>('/demonstrations'),
        api<Services>('/services'),
        api<Run[]>('/runs'),
      ]);
      setDemos(library);
      setServices(status);
      setRuns(history);
      setSelected((previous) => previous || library[0]?.name || '');
    } catch (problem) {
      setError((problem as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
    let stopped = false;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout>;
    function connect() {
      socket = new WebSocket(
        `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/ws`,
      );
      socket.onopen = () => {
        setConnected(true);
        void refresh();
      };
      socket.onmessage = (message) => {
        try {
          const snapshot = JSON.parse(message.data);
          setServices(snapshot.services);
          setRuns(snapshot.runs);
        } catch {
          /* Ignore incomplete status messages; REST refresh remains available. */
        }
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) retry = setTimeout(connect, 2000);
      };
      socket.onerror = () => socket?.close();
    }
    connect();
    const poll = setInterval(() => {
      void refresh();
    }, config.statusPollSeconds * 1000);
    return () => {
      stopped = true;
      clearTimeout(retry);
      clearInterval(poll);
      socket?.close();
    };
  }, [refresh]);

  function choose(name: string) {
    if (locked) return;
    setCamera(false);
    setRunId('');
    setSelected(name);
    setConfirmed(false);
    setError('');
    setMode('object');
  }
  async function upload(file?: File) {
    if (!file) return;
    setPending(true);
    setError('');
    const form = new FormData();
    form.append('file', file);
    try {
      const demo = await api<Demo>('/demonstrations', { method: 'POST', body: form });
      await refresh();
      choose(demo.name);
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setPending(false);
      if (input.current) input.current.value = '';
    }
  }
  async function start(video = selected) {
    setPending(true);
    setError('');
    try {
      const value = await api<Run>('/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video,
          request_id: crypto.randomUUID(),
          calibration: { method: 'operator_planar', plane, workspace_span: span, roi },
        }),
      });
      setRunId(value.run_id);
      setMode('video');
      await refresh();
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setPending(false);
    }
  }
  async function saveRecording(clip: Blob) {
    setPending(true);
    setError('');
    const form = new FormData();
    form.append('file', clip, clip.type.startsWith('video/mp4') ? 'camera.mp4' : 'camera.webm');
    try {
      const demo = await api<Demo>('/live-demonstrations', { method: 'POST', body: form });
      setSelected(demo.name);
      setRunId('');
      setMode('video');
      setConfirmed(true);
      setCamera(false);
      await start(demo.name);
    } finally {
      setPending(false);
    }
  }
  async function reset() {
    setPending(true);
    setError('');
    try {
      await api('/reset', { method: 'POST' });
      await refresh();
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setPending(false);
    }
  }
  function coordinates(event: React.PointerEvent<HTMLDivElement>): [number, number] {
    const box = event.currentTarget.getBoundingClientRect();
    return [
      Math.max(0, Math.min(1, (event.clientX - box.left) / box.width)),
      Math.max(0, Math.min(1, (event.clientY - box.top) / box.height)),
    ];
  }
  function draw(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag.current || busy) return;
    const point = coordinates(event);
    setRoi([
      Math.min(point[0], drag.current[0]),
      Math.min(point[1], drag.current[1]),
      Math.abs(point[0] - drag.current[0]),
      Math.abs(point[1] - drag.current[1]),
    ]);
    setConfirmed(false);
  }

  return (
    <>
      <header className="app-header">
        <div className="brand">
          <Activity size={26} />
          <h1>skill-to-bot</h1>
          <span className="version">Build 02</span>
        </div>
        <span className={`connection ${connected ? 'online' : ''}`}>
          <i />
          {connected ? 'Connected' : 'Reconnecting'}
        </span>
      </header>
      <div className="nav-row">
        <nav aria-label="Views">
          <button
            aria-current={tab === 'workspace' ? 'page' : undefined}
            onClick={() => setTab('workspace')}
          >
            Workspace
          </button>
          <button
            aria-current={tab === 'history' ? 'page' : undefined}
            disabled={cameraLocked}
            onClick={() => {
              setCamera(false);
              setTab('history');
            }}
          >
            Run history <span>{runs.length}</span>
          </button>
        </nav>
        <div className="service-list">
          {['perception', 'simulation'].map((name) => (
            <span
              key={name}
              className={services[name]?.status === 'ready' ? 'ready' : 'unavailable'}
              title={services[name]?.detail}
            >
              <i />
              {name}
            </span>
          ))}
        </div>
      </div>
      <main>
        {error && (
          <div role="alert" className="alert">
            <XCircle size={18} />
            <span>{error}</span>
            <button title="Dismiss error" aria-label="Dismiss error" onClick={() => setError('')}>
              <XCircle size={18} />
            </button>
          </div>
        )}
        {tab === 'history' ? (
          <section>
            <h2>Run history</h2>
            {runs.length === 0 ? (
              <p className="muted">No runs yet.</p>
            ) : (
              <div className="history">
                {runs.map((item) => (
                  <button
                    key={item.run_id}
                    onClick={() => {
                      setRunId(item.run_id);
                      setCamera(false);
                      setSelected(item.video);
                      setConfirmed(false);
                      setMode('video');
                      setTab('workspace');
                    }}
                  >
                    <span>
                      <strong title={item.video}>{displayName(item.video)}</strong>
                      <small>{new Date(item.created_at * 1000).toLocaleString()}</small>
                    </span>
                    <span className={`run-status ${item.status}`}>{item.status}</span>
                    <ArrowRight size={18} />
                  </button>
                ))}
              </div>
            )}
          </section>
        ) : (
          <>
            <div className="workspace-heading">
              <div>
                <h2>Demonstration to robot</h2>
                <p className="muted">Panda · Can transfer · Physics simulation</p>
              </div>
              <div className="actions">
                <button
                  className="secondary"
                  title="Reset simulation"
                  disabled={locked || services.simulation?.status !== 'ready'}
                  onClick={() => void reset()}
                >
                  <RotateCcw size={17} />
                  Reset
                </button>
                <button
                  className={confirmed ? 'primary' : 'confirm-mapping'}
                  disabled={
                    (!selected && !camera) ||
                    (confirmed && (!available || camera)) ||
                    locked ||
                    !validMapping
                  }
                  onClick={() => (confirmed ? void start() : setConfirmed(true))}
                >
                  {busy || pending ? (
                    <LoaderCircle size={17} className="spin" />
                  ) : confirmed ? (
                    <Play size={17} />
                  ) : (
                    <CircleAlert size={17} />
                  )}
                  {busy
                    ? 'Running'
                    : pending
                      ? 'Please wait'
                      : confirmed
                        ? 'Run Demo'
                        : 'Confirm Mapping'}
                </button>
              </div>
            </div>
            <section className="workspace">
              <aside className="library">
                <div className="section-label">
                  <h3>Demonstrations</h3>
                  <button
                    className="icon-button"
                    title="Upload MP4 video"
                    aria-label="Upload MP4 video"
                    disabled={locked}
                    onClick={() => input.current?.click()}
                  >
                    <Upload size={18} />
                  </button>
                  <input
                    ref={input}
                    type="file"
                    accept="video/mp4"
                    hidden
                    onChange={(event) => void upload(event.target.files?.[0])}
                  />
                </div>
                <div className="demo-list">
                  <button
                    className={camera ? 'selected camera-choice' : 'camera-choice'}
                    disabled={locked}
                    onClick={() => {
                      setCamera(true);
                      setRunId('');
                      setConfirmed(false);
                      setError('');
                    }}
                  >
                    <Camera size={22} />
                    <span>
                      <strong>Live Camera</strong>
                      <small>Browser camera</small>
                    </span>
                  </button>
                  {demos.map((demo) => (
                    <button
                      className={!camera && selected === demo.name ? 'selected' : ''}
                      key={demo.name}
                      disabled={locked}
                      onClick={() => choose(demo.name)}
                    >
                      <img
                        src={`/api/demonstrations/${encodeURIComponent(demo.name)}/preview`}
                        alt=""
                      />
                      <span>
                        <strong title={demo.name}>{displayName(demo.name)}</strong>
                        <small>{(demo.bytes / 1024 / 1024).toFixed(1)} MB</small>
                      </span>
                    </button>
                  ))}
                </div>
                {!demos.length && <p className="muted">No demonstrations available.</p>}
                <div className="calibration">
                  <h3>Workspace mapping</h3>
                  <label htmlFor="plane">Transport plane</label>
                  <select
                    id="plane"
                    value={plane}
                    disabled={locked}
                    onChange={(event) => {
                      setPlane(event.target.value as 'front' | 'table');
                      setConfirmed(false);
                    }}
                  >
                    <option value="front">Front plane (sideways)</option>
                    <option value="table">Projected table (two axes)</option>
                  </select>
                  <label htmlFor="span">
                    Horizontal span <span>{span.toFixed(2)} m</span>
                  </label>
                  <input
                    id="span"
                    type="range"
                    min="0.05"
                    max="0.5"
                    step="0.01"
                    value={span}
                    disabled={locked}
                    onChange={(event) => {
                      setSpan(Number(event.target.value));
                      setConfirmed(false);
                    }}
                  />
                  <fieldset>
                    <legend>Object hint (%)</legend>
                    <div className="roi-inputs">
                      {['X', 'Y', 'Width', 'Height'].map((name, index) => (
                        <label key={name}>
                          {name}
                          <input
                            type="number"
                            disabled={locked}
                            min="0"
                            max="100"
                            step="0.1"
                            value={Number((roi[index] * 100).toFixed(1))}
                            onChange={(event) => {
                              const next = [...roi] as Roi;
                              next[index] = Number(event.target.value) / 100;
                              setRoi(next);
                              setConfirmed(false);
                            }}
                          />
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  <p className={`mapping-state ${confirmed ? 'ready' : ''}`}>
                    {confirmed
                      ? `${plane === 'front' ? 'Front-plane' : 'Projected-table'} mapping confirmed`
                      : `${plane === 'front' ? 'Front-plane' : 'Projected-table'} mapping unconfirmed`}
                  </p>
                </div>
              </aside>
              <div className="media-workspace">
                <div className="media-grid">
                  <section className="media-tool">
                    <div className="media-heading">
                      <h3>
                        <Video size={17} />
                        Human demonstration
                      </h3>
                      {!camera && (
                        <div className="segmented">
                          <button
                            aria-pressed={mode === 'object'}
                            onClick={() => setMode('object')}
                          >
                            Mapping
                          </button>
                          <button aria-pressed={mode === 'video'} onClick={() => setMode('video')}>
                            Video
                          </button>
                        </div>
                      )}
                    </div>
                    {camera ? (
                      <LiveCamera
                        roi={roi}
                        confirmed={confirmed}
                        disabled={busy || pending || !available}
                        onLock={setCameraLocked}
                        onMapping={(value) => {
                          setRoi(value);
                          setConfirmed(false);
                        }}
                        onSave={saveRecording}
                      />
                    ) : selected ? (
                      mode === 'video' ? (
                        <div className="tracked-video">
                          <video
                            key={selected}
                            controls
                            preload="metadata"
                            src={`/api/demonstrations/${encodeURIComponent(selected)}`}
                            onLoadedMetadata={(event) =>
                              setSourceTime(event.currentTarget.currentTime)
                            }
                            onTimeUpdate={(event) => setSourceTime(event.currentTarget.currentTime)}
                            onSeeked={(event) => setSourceTime(event.currentTarget.currentTime)}
                          />
                          {tracked && (
                            <div
                              className="roi acquired"
                              aria-label="Tracked object"
                              style={{
                                left: `${tracked.box[0] * 100}%`,
                                top: `${tracked.box[1] * 100}%`,
                                width: `${tracked.box[2] * 100}%`,
                                height: `${tracked.box[3] * 100}%`,
                              }}
                            >
                              <span>Object</span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div
                          className="object-frame"
                          style={{ aspectRatio: frameRatio }}
                          onPointerDown={(event) => {
                            if (busy) return;
                            drag.current = coordinates(event);
                            event.currentTarget.setPointerCapture(event.pointerId);
                          }}
                          onPointerMove={draw}
                          onPointerUp={(event) => {
                            if (!drag.current) return;
                            const origin = drag.current;
                            const point = coordinates(event);
                            drag.current = null;
                            const width = Math.abs(point[0] - origin[0]);
                            const height = Math.abs(point[1] - origin[1]);
                            setRoi(
                              width < 0.03 && height < 0.03
                                ? clickHint(origin)
                                : [
                                    Math.min(point[0], origin[0]),
                                    Math.min(point[1], origin[1]),
                                    width,
                                    height,
                                  ],
                            );
                            setConfirmed(false);
                          }}
                        >
                          <img
                            src={`/api/demonstrations/${encodeURIComponent(selected)}/preview`}
                            alt="Selected demonstration first frame with object selection"
                            onLoad={(event) =>
                              setFrameRatio(
                                event.currentTarget.naturalWidth /
                                  event.currentTarget.naturalHeight,
                              )
                            }
                            draggable={false}
                          />
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
                        </div>
                      )
                    ) : (
                      <div className="empty-media">
                        <Video size={32} />
                        <span>No video selected</span>
                      </div>
                    )}
                    <div className="media-footer">
                      <span title={selected}>
                        {camera
                          ? 'Live Camera'
                          : selected
                            ? displayName(selected)
                            : 'Demonstration'}
                      </span>
                      <span>Source</span>
                    </div>
                  </section>
                  <section className="media-tool">
                    <div className="media-heading">
                      <h3>
                        <Activity size={17} />
                        Panda simulation
                      </h3>
                      <span className="badge">MuJoCo</span>
                    </div>
                    {run && run.status !== 'running' && run.video_available ? (
                      <video
                        key={run.run_id}
                        controls
                        preload="auto"
                        poster={`/api/runs/${run.run_id}/preview`}
                        src={`/api/runs/${run.run_id}/artifacts/simulation.mp4`}
                        onError={() => setError('Simulation video could not be loaded.')}
                      />
                    ) : (
                      <div className="empty-media">
                        {busy ? (
                          <LoaderCircle size={32} className="spin" />
                        ) : (
                          <Activity size={32} />
                        )}
                        <span>
                          {busy ? run?.phase || 'Processing' : 'Ready for a demonstration'}
                        </span>
                        <small>
                          {services.simulation?.status === 'ready'
                            ? 'Panda · LIBERO tabletop'
                            : 'Simulation unavailable'}
                        </small>
                      </div>
                    )}
                    <div className="media-footer">
                      <span>{run ? `Run ${run.run_id.slice(0, 8)}` : 'No run yet'}</span>
                      <span>Robot output</span>
                    </div>
                  </section>
                </div>
                <RunStatus key={run?.run_id} run={run} onObservations={setObservations} />
              </div>
            </section>
          </>
        )}
      </main>
      <footer>
        skill-to-bot <span>Local development · v0.1.0</span>
      </footer>
    </>
  );
}
