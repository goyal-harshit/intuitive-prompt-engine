import type { SequenceSegment } from '../types/domain'
import { Panel } from './Panel'

interface PrimitivesPanelProps {
  primitives: SequenceSegment[]
}

export function PrimitivesPanel({ primitives }: PrimitivesPanelProps) {
  return (
    <Panel title="Motion primitives">
      {primitives.length === 0 ? (
        <div className="p-2 text-[12.5px] italic text-muted-2">No primitives yet.</div>
      ) : (
        primitives.map((seg) => (
          <div
            key={seg.id}
            className="mb-1.5 animate-[slidein_0.2s_ease] rounded-md border border-border-soft border-l-2 border-l-accent bg-panel-2 px-2.5 py-1.5 text-xs"
          >
            <b className="font-semibold text-text">{seg.primitive}</b>
            {' · '}
            {Math.round(seg.confidence * 100)}%{' · '}
            {seg.params.duration_s}s
          </div>
        ))
      )}
    </Panel>
  )
}
