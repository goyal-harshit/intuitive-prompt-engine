import type { DrawnShape, StrokePoint } from '../types/domain'
import { Panel } from './Panel'

interface DrawCanvasPanelProps {
  drawPoints: StrokePoint[]
  lastShape: DrawnShape | null
  onClear: () => void
}

function pointsToPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return ''
  const [first, ...rest] = points
  return `M ${first.x} ${first.y} ` + rest.map((p) => `L ${p.x} ${p.y}`).join(' ')
}

export function DrawCanvasPanel({ drawPoints, lastShape, onClear }: DrawCanvasPanelProps) {
  const hasContent = drawPoints.length > 0 || lastShape !== null

  return (
    <Panel
      title="Air-draw canvas"
      bodyClassName="flex flex-1 flex-col p-3"
      badge={
        <button
          type="button"
          onClick={onClear}
          className="rounded-full border border-border-soft bg-panel-2 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted transition-colors hover:border-accent hover:text-accent"
        >
          Clear
        </button>
      }
    >
      <div className="relative flex min-h-0 w-full flex-1 items-center justify-center overflow-hidden rounded-lg border border-border bg-app-bg">
        <svg viewBox="0 0 1 1" className="h-full w-full" preserveAspectRatio="xMidYMid meet">
          {lastShape && (
            <path
              d={pointsToPath(lastShape.points)}
              fill="none"
              stroke="var(--color-muted-2)"
              strokeWidth={0.006}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="0.012 0.01"
            />
          )}
          {drawPoints.length > 0 && (
            <path
              d={pointsToPath(drawPoints)}
              fill="none"
              stroke="var(--color-accent)"
              strokeWidth={0.008}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
        </svg>
        {!hasContent && (
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 p-[18px] text-center text-xs text-muted-2">
            <p>
              Pinch thumb and index finger together, then move your hand to draw. Release the pinch
              to finalize the shape.
            </p>
          </div>
        )}
      </div>
      {lastShape && (
        <div className="mt-2.5 rounded-md border border-border-soft bg-panel-2 px-2.5 py-1.5 text-xs">
          <b className="font-semibold capitalize text-text">{lastShape.shape}</b>
          {' · '}
          {Math.round(lastShape.confidence * 100)}%{' · '}
          <span className="text-muted">{lastShape.position_label}</span>
        </div>
      )}
    </Panel>
  )
}
