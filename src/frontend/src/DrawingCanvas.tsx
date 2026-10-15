// Purpose: Capture real pointer samples and render human strokes without altering saved input.
import { useEffect, useRef, useState } from 'react';
import { Undo2, Trash2 } from 'lucide-react';
import config from '../config.json';

export type Point = {
  x: number;
  y: number;
  t_ms: number;
  pressure?: number;
  pointer_type: 'pen' | 'touch' | 'mouse';
  tilt_x?: number;
  tilt_y?: number;
  twist?: number;
};
export type Stroke = { points: Point[]; color?: string; brush_size?: number };
export type Demonstration = {
  version: '1.0';
  type: 'drawing';
  coordinate_space: 'normalized_screen';
  canvas: { aspect_ratio: number };
  device: {
    pointer_type: 'pen' | 'touch' | 'mouse' | 'mixed';
    pressure_observed: boolean;
  };
  source: { type: 'human_capture' | 'synthetic_fixture' };
  strokes: Stroke[];
};

export function metadata(strokes: Stroke[]) {
  const points = strokes.flatMap((s) => s.points);
  const types = new Set(points.map((p) => p.pointer_type));
  const pressureObserved = ['pen', 'touch'].some((kind) => {
    const values = points
      .filter((p) => p.pointer_type === kind && (p.pressure ?? 0) > 0)
      .map((p) => p.pressure!);
    return (
      values.length > 0 && Math.max(...values) - Math.min(...values) > config.pressureTolerance
    );
  });
  return {
    pointer_type: (types.size > 1
      ? 'mixed'
      : points[0]?.pointer_type || 'mouse') as Demonstration['device']['pointer_type'],
    pressure_observed: pressureObserved,
  };
}

function renderStrokes(canvas: HTMLCanvasElement, strokes: Stroke[]) {
  const context = canvas.getContext('2d')!;
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.lineCap = 'round';
  context.lineJoin = 'round';
  for (const stroke of strokes) {
    context.strokeStyle = stroke.color ?? config.defaultColor;
    let pressure = config.defaultPressure;
    for (let i = 1; i < stroke.points.length; i++) {
      const a = stroke.points[i - 1],
        b = stroke.points[i];
      if (b.pointer_type !== 'mouse' && (b.pressure ?? 0) > 0) pressure = b.pressure!;
      context.lineWidth =
        (stroke.brush_size ?? config.defaultBrushSize) * canvas.height * (0.5 + pressure);
      context.beginPath();
      context.moveTo(a.x * canvas.width, a.y * canvas.height);
      context.lineTo(b.x * canvas.width, b.y * canvas.height);
      context.stroke();
    }
  }
}

