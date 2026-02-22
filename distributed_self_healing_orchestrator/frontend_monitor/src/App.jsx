import { useState, useEffect, useRef } from 'react'
import Header from './components/Header'
import BotsTable from './components/BotsTable'
import ChartsPanel from './components/ChartsPanel'
import { fetchBotStatus } from './services/api'

function App() {
  const [bots, setBots] = useState({})
  const [failures, setFailures] = useState([])
  const [lastUpdate, setLastUpdate] = useState('--')
  const [snackbar, setSnackbar] = useState({ open: false, message: '', variant: 'generic' })
  const playedRef = useRef({})
  const seenRef = useRef({})
  const snackbarTimerRef = useRef(null)
  const audioCtxRef = useRef(null)
  const audioUnlockedRef = useRef(false)
  const audioHintShownRef = useRef(false)

  const getSoundProfile = (failure) => {
    const rawType =
      (failure?.category || failure?.failure_type || failure?.metadata?.error_type || '')
        .toString()
        .toLowerCase()

    if (rawType.includes('network') || rawType.includes('timeout') || rawType.includes('connection')) {
      return { label: 'network', tones: [600, 520], durationMs: 180 }
    }

    if (
      rawType.includes('selector') ||
      rawType.includes('locator') ||
      rawType.includes('element') ||
      rawType.includes('not found')
    ) {
      return { label: 'ui', tones: [880, 1200], durationMs: 140 }
    }

    if (rawType.includes('assert') || rawType.includes('validation')) {
      return { label: 'assert', tones: [740, 740], durationMs: 120 }
    }

    return { label: 'generic', tones: [880], durationMs: 200 }
  }

  const playAlertSound = (failure) => {
    try {
      if (!audioUnlockedRef.current || !audioCtxRef.current) {
        if (!audioHintShownRef.current) {
          audioHintShownRef.current = true
          showSnackbar('Click anywhere to enable sound alerts', 'generic')
        }
        return
      }

      const ctx = audioCtxRef.current

      const profile = getSoundProfile(failure)
      const oscillator = ctx.createOscillator()
      const gain = ctx.createGain()

      oscillator.type = 'sine'
      gain.gain.value = 0.04

      oscillator.connect(gain)
      gain.connect(ctx.destination)

      const now = ctx.currentTime
      const duration = profile.durationMs / 1000
      profile.tones.forEach((freq, idx) => {
        const t = now + idx * duration
        oscillator.frequency.setValueAtTime(freq, t)
      })

      oscillator.start()
      oscillator.stop(now + profile.tones.length * duration)

    } catch (err) {
      console.warn('Audio alert blocked or unavailable:', err)
    }
  }

  const unlockAudio = () => {
    if (audioUnlockedRef.current) return
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      if (!AudioContext) return
      const ctx = new AudioContext()
      audioCtxRef.current = ctx
      const resumeResult = ctx.resume()
      if (resumeResult && typeof resumeResult.then === 'function') {
        resumeResult
          .then(() => {
            if (ctx.state === 'running') {
              audioUnlockedRef.current = true
            }
          })
          .catch(() => {
            // If this fails, we'll retry on next gesture.
          })
      } else if (ctx.state === 'running') {
        audioUnlockedRef.current = true
      }
    } catch (err) {
      // If this fails, we'll retry on next gesture.
    }
  }

  const showSnackbar = (message, variant) => {
    setSnackbar({ open: true, message, variant })
    if (snackbarTimerRef.current) {
      clearTimeout(snackbarTimerRef.current)
    }
    snackbarTimerRef.current = setTimeout(() => {
      setSnackbar((prev) => ({ ...prev, open: false }))
    }, 4500)
  }

  const getFailureKey = (failure) => `${failure.botId || 'unknown'}:${failure.timestamp || 0}`

  const shouldPlayForFailure = (failure, previousCategory) => {
    const category = failure.category || failure.failure_type
    if (!category) return false
    if (category === 'pending' || category === 'unknown') return false
    return previousCategory !== category
  }

  const loadStatus = async () => {
    try {
      const data = await fetchBotStatus()
      const nextFailures = data.failures || []
      setBots(data.bots || {})
      setFailures(nextFailures)
      setLastUpdate(new Date().toLocaleString())

      const latest = nextFailures[0]
      if (latest) {
        const key = getFailureKey(latest)
        const previousCategory = playedRef.current[key]
        if (shouldPlayForFailure(latest, previousCategory)) {
          playAlertSound(latest)
        }
        playedRef.current[key] = latest.category || latest.failure_type

        if (!seenRef.current[key]) {
          seenRef.current[key] = true
          playAlertSound(latest)
          const label = latest.category || latest.failure_type || 'Unknown'
          const message = latest.error || latest.error_message || 'Failure detected'
          const variant = getSoundProfile(latest).label
          showSnackbar(`Failure detected · ${label}: ${message}`, variant)
        }
      }
    } catch (error) {
      console.error('Error loading status:', error)
    }
  }

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 3000)
    return () => {
      clearInterval(interval)
    }
  }, [])

  const handleUserGesture = () => {
    unlockAudio()
  }

  const handleFailureClick = (failure) => {
    playAlertSound(failure)
    const label = failure.category || failure.failure_type || 'Unknown'
    const message = failure.error || failure.error_message || 'Failure detected'
    const variant = getSoundProfile(failure).label
    showSnackbar(`Failure detected · ${label}: ${message}`, variant)
  }

  return (
    <>
      <div onClick={handleUserGesture} onKeyDown={handleUserGesture} role="presentation">
        <Header lastUpdate={lastUpdate} onRefresh={loadStatus} />
        
        <div className="card">
          <div className="card-left">
            <BotsTable bots={bots} />
          </div>
          
          <div className="card-right">
            <ChartsPanel bots={bots} failures={failures} onFailureClick={handleFailureClick} />
          </div>
        </div>

        <div className={`snackbar ${snackbar.variant} ${snackbar.open ? 'show' : ''}`}>
          {snackbar.message}
        </div>
      </div>
    </>
  )
}

export default App
