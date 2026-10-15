// Purpose: Present saved work consistently and confirm removal from run history.
import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, LoaderCircle, PenLine, Trash2 } from 'lucide-react';
import type { Run } from './RunStatus';

export type SavedDemo = { id: string; strokes: number };

function runTitle(run: Run) {
  return run.source_type === 'synthetic_fixture' ? 'Fixture drawing' : 'Drawing';
}

export function RunList({
  runs,
  disabled,
  loading = false,
  cards = false,
  emptyMessage = 'No runs yet.',
  onOpen,
  onDelete,
}: {
  runs: Run[];
  disabled: boolean;
  cards?: boolean;
  loading?: boolean;
  emptyMessage?: string;
  onOpen: (run: Run) => void;
  onDelete?: (run: Run) => void;
}) {
  if (!runs.length)
    return <p className="empty-state">{loading ? 'Loading runs...' : emptyMessage}</p>;
  return (
    <div className={cards ? 'run-grid' : 'history'}>
      {runs.map((run) => (
        <article className="run-item" key={run.run_id} data-run-id={run.run_id}>
          <button className="run-open" disabled={disabled} onClick={() => onOpen(run)}>
            <span className="run-preview">
              <PenLine size={24} />
              {run.thumbnail_available && (
                <img
                  src={`/api/runs/${run.run_id}/artifacts/simulator-final.png`}
                  alt={`Simulator result: ${runTitle(run)}`}
                  loading={cards ? 'eager' : 'lazy'}
                  onError={(event) => {
                    event.currentTarget.style.display = 'none';
                  }}
                />
              )}
            </span>
            <span className="item-copy">
              <strong>{runTitle(run)}</strong>
              <small>
                {run.stroke_count ?? 0} {run.stroke_count === 1 ? 'stroke' : 'strokes'} ·{' '}
                {new Date(run.created_at * 1000).toLocaleString(undefined, {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })}
              </small>
            </span>
            <span className={`status ${run.status}`}>
              <span className="status-dot" />
              {run.status}
            </span>
            <ArrowUpRight size={18} className="open-arrow" />
          </button>
          {onDelete && (
            <button
              className="icon-button delete-run"
              title="Delete from history"
              aria-label={`Delete ${runTitle(run)} from history`}
              disabled={disabled || run.status === 'running'}
              onClick={() => onDelete(run)}
            >
              <Trash2 size={18} />
            </button>
          )}
        </article>
      ))}
    </div>
  );
}

export function DemoList({
  demos,
  disabled,
  loading = false,
  onOpen,
}: {
  demos: SavedDemo[];
  disabled: boolean;
  loading?: boolean;
  onOpen: (id: string) => void;
}) {
  if (!demos.length)
    return <p className="empty-state">{loading ? 'Loading demos...' : 'No saved demos yet.'}</p>;
  return (
    <div className="demo-list">
      {demos.map((demo) => (
        <button key={demo.id} disabled={disabled} onClick={() => onOpen(demo.id)}>
          <span className="demo-icon">
            <PenLine size={22} />
          </span>
          <span className="item-copy">
            <strong>Drawing</strong>
            <small>
              {demo.strokes} {demo.strokes === 1 ? 'stroke' : 'strokes'} · Human capture
            </small>
          </span>
          <ArrowUpRight size={18} />
        </button>
      ))}
    </div>
  );
}

export function DeleteRunDialog({
  run,
  onCancel,
  onConfirm,
}: {
  run: Run;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const element = dialog.current;
    const previousFocus = document.activeElement as HTMLElement | null;
    element?.showModal();
    return () => {
      element?.close();
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      aria-labelledby="delete-title"
      aria-describedby="delete-description"
      onCancel={(event) => {
        event.preventDefault();
        if (!pending) onCancel();
      }}
    >
      <h2 id="delete-title">Delete from history?</h2>
      <p className="dialog-name">{runTitle(run)}</p>
      <p id="delete-description">The saved demonstration and execution files will be kept.</p>
      {error && (
        <p role="alert" className="error-text">
          {error}
        </p>
      )}
      <div className="dialog-actions">
        <button autoFocus disabled={pending} onClick={onCancel}>
          Cancel
        </button>
        <button
          className="danger"
          disabled={pending}
          onClick={async () => {
            setPending(true);
            setError('');
            try {
              await onConfirm();
            } catch (error) {
              setError((error as Error).message);
            } finally {
              setPending(false);
            }
          }}
        >
          {pending ? <LoaderCircle size={18} className="spin" /> : <Trash2 size={18} />}Delete from
          history
        </button>
      </div>
    </dialog>
  );
}
