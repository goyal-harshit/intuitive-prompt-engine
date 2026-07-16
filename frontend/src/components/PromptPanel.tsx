import { Panel } from './Panel'

interface PromptPanelProps {
  prompt: string
}

export function PromptPanel({ prompt }: PromptPanelProps) {
  return (
    <Panel
      title="Compiled prompt"
      flex="flex-none"
      bodyClassName="max-h-[100px] overflow-y-auto px-3.5 py-3 text-xs leading-relaxed text-muted"
    >
      {prompt}
    </Panel>
  )
}
