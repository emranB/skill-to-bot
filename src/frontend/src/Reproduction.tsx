// Purpose: Play actual simulator recordings and expose playback and retargeting controls.
import { useRef, useState } from 'react';
import { ArrowUpRight, LoaderCircle, PenLine } from 'lucide-react';
import { apiUrl } from './api';
import { phaseName, type Run } from './RunStatus';

export default function Reproduction({
  run,
  disabled,
  onRetarget,
}: {
  run?: Run;
  disabled: boolean;
  onRetarget: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [speed, setSpeed] = useState(1);
  return (
    <>
      <div className="section-heading">
        <h3>Panda Reproduction</h3>
        <span className="muted">
          {run?.status === 'running' ? phaseName(run.phase) : run?.status || 'Waiting'}
        </span>
      </div>
      <div className="media-toolbar">
        <span className="muted">Playback</span>
        <div className="playback-speeds" role="group" aria-label="Playback speed">
          {[1, 2, 5, 10].map((rate) => (
            <button
              key={rate}
              aria-pressed={speed === rate}
              disabled={!run?.video_available}
              onClick={() => {
                setSpeed(rate);
                if (video.current) video.current.playbackRate = rate;
              }}
            >
              {rate}x
            </button>
          ))}
        </div>
      </div>
      <div className="robot-surface">
        {run?.video_available ? (
          <video
            ref={video}
            key={run.run_id}
            aria-label="Panda drawing simulation"
            src={apiUrl(`/runs/${run.run_id}/artifacts/simulation.mp4`)}
            controls
            autoPlay
            muted
            playsInline
            preload="metadata"
            onLoadedMetadata={() => {
              if (video.current) video.current.playbackRate = speed;
            }}
          />
        ) : (
          <div className="waiting">
            {run?.status === 'running' ? (
              <LoaderCircle className="spin" size={28} />
            ) : (
              <PenLine size={28} />
            )}
            <span>
              {run?.status === 'running'
                ? phaseName(run.phase)
                : run?.status === 'failed'
                  ? 'Drawing stopped'
                  : run
                    ? 'Recording unavailable'
                    : 'Waiting for a drawing'}
            </span>
          </div>
        )}
      </div>
      <div className="result-actions">
        {run?.skill_available ? (
          <button disabled={disabled} onClick={onRetarget}>
            <ArrowUpRight size={17} />
            Run on shifted paper
          </button>
        ) : (
          <span className="muted">Simulator recording</span>
        )}
      </div>
    </>
  );
}
