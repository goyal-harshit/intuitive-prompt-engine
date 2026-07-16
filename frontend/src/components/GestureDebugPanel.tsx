import type { GestureDebugPayload, GestureFeatureVector } from '../types/domain'
import { Panel } from './Panel'

interface GestureDebugPanelProps {
  debug: GestureDebugPayload | null
  features: GestureFeatureVector | null
  ambient: Record<string, number>
}

function AffectRow({
  label,
  raw,
  smoothed,
  signed = true,
}: {
  label: string
  raw: number
  smoothed: number | undefined
  signed?: boolean
}) {
  const toPct = (v: number) => Math.min(100, Math.max(0, (signed ? (v + 1) / 2 : v) * 100))
  return (
    <div className="mb-2 py-1">
      <div className="mb-1 flex items-center justify-between text-[11.5px] font-medium capitalize text-muted">
        <span>{label}</span>
        <span className="font-mono text-[11px] text-muted-2">
          raw {raw.toFixed(2)} · smoothed {smoothed === undefined ? '—' : smoothed.toFixed(2)}
        </span>
      </div>
      <div className="relative h-[7px] overflow-hidden rounded bg-app-bg">
        <div
          className="absolute inset-y-0 left-0 rounded bg-[rgb(110_168_255_/_0.35)] transition-[width] duration-150 ease-out"
          style={{ width: `${toPct(raw)}%` }}
        />
        {smoothed !== undefined && (
          <div
            className="brand-gradient-bg absolute inset-y-0 left-0 w-[2px] transition-[left] duration-300 ease-out"
            style={{ left: `${toPct(smoothed)}%` }}
          />
        )}
      </div>
    </div>
  )
}

export function GestureDebugPanel({ debug, features, ambient }: GestureDebugPanelProps) {
  const matches = debug?.matches ?? []

  return (
    <Panel
      title="Gesture transparency"
      badge={
        debug?.drawing && (
          <span className="rounded-full border border-[rgb(110_168_255_/_0.25)] bg-[rgb(110_168_255_/_0.12)] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
            drawing
          </span>
        )
      }
    >
      <h3 className="mb-1.5 mt-0 text-[10.5px] font-semibold uppercase tracking-wider text-muted-2">
        What's matching right now
      </h3>
      {matches.length === 0 ? (
        <div className="mb-3 p-2 text-[12.5px] italic text-muted-2">
          Move to see live primitive matches and what they'd mean.
        </div>
      ) : (
        <div className="mb-3">
          {matches.map((m) => (
            <div key={m.primitive} className="mb-1.5 py-1">
              <div className="mb-1 flex items-center justify-between text-[11.5px] font-medium text-muted">
                <span className="capitalize text-text">{m.primitive.replace(/_/g, ' ')}</span>
                <span className="font-mono text-[11px] text-muted-2">
                  {Math.round(m.match_score * 100)}%
                </span>
              </div>
              <div className="h-[6px] overflow-hidden rounded bg-app-bg">
                <div
                  className="brand-gradient-bg h-full rounded transition-[width] duration-150 ease-out"
                  style={{ width: `${Math.min(100, Math.max(0, m.match_score * 100))}%` }}
                />
              </div>
              <p className="mt-1 text-[11px] text-muted-2">would mean: {m.would_mean}</p>
            </div>
          ))}
        </div>
      )}

      <h3 className="mb-1.5 mt-3 text-[10.5px] font-semibold uppercase tracking-wider text-muted-2">
        Raw vs. smoothed mood
      </h3>
      {!features ? (
        <div className="p-2 text-[12.5px] italic text-muted-2">
          Start a session to compare raw and smoothed affect.
        </div>
      ) : (
        <>
          <AffectRow label="valence" raw={features.valence} smoothed={ambient.valence} />
          <AffectRow
            label="arousal"
            raw={features.arousal}
            smoothed={ambient.arousal}
            signed={false}
          />
        </>
      )}
    </Panel>
  )
}