export default function DrawingCanvas({
  strokes,
  onChange,
  disabled,
  drawing,
  onDrawingChange,
  aspectRatio = config.canvasAspectRatio,
}: {
  strokes: Stroke[];
  onChange: (strokes: Stroke[]) => void;
  disabled: boolean;
  drawing: boolean;
  onDrawingChange: (drawing: boolean) => void;
  aspectRatio?: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const active = useRef<{ id: number; stroke: Stroke } | null>(null);
  const captured = useRef(strokes);
  const origin = useRef<number | null>(null);
  const [warning, setWarning] = useState('');
  const [color, setColor] = useState(strokes.at(-1)?.color ?? config.defaultColor);
  const [brushSize, setBrushSize] = useState(strokes.at(-1)?.brush_size ?? config.defaultBrushSize);
  const [liveDevice, setLiveDevice] = useState<ReturnType<typeof metadata> | null>(null);
  const device = liveDevice ?? metadata(strokes);
  const sampleCount = strokes.reduce((count, stroke) => count + stroke.points.length, 0);
  captured.current = strokes;
  useEffect(() => {
    if (canvas.current) renderStrokes(canvas.current, strokes);
  }, [strokes, aspectRatio]);

  function append(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!active.current || active.current.id !== event.pointerId) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const source = event.nativeEvent;
    const samples =
      typeof source.getCoalescedEvents === 'function' ? source.getCoalescedEvents() : [];
    const events = samples.length ? samples : [source];
    for (const e of events) {
      const last = active.current.stroke.points.at(-1);
      const t = Math.max(
        last?.t_ms ?? captured.current.at(-1)?.points.at(-1)?.t_ms ?? 0,
        e.timeStamp - (origin.current ?? e.timeStamp),
      );
      if (
        t > config.maxSessionMs ||
        sampleCount + active.current.stroke.points.length >= config.maxSamples
      ) {
        setWarning('Drawing limit reached. Save this drawing or clear it.');
        break;
      }
      active.current.stroke.points.push({
        x: Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)),
        y: Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height)),
        t_ms: t,
        ...(e.pointerType === 'pen' || e.pointerType === 'touch' ? { pressure: e.pressure } : {}),
        pointer_type:
          e.pointerType === 'pen' ? 'pen' : e.pointerType === 'touch' ? 'touch' : 'mouse',
        ...(e.pointerType === 'pen' && typeof e.tiltX === 'number'
          ? { tilt_x: e.tiltX, tilt_y: e.tiltY }
          : {}),
        ...(e.pointerType === 'pen' && typeof e.twist === 'number' ? { twist: e.twist } : {}),
      });
    }
    const live = [...captured.current, active.current.stroke];
    const input = metadata(live);
    setLiveDevice(input);
    if (canvas.current) renderStrokes(canvas.current, live);
  }
  function finish(event: React.PointerEvent<HTMLCanvasElement>, cancelled = false) {
    if (!active.current || active.current.id !== event.pointerId) return;
    if (!cancelled) append(event);
    const stroke = active.current.stroke;
    const points = stroke.points;
    active.current = null;
    onDrawingChange(false);
    setLiveDevice(null);
    event.currentTarget.releasePointerCapture(event.pointerId);
    if (
      points.length > 1 &&
      points.some((p) => Math.hypot(p.x - points[0].x, p.y - points[0].y) > 0.0001)
    )
      onChange([...captured.current, stroke]);
    else if (canvas.current) renderStrokes(canvas.current, captured.current);
  }
  return (
    <>
      <div className="brush-tools" aria-label="Drawing tools">
        <label className="color-tool">
          Color
          <input
            type="color"
            aria-label="Brush color"
            value={color}
            disabled={disabled || drawing}
            onChange={(e) => setColor(e.target.value)}
          />
        </label>
        <label className="size-tool" htmlFor="brush-size">
          Brush size
          <input
            id="brush-size"
            aria-label="Brush size"
            type="range"
            min="2"
            max="30"
            step="1"
            value={brushSize * 600}
            disabled={disabled || drawing}
            onChange={(e) => setBrushSize(Number(e.target.value) / 600)}
          />
          <output htmlFor="brush-size">{Math.round(brushSize * 600)} px</output>
        </label>
      </div>
      <canvas
        ref={canvas}
        width={900}
        height={Math.round(900 / aspectRatio)}
        aria-label="Human drawing surface"
        className="drawing-surface"
        style={{
          touchAction: 'none',
          aspectRatio,
        }}
        onPointerDown={(event) => {
          if (disabled || active.current || event.button !== 0) return;
          if (captured.current.length >= config.maxStrokes) {
            setWarning('Stroke limit reached.');
            return;
          }
          event.preventDefault();
          if (!captured.current.length) origin.current = event.timeStamp;
          else if (origin.current === null)
            origin.current = event.timeStamp - (captured.current.at(-1)?.points.at(-1)?.t_ms ?? 0);
          active.current = {
            id: event.pointerId,
            stroke: { points: [], color, brush_size: brushSize },
          };
          event.currentTarget.setPointerCapture(event.pointerId);
          onDrawingChange(true);
          append(event);
        }}
        onPointerMove={append}
        onPointerUp={(event) => finish(event)}
        onPointerCancel={(event) => finish(event, true)}
        onLostPointerCapture={() => {
          active.current = null;
          onDrawingChange(false);
          setLiveDevice(null);
          if (canvas.current) renderStrokes(canvas.current, captured.current);
        }}
      />
      <div className="canvas-toolbar">
        <span>
          {device.pointer_type === 'mixed'
            ? 'Mixed input'
            : device.pointer_type.charAt(0).toUpperCase() + device.pointer_type.slice(1)}
        </span>
        <span className={device.pressure_observed ? 'success-text' : 'muted'}>
          {device.pressure_observed ? 'Variable pressure' : 'Constant pressure'}
        </span>
        <span>
          {strokes.length} {strokes.length === 1 ? 'stroke' : 'strokes'}
        </span>
        <span>{sampleCount} samples</span>
        <div className="tools">
          <button
            title="Undo last stroke"
            aria-label="Undo last stroke"
            disabled={disabled || drawing || !strokes.length}
            onClick={() => onChange(strokes.slice(0, -1))}
          >
            <Undo2 size={18} />
          </button>
          <button
            title="Clear drawing"
            aria-label="Clear drawing"
            disabled={disabled || drawing || !strokes.length}
            onClick={() => {
              origin.current = null;
              setWarning('');
              onChange([]);
            }}
          >
            <Trash2 size={18} />
          </button>
        </div>
      </div>
      {warning && (
        <p role="alert" className="error-text">
          {warning}
        </p>
      )}
    </>
  );
}
