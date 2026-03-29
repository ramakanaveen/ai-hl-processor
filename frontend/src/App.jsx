import { useEffect, useRef, useState } from 'react'
import { LiveFeed } from './components/LiveFeed/LiveFeed'
import { History } from './components/History/History'
import { Insights } from './components/Insights/Insights'
import { Dashboard } from './components/Dashboard/Dashboard'
import { EndOfDay } from './components/EndOfDay/EndOfDay'
import { CorrectionModal } from './components/Corrections/CorrectionModal'
import { normalizeHeadline } from './utils/results'
import './styles.css'

const TABS = ['History', 'Dashboard', 'End of Day']
const MIN_LEFT_WIDTH = 320
const MIN_RIGHT_WIDTH = 360
const MIN_TOP_HEIGHT = 180
const MIN_BOTTOM_HEIGHT = 220

export default function App() {
  const [activeTab, setActiveTab] = useState('History')
  const [correcting, setCorrecting] = useState(null)
  const [correctionOverrides, setCorrectionOverrides] = useState({})
  const [activeLiveHeadlines, setActiveLiveHeadlines] = useState([])
  const [liveWindowMs, setLiveWindowMs] = useState(2 * 60 * 1000)
  const [leftPaneWidth, setLeftPaneWidth] = useState(48)
  const [topPaneHeight, setTopPaneHeight] = useState(36)
  const [dragging, setDragging] = useState(null)
  const mainLayoutRef = useRef(null)
  const rightColumnRef = useRef(null)

  function handleCorrectionSaved(updatedResult) {
    if (!updatedResult?.headline) return

    setCorrectionOverrides(current => ({
      ...current,
      [normalizeHeadline(updatedResult.headline)]: updatedResult,
    }))
  }

  useEffect(() => {
    if (!dragging) return undefined

    function onMouseMove(event) {
      if (dragging === 'vertical' && mainLayoutRef.current) {
        const rect = mainLayoutRef.current.getBoundingClientRect()
        const nextLeft = event.clientX - rect.left
        const clamped = Math.min(
          Math.max(nextLeft, MIN_LEFT_WIDTH),
          rect.width - MIN_RIGHT_WIDTH
        )
        setLeftPaneWidth((clamped / rect.width) * 100)
      }

      if (dragging === 'horizontal' && rightColumnRef.current) {
        const rect = rightColumnRef.current.getBoundingClientRect()
        const nextTop = event.clientY - rect.top
        const clamped = Math.min(
          Math.max(nextTop, MIN_TOP_HEIGHT),
          rect.height - MIN_BOTTOM_HEIGHT
        )
        setTopPaneHeight((clamped / rect.height) * 100)
      }
    }

    function onMouseUp() {
      setDragging(null)
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)

    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [dragging])

  return (
    <div className="app">
      <header className="topbar">
        <span className="logo">HL Impact</span>
        <nav className="tabs">
          {TABS.map(tab => (
            <button
              key={tab}
              className={`tab ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>

      <main
        ref={mainLayoutRef}
        className={`main-layout ${dragging ? 'is-dragging' : ''}`}
        style={{ '--left-pane-width': `${leftPaneWidth}%` }}
      >
        <section className="col-left pane">
          <LiveFeed
            onCorrect={setCorrecting}
            correctionOverrides={correctionOverrides}
            onActiveHeadlinesChange={setActiveLiveHeadlines}
            liveWindowMs={liveWindowMs}
            onLiveWindowChange={setLiveWindowMs}
          />
        </section>

        <div
          className="pane-resizer pane-resizer-vertical"
          onMouseDown={() => setDragging('vertical')}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize columns"
        />

        <section
          ref={rightColumnRef}
          className="col-right"
          style={{ '--top-pane-height': `${topPaneHeight}%` }}
        >
          <div className="pane pane-top">
            <Insights />
          </div>

          <div
            className="pane-resizer pane-resizer-horizontal"
            onMouseDown={() => setDragging('horizontal')}
            role="separator"
            aria-orientation="horizontal"
            aria-label="Resize right panels"
          />

          <div className="pane pane-bottom">
            {activeTab === 'History' && (
              <History
                onCorrect={setCorrecting}
                correctionOverrides={correctionOverrides}
                activeHeadlineKeys={activeLiveHeadlines}
              />
            )}
            {activeTab === 'Dashboard' && <Dashboard />}
            {activeTab === 'End of Day' && <EndOfDay />}
          </div>
        </section>
      </main>

      {correcting && (
        <CorrectionModal
          result={correcting}
          onSaved={handleCorrectionSaved}
          onClose={() => setCorrecting(null)}
        />
      )}
    </div>
  )
}
