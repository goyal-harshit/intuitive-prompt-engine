import { useState } from 'react'
import { Panel as ResizablePanel } from 'react-resizable-panels'
import { useSession } from './hooks/useSession'
import { useMediaQuery } from './hooks/useMediaQuery'
import { TopBar } from './components/TopBar'
import { ErrorBanner } from './components/ErrorBanner'
import { CameraPanel } from './components/CameraPanel'
import { FeatureBars } from './components/FeatureBars'
import { PrimitivesPanel } from './components/PrimitivesPanel'
import { IntentPanel } from './components/IntentPanel'
import { SceneGraphPanel } from './components/SceneGraphPanel'
import { GeneratedImagePanel } from './components/GeneratedImagePanel'
import { PromptPanel } from './components/PromptPanel'
import { DrawCanvasPanel } from './components/DrawCanvasPanel'
import { GestureDebugPanel } from './components/GestureDebugPanel'
import { SettingsModal } from './components/SettingsModal'
import { HelpModal } from './components/HelpModal'
import { ResizeHandle } from './components/ResizeHandle'
import { PersistedPanelGroup } from './components/PersistedPanelGroup'

function App() {
  const { state, start, stop, togglePause, resetScene, clearDraw, dismissBanner } = useSession()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const isWide = useMediaQuery('(min-width: 1150px)')

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopBar
        statusText={state.statusText}
        statusTone={state.statusTone}
        starting={state.starting}
        sessionActive={!!state.sessionId}
        paused={state.paused}
        onStart={start}
        onStop={stop}
        onTogglePause={togglePause}
        onReset={resetScene}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenHelp={() => setHelpOpen(true)}
      />

      {state.banner && (
        <ErrorBanner
          title={state.banner.title}
          message={state.banner.message}
          warn={state.banner.warn}
          onDismiss={dismissBanner}
        />
      )}

      {isWide ? (
        <main className="min-h-0 flex-1 overflow-hidden p-[14px_22px]">
          <PersistedPanelGroup id="layout-columns" orientation="horizontal">
            <ResizablePanel defaultSize={32} minSize={18}>
              <PersistedPanelGroup id="layout-col-1" orientation="vertical">
                <ResizablePanel defaultSize={36} minSize={15}>
                  <CameraPanel sessionId={state.sessionId} />
                </ResizablePanel>
                <ResizeHandle direction="vertical" />
                <ResizablePanel defaultSize={22} minSize={12}>
                  <FeatureBars features={state.features} />
                </ResizablePanel>
                <ResizeHandle direction="vertical" />
                <ResizablePanel defaultSize={42} minSize={15}>
                  <DrawCanvasPanel
                    drawPoints={state.drawPoints}
                    lastShape={state.lastShape}
                    onClear={clearDraw}
                  />
                </ResizablePanel>
              </PersistedPanelGroup>
            </ResizablePanel>

            <ResizeHandle direction="horizontal" />

            <ResizablePanel defaultSize={34} minSize={18}>
              <PersistedPanelGroup id="layout-col-2" orientation="vertical">
                <ResizablePanel defaultSize={25} minSize={12}>
                  <SceneGraphPanel scene={state.scene} completeness={state.completeness} />
                </ResizablePanel>
                <ResizeHandle direction="vertical" />
                <ResizablePanel defaultSize={25} minSize={12}>
                  <PrimitivesPanel primitives={state.primitives} />
                </ResizablePanel>
                <ResizeHandle direction="vertical" />
                <ResizablePanel defaultSize={25} minSize={12}>
                  <IntentPanel intents={state.intents} />
                </ResizablePanel>
                <ResizeHandle direction="vertical" />
                <ResizablePanel defaultSize={25} minSize={12}>
                  <GestureDebugPanel
                    debug={state.gestureDebug}
                    features={state.features}
                    ambient={state.ambient}
                  />
                </ResizablePanel>
              </PersistedPanelGroup>
            </ResizablePanel>

            <ResizeHandle direction="horizontal" />

            <ResizablePanel defaultSize={34} minSize={18}>
              <PersistedPanelGroup id="layout-col-3" orientation="vertical">
                <ResizablePanel defaultSize={70} minSize={25}>
                  <GeneratedImagePanel imageUrl={state.imageUrl} generating={state.generating} />
                </ResizablePanel>
                <ResizeHandle direction="vertical" />
                <ResizablePanel defaultSize={30} minSize={15}>
                  <PromptPanel prompt={state.prompt} />
                </ResizablePanel>
              </PersistedPanelGroup>
            </ResizablePanel>
          </PersistedPanelGroup>
        </main>
      ) : (
        <main className="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto p-[14px_22px]">
          <CameraPanel sessionId={state.sessionId} />
          <FeatureBars features={state.features} />
          <DrawCanvasPanel
            drawPoints={state.drawPoints}
            lastShape={state.lastShape}
            onClear={clearDraw}
          />
          <SceneGraphPanel scene={state.scene} completeness={state.completeness} />
          <PrimitivesPanel primitives={state.primitives} />
          <IntentPanel intents={state.intents} />
          <GestureDebugPanel
            debug={state.gestureDebug}
            features={state.features}
            ambient={state.ambient}
          />
          <GeneratedImagePanel imageUrl={state.imageUrl} generating={state.generating} />
          <PromptPanel prompt={state.prompt} />
        </main>
      )}

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
      <HelpModal open={helpOpen} onOpenChange={setHelpOpen} />
    </div>
  )
}

export default App
