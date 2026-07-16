import { Separator } from 'react-resizable-panels'

export function ResizeHandle({ direction }: { direction: 'horizontal' | 'vertical' }) {
  return (
    <Separator
      className={
        direction === 'horizontal'
          ? 'group relative mx-0.5 w-1.5 flex-none rounded-full outline-none'
          : 'group relative my-0.5 h-1.5 flex-none rounded-full outline-none'
      }
    >
      <div
        className={
          direction === 'horizontal'
            ? 'absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-border transition-colors group-hover:bg-accent group-data-[separator=active]:bg-accent'
            : 'absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border transition-colors group-hover:bg-accent group-data-[separator=active]:bg-accent'
        }
      />
    </Separator>
  )
}
