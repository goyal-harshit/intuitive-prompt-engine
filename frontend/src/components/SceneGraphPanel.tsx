import type { AttributeValue, SceneGraph } from '../types/domain'
import { Panel, PanelNumberBadge } from './Panel'

interface SceneGraphPanelProps {
  scene: SceneGraph | null
  completeness: number
}

function AttrRow({ label, attr }: { label: string; attr: AttributeValue }) {
  return (
    <div className="grid grid-cols-[92px_1fr_58px] items-center gap-2.5 py-[3px]">
      <label className="truncate text-[11.5px] capitalize text-muted">
        {label.replace(/_/g, ' ')}
      </label>
      <span className="truncate whitespace-nowrap text-xs capitalize text-text">{attr.value}</span>
      <div className="h-[5px] overflow-hidden rounded bg-app-bg">
        <div
          className="brand-gradient-bg h-full rounded"
          style={{ width: `${attr.confidence * 100}%` }}
        />
      </div>
    </div>
  )
}

export function SceneGraphPanel({ scene, completeness }: SceneGraphPanelProps) {
  const objects = scene ? Object.values(scene.objects) : []
  const globals = scene ? Object.entries(scene.globals) : []
  const pct = Math.min(100, Math.max(0, completeness * 100))

  return (
    <Panel
      title={
        <>
          <PanelNumberBadge n={2} />
          Scene graph
        </>
      }
      badge={
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-[84px] overflow-hidden rounded bg-app-bg">
            <div
              className="brand-gradient-bg h-full rounded transition-[width] duration-300 ease-out"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="min-w-[32px] text-right font-mono text-[11.5px] font-medium text-accent">
            {Math.floor(pct)}%
          </span>
        </div>
      }
    >
      {objects.length === 0 && globals.length === 0 ? (
        <div className="p-2 text-[12.5px] italic text-muted-2">
          Gesture to begin shaping the scene…
        </div>
      ) : (
        <>
          {objects.length > 0 && (
            <>
              <h3 className="mb-1.5 mt-0 text-[10.5px] font-semibold uppercase tracking-wider text-muted-2">
                Objects
              </h3>
              {objects.map((obj) => (
                <div
                  key={obj.id}
                  className="mb-2 rounded-lg border border-border bg-panel-2 px-2.5 py-2"
                >
                  <b className="brand-gradient-text text-[13.5px] capitalize">{obj.category}</b>{' '}
                  <span className="text-[11px] text-muted">salience {obj.salience.toFixed(2)}</span>
                  {Object.entries(obj.attributes).map(([key, attr]) => (
                    <AttrRow key={key} label={key} attr={attr} />
                  ))}
                </div>
              ))}
            </>
          )}
          {globals.length > 0 && (
            <>
              <h3 className="mb-1.5 mt-3 text-[10.5px] font-semibold uppercase tracking-wider text-muted-2">
                Environment · Mood · Style
              </h3>
              {globals.map(([key, attr]) => (
                <AttrRow key={key} label={key} attr={attr} />
              ))}
            </>
          )}
        </>
      )}
    </Panel>
  )
}
