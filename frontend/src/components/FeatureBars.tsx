import { FEATURE_KEYS } from '../types/domain'
import type { GestureFeatureVector } from '../types/domain'
import { Panel } from './Panel'

interface FeatureBarsProps {
  features: GestureFeatureVector | null
}

export function FeatureBars({ features }: FeatureBarsProps) {
  return (
    <Panel
      title="Live motion features"
      badge={
        <span className="rounded-full border border-[rgb(110_168_255_/_0.25)] bg-[rgb(110_168_255_/_0.12)] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
          real-time
        </span>
      }
    >
      {!features ? (
        <div className="p-2 text-[12.5px] italic text-muted-2">
          Start a session to read your motion.
        </div>
      ) : (
        <>
          {FEATURE_KEYS.map((key) => {
            const v = features[key] ?? 0
            const pct = Math.min(
              100,
              Math.max(0, (key === 'valence' ? (v + 1) / 2 : Math.abs(v)) * 100),
            )
            return (
              <div key={key} className="grid grid-cols-[96px_1fr_44px] items-center gap-2.5 py-1">
                <label className="text-[11.5px] font-medium capitalize text-muted">
                  {key.replace(/_/g, ' ')}
                </label>
                <div className="h-[7px] overflow-hidden rounded bg-app-bg">
                  <div
                    className="brand-gradient-bg h-full rounded transition-[width] duration-150 ease-out"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-right font-mono text-[11px] text-text">{v.toFixed(2)}</span>
              </div>
            )
          })}
          <div className="grid grid-cols-[96px_1fr_44px] items-center gap-2.5 py-1">
            <label className="text-[11.5px] font-medium capitalize text-muted">hands</label>
            <div className="h-[7px] overflow-hidden rounded bg-app-bg">
              <div
                className="brand-gradient-bg h-full rounded transition-[width] duration-150 ease-out"
                style={{ width: features.hands_visible ? '100%' : '0%' }}
              />
            </div>
            <span className="text-right font-mono text-[11px] text-text">
              {features.hands_visible}
            </span>
          </div>
        </>
      )}
    </Panel>
  )
}
