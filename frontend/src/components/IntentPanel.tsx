import type { IntentFrame } from '../types/domain'
import { Panel } from './Panel'

interface IntentPanelProps {
  intents: IntentFrame[]
}

export function IntentPanel({ intents }: IntentPanelProps) {
  return (
    <Panel title="Intent stream">
      {intents.length === 0 ? (
        <div className="p-2 text-[12.5px] italic text-muted-2">
          Inferred intentions will appear here.
        </div>
      ) : (
        intents.map((frame) => (
          <div
            key={frame.id}
            className="mb-1.5 animate-[slidein_0.2s_ease] rounded-md border border-border-soft border-l-2 border-l-accent bg-panel-2 px-2.5 py-1.5 text-xs"
          >
            <b className="font-semibold text-text">{frame.attribute}</b> → {frame.value}{' '}
            <span className="text-muted">
              ({frame.confidence}
              {frame.modifiers.length ? `, ${frame.modifiers.join(', ')}` : ''})
            </span>
          </div>
        ))
      )}
    </Panel>
  )
}
