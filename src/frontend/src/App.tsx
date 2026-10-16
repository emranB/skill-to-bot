// Purpose: Connect Home, the saved library and the drawing-to-Panda workflow.
import { useEffect, useRef, useState } from 'react';
import {
  ArrowRight,
  Bot,
  History,
  House,
  Library,
  LoaderCircle,
  MoveRight,
  PenLine,
  Play,
  Plus,
  Route,
} from 'lucide-react';
import config from '../config.json';
import { api, jsonBody } from './api';
import DrawingCanvas, { metadata, type Demonstration, type Stroke } from './DrawingCanvas';
import { DeleteRunDialog, DemoList, RunList, type SavedDemo } from './Library';
import Reproduction from './Reproduction';
import RunStatus, { type Run } from './RunStatus';

const views = [
  { id: 'home', label: 'Home', icon: House },
  { id: 'workspace', label: 'Workspace', icon: PenLine },
  { id: 'history', label: 'Run history', icon: History },
  { id: 'demos', label: 'Saved demos', icon: Library },
] as const;

export default function App() {
  const [view, setView] = useState<(typeof views)[number]['id']>('home');
  const [strokes, setStrokes] = useState<Stroke[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [run, setRun] = useState<Run>();
  const [runId, setRunId] = useState('');
  const [savedId, setSavedId] = useState('');
  const [aspectRatio, setAspectRatio] = useState(config.canvasAspectRatio);
  const [demos, setDemos] = useState<SavedDemo[]>([]);
  const [ready, setReady] = useState<boolean | null>(null);
  const [connected, setConnected] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [libraryLoaded, setLibraryLoaded] = useState(false);
  const [pending, setPending] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState<Run>();
  // Ignore stale poll responses that arrive after a confirmed history removal.
  const removed = useRef(new Set<string>());
  // Home shows completed human work, once per demonstration, never test fixtures.
  const featured: Run[] = [];
  for (const item of runs) {
    if (
      item.source_type === 'human_capture' &&
      item.status === 'completed' &&
      item.thumbnail_available &&
      !featured.some((previous) => previous.demonstration_id === item.demonstration_id)
    )
      featured.push(item);
    if (featured.length === 3) break;
  }
  const preview = featured.find((item) => item.video_available);
  const busy = runs.some((item) => item.status === 'running');
  const locked = busy || pending;
  useEffect(() => {
    if (view !== 'demos' && view !== 'home') return;
    const controller = new AbortController();
    void api<SavedDemo[]>('/demonstrations', { signal: controller.signal })
      .then((items) => {
        setDemos(items);
        setLibraryLoaded(true);
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) {
          setError(error.message);
          setLibraryLoaded(true);
        }
      });
    return () => controller.abort();
  }, [view, savedId]);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const [history, services, selected] = await Promise.all([
          api<Run[]>('/runs?summary=true', { signal: controller.signal }),
          api<{ simulation: { status: string } }>('/services', { signal: controller.signal }),
          runId
            ? api<Run>(`/runs/${runId}?summary=true`, { signal: controller.signal })
            : Promise.resolve(undefined),
        ]);
        if (controller.signal.aborted) return;
        setRuns(history.filter((item) => !removed.current.has(item.run_id)));
        setReady(services.simulation.status === 'ready');
        setConnected(true);
        setRun(selected);
        setLoaded(true);
      } catch {
        if (!controller.signal.aborted) {
          setReady(false);
          setConnected(false);
          setLoaded(true);
        }
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, config.statusPollSeconds * 1000);
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [runId]);

  function change(value: Stroke[]) {
    setStrokes(value);
    setSavedId('');
    setRunId('');
    setRun(undefined);
    setError('');
    if (!value.length) {
      setAspectRatio(config.canvasAspectRatio);
    }
  }
  function newDrawing() {
    change([]);
    setView('workspace');
  }
  async function loadDemo(id: string, selectedRunId = '') {
    setPending(true);
    setError('');
    try {
      const raw = await api<Demonstration>(`/demonstrations/${id}`);
      setStrokes(raw.strokes);
      setAspectRatio(raw.canvas.aspect_ratio);
      setSavedId(id);
      setRunId(selectedRunId);
      setRun(undefined);
      setView('workspace');
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  async function start(alternate = false) {
    setPending(true);
    setError('');
    try {
      let id = savedId;
      if (!id) {
        const raw: Demonstration = {
          version: '1.0',
          type: 'drawing',
          coordinate_space: 'normalized_screen',
          canvas: { aspect_ratio: aspectRatio },
          device: metadata(strokes),
          source: { type: 'human_capture' },
          strokes,
        };
        id = (await api<{ id: string }>('/demonstrations', jsonBody(raw))).id;
        setSavedId(id);
      }
      const next = await api<Run>(
        '/runs',
        jsonBody({
          demonstration_id: id,
          request_id: crypto.randomUUID(),
          paper_pose: alternate ? { offset: [0.015, -0.01], yaw: 0.12 } : null,
          reuse_run_id: alternate && run?.skill_available ? run.run_id : null,
        }),
      );
      setRunId(next.run_id);
      setRun(next);
      setRuns((history) => [next, ...history.filter((item) => item.run_id !== next.run_id)]);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setPending(false);
    }
  }
  async function deleteRun() {
    if (!deleting) return;
    await api<void>(`/runs/${deleting.run_id}`, { method: 'DELETE' });
    removed.current.add(deleting.run_id);
    setRuns((history) => history.filter((item) => item.run_id !== deleting.run_id));
    if (runId === deleting.run_id) {
      setRunId('');
      setRun(undefined);
    }
    setDeleting(undefined);
  }
  const openRun = (item: Run) => void loadDemo(item.demonstration_id, item.run_id);
  const openDemo = (id: string) => void loadDemo(id);

  return (
    <>
      <header className="app-header">
        <button
          className="brand"
          aria-label="skill-to-bot Home"
          disabled={drawing || pending}
          onClick={() => setView('home')}
        >
          <PenLine size={22} />
          skill-to-bot
        </button>
        <span
          role="status"
          className={`service ${ready ? (busy ? 'busy' : 'ready') : ready === null ? 'connecting' : ''}`}
        >
          <span className="status-dot" />
          {ready === null
            ? 'Connecting...'
            : !ready
              ? 'Simulation unavailable'
              : busy
                ? 'Run in progress'
                : 'Simulation ready'}
        </span>
        <div className="nav-row">
          <nav aria-label="Views">
            {views.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                aria-current={view === id ? 'page' : undefined}
                disabled={drawing || pending}
                onClick={() => setView(id)}
              >
                <Icon size={18} />
                <span>{label}</span>
                {id === 'history' && <span className="nav-count">{runs.length}</span>}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main>
        {(!connected || error) && (
          <p role="alert" className="alert">
            {connected ? error : 'Connection lost. Reconnecting...'}
          </p>
        )}
        {view === 'home' && (
          <>
            <section className="home-intro" aria-labelledby="home-title">
              <p className="eyebrow">HANDWRITING TO ROBOT MOTION</p>
              <h1 id="home-title">skill-to-bot</h1>
              <p className="home-tagline">Your strokes. A robot&apos;s next move.</p>
              <p className="home-description">
                Draw naturally. A simulated Panda follows your strokes on paper, with every movement
                recorded for you to see.
              </p>
              <div className="actions">
                <button className="primary" disabled={locked} onClick={newDrawing}>
                  <Plus size={18} />
                  New drawing
                </button>
                {preview && (
                  <button className="watch-run" disabled={pending} onClick={() => openRun(preview)}>
                    <Play size={16} />
                    Watch a run
                    <ArrowRight size={16} />
                  </button>
                )}
              </div>
              <ol className="drawing-flow" aria-label="Drawing workflow">
                <li>
                  <PenLine size={17} />
                  Draw
                </li>
                <li aria-hidden="true">
                  <MoveRight size={17} />
                </li>
                <li>
                  <Route size={17} />
                  Save
                </li>
                <li aria-hidden="true">
                  <MoveRight size={17} />
                </li>
                <li>
                  <Bot size={17} />
                  Reproduce
                </li>
              </ol>
            </section>
            <section className="home-section home-gallery">
              <div className="section-heading">
                <h2>From hand to paper</h2>
                <button className="text-button" onClick={() => setView('history')}>
                  History
                  <ArrowRight size={17} />
                </button>
              </div>
              <RunList
                runs={featured}
                loading={!loaded}
                disabled={pending}
                cards
                emptyMessage="No completed human drawings yet."
                onOpen={openRun}
              />
            </section>
            <dl className="overview">
              <div>
                <dt>Completed runs</dt>
                <dd>{loaded ? runs.filter((item) => item.status === 'completed').length : '-'}</dd>
              </div>
              <div>
                <dt>In progress</dt>
                <dd>{loaded ? runs.filter((item) => item.status === 'running').length : '-'}</dd>
              </div>
              <div>
                <dt>Saved demos</dt>
                <dd>{libraryLoaded ? demos.length : '-'}</dd>
              </div>
            </dl>
            <section className="home-section">
              <div className="section-heading">
                <h3>Saved demos</h3>
                <button className="text-button" onClick={() => setView('demos')}>
                  View all
                  <ArrowRight size={17} />
                </button>
              </div>
              <DemoList
                demos={demos.slice(0, 4)}
                loading={!libraryLoaded}
                disabled={pending}
                onOpen={openDemo}
              />
            </section>
          </>
        )}
        {view === 'history' && (
          <section>
            <div className="page-heading">
              <div>
                <h1>Run history</h1>
                <p className="muted">{runs.length} runs</p>
              </div>
            </div>
            <RunList
              runs={runs}
              loading={!loaded}
              disabled={pending}
              onOpen={openRun}
              onDelete={setDeleting}
            />
          </section>
        )}
        {view === 'demos' && (
          <section>
            <div className="page-heading">
              <div>
                <h1>Saved demos</h1>
                <p className="muted">{demos.length} demonstrations</p>
              </div>
            </div>
            <DemoList demos={demos} loading={!libraryLoaded} disabled={pending} onOpen={openDemo} />
          </section>
        )}
        {view === 'workspace' && (
          <>
            <div className="page-heading">
              <div>
                <h1>Workspace</h1>
                <p className="muted">
                  Human drawing
                  <ArrowRight size={14} />
                  Panda reproduction
                </p>
              </div>
              <div className="actions">
                <button
                  className="icon-button"
                  title="New drawing"
                  aria-label="New drawing"
                  disabled={locked || drawing}
                  onClick={newDrawing}
                >
                  <Plus size={20} />
                </button>
                <button
                  className="primary"
                  disabled={locked || drawing || !ready || !strokes.length}
                  onClick={() => void start()}
                >
                  {locked ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}
                  {pending ? 'Working...' : busy ? 'Running' : 'Save & Run'}
                </button>
              </div>
            </div>
            <div className="workspace">
              <section>
                <div className="section-heading">
                  <h3>Human Drawing</h3>
                  <span className="muted">{savedId ? 'Saved' : 'Unsaved'}</span>
                </div>
                <DrawingCanvas
                  key={savedId || 'draft'}
                  strokes={strokes}
                  onChange={change}
                  disabled={locked}
                  drawing={drawing}
                  onDrawingChange={setDrawing}
                  aspectRatio={aspectRatio}
                />
              </section>
              <section>
                <Reproduction
                  run={run}
                  disabled={locked || drawing || !ready}
                  onRetarget={() => void start(true)}
                />
              </section>
            </div>
            <RunStatus run={run} />
          </>
        )}
      </main>
      {deleting && (
        <DeleteRunDialog
          run={deleting}
          onCancel={() => setDeleting(undefined)}
          onConfirm={deleteRun}
        />
      )}
    </>
  );
}
