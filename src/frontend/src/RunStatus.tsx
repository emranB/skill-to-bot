// Purpose: Display actual drawing execution progress, metrics and independently inspectable artifacts.
import { useEffect, useMemo, useState } from 'react';
import { CircleCheck, CircleAlert, LoaderCircle } from 'lucide-react';
import { api } from './api';

const tabs = ['Logs', 'Raw Input', 'Skill', 'Trace'];
const phases: Record<string, string> = {
  processing: 'Preparing skill',
  executing: 'Starting Panda',
  initializing: 'Preparing Panda',
  approach: 'Approaching paper',
  descend: 'Lowering pen',
  draw: 'Drawing',
  lift: 'Lifting pen',
  park: 'Finishing drawing',
  completed: 'Evaluating result',
};

export function phaseName(phase: string) {
  return phases[phase] || phase;
}

export type Run = {
  run_id: string;
  demonstration_id: string;
  status: string;
  phase: string;
  created_at: number;
  source_type?: string;
  stroke_index?: number;
  stroke_count?: number;
  video_available?: boolean;
  thumbnail_available?: boolean;
  result?: {
    mean_path_error_m: number | null;
    p95_path_error_m: number | null;
    max_shape_error_m?: number | null;
    contact_coverage: number;
    physical_contact_coverage?: number;
    strokes_completed: number;
    stroke_count: number;
  };
  error?: string;
  logs?: { time: number; message: string }[];
  skill_available?: boolean;
};

export default function RunStatus({ run }: { run?: Run }) {
  const [tab, setTab] = useState('Logs');
  const [detail, setDetail] = useState<unknown>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    setDetail(null);
    setError('');
    if (!run || tab === 'Logs') return;
    const controller = new AbortController();
    const path =
      tab === 'Raw Input'
        ? `/demonstrations/${run.demonstration_id}`
        : `/runs/${run.run_id}/artifacts/${tab === 'Skill' ? 'skill' : 'trace'}.json`;
    api(path, { signal: controller.signal })
      .then(setDetail)
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message);
      });
    return () => controller.abort();
  }, [run?.run_id, run?.status, run?.skill_available, tab]);
  const content = useMemo(
    () => (detail ? JSON.stringify(detail, null, 2) : 'Loading...'),
    [detail],
  );
  if (!run)
    return (
      <section className="run-details">
        <h3>Run status</h3>
        <p className="muted">No run selected.</p>
      </section>
    );
  const stage = run.status === 'completed' ? 2 : run.skill_available ? 1 : 0;
  const elapsed = Math.max(0, Math.floor(Date.now() / 1000 - run.created_at));
  const millimeters = (value: number | null | undefined) =>
    value == null ? 'Unavailable' : `${(value * 1000).toFixed(2)} mm`;
  const percent = (value: number | undefined) =>
    value == null ? 'Unavailable' : `${(value * 100).toFixed(1)}%`;
  const result = run.result;
  const metrics = result
    ? [
        ['Mean path error', millimeters(result.mean_path_error_m)],
        ['95th percentile', millimeters(result.p95_path_error_m)],
        ['Shape error', millimeters(result.max_shape_error_m)],
        ['Paper proximity', percent(result.contact_coverage)],
        ['Physical contact', percent(result.physical_contact_coverage)],
        ['Strokes reproduced', `${result.strokes_completed}/${result.stroke_count}`],
      ]
    : [];
  return (
    <section className="run-details">
      <div className="section-heading">
        <h3>Run status</h3>
        <span className={`status ${run.status}`}>
          {run.status === 'running' ? (
            <LoaderCircle className="spin" size={18} />
          ) : run.status === 'completed' ? (
            <CircleCheck size={18} />
          ) : (
            <CircleAlert size={18} />
          )}{' '}
          {run.status === 'running' ? phaseName(run.phase) : run.status}
          {run.status === 'running' &&
            run.stroke_index !== undefined &&
            ` · Stroke ${run.stroke_index + 1}/${run.stroke_count}`}
        </span>
      </div>
      {run.status === 'running' && (
        <p className="muted">
          {Math.floor(elapsed / 60)}m {elapsed % 60}s elapsed
        </p>
      )}
      <ol className="run-stages" aria-label="Execution stages">
        {['Prepare skill', 'Draw on paper', 'Review result'].map((label, index) => (
          <li
            key={label}
            className={index < stage || run.status === 'completed' ? 'done' : ''}
            aria-current={index === stage ? 'step' : undefined}
          >
            <span>
              {index < stage || run.status === 'completed' ? <CircleCheck size={18} /> : index + 1}
            </span>
            {label}
          </li>
        ))}
      </ol>
      {run.status === 'running' && run.stroke_index !== undefined && run.stroke_count && (
        <progress
          aria-label="Stroke progress"
          value={run.stroke_index ? Math.min(run.stroke_index, run.stroke_count) : undefined}
          max={run.stroke_count}
        />
      )}
      {run.error && (
        <p role="alert" className="error-text">
          {run.error}
        </p>
      )}
      {result && (
        <dl className="metrics">
          {metrics.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      )}
      <div role="tablist" aria-label="Run details" className="detail-tabs">
        {tabs.map((name, index) => (
          <button
            role="tab"
            id={`detail-tab-${index}`}
            aria-controls="run-panel"
            tabIndex={name === tab ? 0 : -1}
            aria-selected={name === tab}
            key={name}
            onClick={() => setTab(name)}
            onKeyDown={(event) => {
              const targets: Record<string, number> = {
                ArrowRight: (index + 1) % tabs.length,
                ArrowLeft: (index + tabs.length - 1) % tabs.length,
                Home: 0,
                End: tabs.length - 1,
              };
              const next = targets[event.key];
              if (next === undefined) return;
              event.preventDefault();
              setTab(tabs[next]);
              document.getElementById(`detail-tab-${next}`)?.focus();
            }}
          >
            {name}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id="run-panel"
        aria-labelledby={`detail-tab-${tabs.indexOf(tab)}`}
        tabIndex={0}
        className="detail-content"
      >
        {tab === 'Logs' ? (
          <ol className="logs">
            {run.logs?.map((log, index) => (
              <li key={index}>
                <time>{new Date(log.time * 1000).toLocaleTimeString()}</time>
                {log.message}
              </li>
            ))}
          </ol>
        ) : (
          <pre>{error || content}</pre>
        )}
      </div>
    </section>
  );
}
