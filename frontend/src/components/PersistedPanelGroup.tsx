import { Group, useDefaultLayout, type GroupProps } from 'react-resizable-panels'

interface PersistedPanelGroupProps extends Omit<
  GroupProps,
  'id' | 'defaultLayout' | 'onLayoutChanged'
> {
  id: string
}

/** Wraps `Group` with layout persisted to localStorage, keyed by `id`. */
export function PersistedPanelGroup({ id, ...rest }: PersistedPanelGroupProps) {
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({ id, storage: localStorage })
  return <Group id={id} defaultLayout={defaultLayout} onLayoutChanged={onLayoutChanged} {...rest} />
}
