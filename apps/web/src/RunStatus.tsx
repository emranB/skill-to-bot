// Purpose: Show run progress, recorded logs, skill intent, and tracked observations.
import { useEffect, useState } from 'react';
import { CheckCircle2, Circle, LoaderCircle, XCircle } from 'lucide-react';

export type Run = {
  run_id: string;
  video: string;
  status: string;
  phase: string;
  error: string | null;
  created_at: number;
  result?: { success: boolean; position_error_m: number; lifted: boolean; released: boolean };
  skill?: Record<string, unknown>;
  limitations?: string[];
  logs?: { time: number; message: string }[];
  video_available?: boolean;
};
export type Observation = {
  time: number;
  u: number;
  v: number;
  confidence: number;
  box: number[];
  on_surface?: boolean;
  segmentation_source?: string;
  geometry_source?: string;
  surface_position?: number[];
  height_m?: number;
};

const phases = [
  ['processing', 'Extract skill'],
  ['approach', 'Approach'],
  ['descend', 'Descend'],
  ['grasp', 'Grasp'],
  ['lift', 'Lift'],
  ['transport', 'Transport'],
  ['place', 'Place'],
  ['release', 'Release'],
  ['retreat', 'Retreat'],
];

export default function RunStatus({
  run,
  onObservations,
}: {
  run?: Run;
  onObservations: (samples: Observation[]) => void;
}) {
  const [tab, setTab] = useState('Logs');
  const [observations, setObservations] = useState<Observation[]>([]);
  const [error, setError] = useState('');
  const runId = run?.run_id;
  const hasSkill = Boolean(run?.skill);

  useEffect(() => {
    setObservations([]);
    onObservations([]);
    setError('');
    if (!runId || !hasSkill) return;
    const controller = new AbortController();
    fetch(`/api/runs/${runId}/artifacts/observations.json`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('Observations could not be loaded.');
        return response.json();
      })
      .then((samples) => {
        setObservations(samples);
        onObservations(samples);
      })
      .catch((problem) => {
        if (!controller.signal.aborted) setError(problem.message);
      });
    return () => controller.abort();
  }, [runId, hasSkill, onObservations]);

  const phaseIndex = phases.findIndex(([name]) => name === run?.phase);
  const completed = run?.status === 'completed';
  const failed = run?.status === 'failed';
  const current =
    phases[phaseIndex]?.[1] || (run?.phase === 'executing' ? 'Starting simulation' : 'Preparing');
  const StatusIcon = completed ? CheckCircle2 : failed ? XCircle : LoaderCircle;
  const summary = !run
    ? 'Waiting for a demo'
    : completed
      ? 'Transfer complete'
      : failed
        ? 'Run stopped'
        : current;

  function details() {
    if (tab === 'Logs') {
      if (!run?.logs?.length)
        return <p className="muted">{run ? 'No recorded logs for this run.' : 'No run yet.'}</p>;
      return (
        <ol className="run-logs">
          {run.logs.map((entry, index) => (
            <li key={index}>
              <time>{new Date(entry.time * 1000).toLocaleTimeString()}</time>
              <span>{entry.message}</span>
            </li>
          ))}
        </ol>
      );
    }
    if (tab === 'Skill') {
      if (!run?.skill) return <p className="muted">Skill appears after video processing.</p>;
      return (
        <>
          <pre>{JSON.stringify(run.skill, null, 2)}</pre>
          {run.limitations?.map((note) => (
            <p className="muted" key={note}>
              {note}
            </p>
          ))}
        </>
      );
    }
    if (error) return <p className="run-error">{error}</p>;
    if (!observations.length)
      return <p className="muted">Observations appear after object tracking.</p>;
    return (
      <>
        <p className="muted">{observations.length} tracked frames · Normalized image coordinates</p>
        {observations[0]?.segmentation_source && (
          <p className="muted">
            Acquisition:{' '}
            {observations[0].segmentation_source === 'yolo' ? 'YOLO' : 'GrabCut fallback'}
          </p>
        )}
        <table>
          <thead>
            <tr>
              <th>Time (s)</th>
              <th>X</th>
              <th>Y</th>
              <th>Confidence</th>
              <th>Surface</th>
              <th>Geometry</th>
              <th>Rectangle (x, y, w, h)</th>
              {observations[0].surface_position && <th>Support (lateral, depth, height m)</th>}
            </tr>
          </thead>
          <tbody>
            {observations.map((sample, index) => (
              <tr key={index}>
                <td>{sample.time.toFixed(2)}</td>
                <td>{sample.u.toFixed(3)}</td>
                <td>{sample.v.toFixed(3)}</td>
                <td>{sample.confidence.toFixed(2)}</td>
                <td>
                  {sample.on_surface === undefined
                    ? 'Unknown'
                    : sample.on_surface
                      ? 'On surface'
                      : 'Lifted'}
                </td>
                <td>{sample.geometry_source || 'Tracker'}</td>
                <td>{sample.box.map((value) => value.toFixed(3)).join(', ')}</td>
                {observations[0].surface_position && (
                  <td>
                    {[...sample.surface_position!, sample.height_m!]
                      .map((value) => value.toFixed(3))
                      .join(', ')}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </>
    );
  }

  return (
    <section className="run-detail" aria-label="Run status">
      <div className="section-label">
        <h3>Run status</h3>
        {run && (
          <span className={`run-status ${run.status}`}>
            <StatusIcon size={16} className={run.status === 'running' ? 'spin' : undefined} />
            {run.status}
          </span>
        )}
      </div>
      <p className="progress-summary" role="status">
        {summary}
        <span>
          {run ? new Date(run.created_at * 1000).toLocaleTimeString() : 'Mapping not run yet'}
        </span>
      </p>
      <div className="phases" aria-label="Execution progress">
        {phases.map(([name, label], index) => {
          const done = completed || index < phaseIndex;
          const active = name === run?.phase && !completed;
          const Icon = done ? CheckCircle2 : active ? StatusIcon : Circle;
          return (
            <div
              key={name}
              className={done ? 'done' : active ? 'active' : ''}
              aria-current={active ? 'step' : undefined}
            >
              <Icon size={16} className={active && !failed ? 'spin' : undefined} />
              <strong>{label}</strong>
            </div>
          );
        })}
      </div>
      {run?.error && <p className="run-error">{run.error}</p>}
      {run?.result && (
        <div className="metrics">
          <span>
            Placement error <strong>{(run.result.position_error_m * 1000).toFixed(1)} mm</strong>
          </span>
          <span>
            Lift <strong>{run.result.lifted ? 'Verified' : 'Failed'}</strong>
          </span>
          <span>
            Release <strong>{run.result.released ? 'Verified' : 'Failed'}</strong>
          </span>
        </div>
      )}
      <div className="detail-tabs" role="tablist" aria-label="Run details">
        {['Logs', 'Skill', 'Observations'].map((name) => (
          <button
            key={name}
            id={`tab-${name}`}
            role="tab"
            aria-selected={tab === name}
            aria-controls="run-panel"
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <div
        id="run-panel"
        role="tabpanel"
        aria-labelledby={`tab-${tab}`}
        className="detail-panel"
        tabIndex={0}
      >
        {details()}
      </div>
    </section>
  );
}
