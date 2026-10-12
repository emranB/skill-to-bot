// Purpose: Edit measured support geometry and display its reference corners.
export type Point = [number, number];
export type Surface = {
  corners: (Point | null)[];
  size: [number, number];
  horizontal_fov: number;
  object_height: number;
  image_aspect: number;
};

const corners = ['Near left', 'Near right', 'Far right', 'Far left'];

export function SurfaceOutline({ surface }: { surface: Surface }) {
  return (
    <svg
      className="surface-outline"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-label="Calibrated surface corners"
    >
      {surface.corners.every(Boolean) && (
        <polygon
          points={surface.corners.map((point) => `${point![0] * 100},${point![1] * 100}`).join(' ')}
        />
      )}
      {surface.corners.map(
        (point, index) =>
          point && (
            <g key={index}>
              <circle cx={point[0] * 100} cy={point[1] * 100} r="1.2" />
              <text x={point[0] * 100 + 2} y={point[1] * 100 - 1}>
                {index + 1}
              </text>
            </g>
          ),
      )}
    </svg>
  );
}

export default function SurfaceMapping({
  surface,
  point,
  disabled,
  onPoint,
  onChange,
}: {
  surface: Surface;
  point: number;
  disabled: boolean;
  onPoint: (point: number) => void;
  onChange: (surface: Surface) => void;
}) {
  const fields = [
    [
      'Surface width (m)',
      surface.size[0],
      0.05,
      2,
      (value: number) => ({ ...surface, size: [value, surface.size[1]] as [number, number] }),
    ],
    [
      'Surface depth (m)',
      surface.size[1],
      0.05,
      2,
      (value: number) => ({ ...surface, size: [surface.size[0], value] as [number, number] }),
    ],
    [
      'Object height (m)',
      surface.object_height,
      0.01,
      0.5,
      (value: number) => ({ ...surface, object_height: value }),
    ],
    [
      'Camera horizontal FOV (deg)',
      surface.horizontal_fov,
      35,
      120,
      (value: number) => ({ ...surface, horizontal_fov: value }),
    ],
  ] as const;
  return (
    <fieldset disabled={disabled}>
      <legend>Measured support</legend>
      <div className="roi-inputs">
        {fields.map(([label, value, min, max, change]) => (
          <label key={label}>
            {label}
            <input
              type="number"
              min={min}
              max={max}
              step={max === 120 ? 1 : 0.01}
              value={value || ''}
              onChange={(event) => onChange(change(Number(event.target.value)))}
            />
          </label>
        ))}
      </div>
      <label className="reference-label">
        Reference point
        <select value={point} onChange={(event) => onPoint(Number(event.target.value))}>
          <option value={-1}>Object hint</option>
          {corners.map((name, index) => (
            <option key={name} value={index}>
              {index + 1}. {name}
            </option>
          ))}
        </select>
      </label>
      {point >= 0 && (
        <div className="roi-inputs">
          {['Corner X (%)', 'Corner Y (%)'].map((label, axis) => (
            <label key={label}>
              {label}
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={
                  surface.corners[point]
                    ? Number((surface.corners[point]![axis] * 100).toFixed(1))
                    : ''
                }
                onChange={(event) => {
                  const next = [...surface.corners];
                  const corner = [...(next[point] || [0, 0])] as Point;
                  corner[axis] = Number(event.target.value) / 100;
                  next[point] = corner;
                  onChange({ ...surface, corners: next });
                }}
              />
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}
