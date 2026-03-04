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
  const pendingAlertsRef = useRef([])

  const getSoundProfile = (failure) => {
    const rawType =
      (failure?.category || failure?.failure_type || failure?.metadata?.error_type || '')
        .toString()
        .toLowerCase()

    if (rawType.includes('network') || rawType.includes('timeout') || rawType.includes('connection')) {
      return { label: 'network', tones: [600, 520], durationMs: 180 }
    }

    return { label: 'other', tones: [900, 900], durationMs: 120 }
  }

  const playAlertSound = (failure) => {
    try {
      if (!audioUnlockedRef.current || !audioCtxRef.current) {
        pendingAlertsRef.current.push(failure)
        if (!audioHintShownRef.current) {
          audioHintShownRef.current = true
          showSnackbar('Click anywhere to enable sound alerts', 'generic')
        }
        return false
      }

      const ctx = audioCtxRef.current
      if (ctx.state !== 'running') {
        return false
      }

      const profile = getSoundProfile(failure)
      const now = ctx.currentTime
      const duration = profile.durationMs / 1000
      profile.tones.forEach((freq, idx) => {
        const oscillator = ctx.createOscillator()
        const gain = ctx.createGain()
        const t = now + idx * duration

        oscillator.type = 'square'
        oscillator.frequency.setValueAtTime(freq, t)

        gain.gain.setValueAtTime(0.0001, t)
        gain.gain.exponentialRampToValueAtTime(0.12, t + 0.02)
        gain.gain.exponentialRampToValueAtTime(0.0001, t + duration)

        oscillator.connect(gain)
        gain.connect(ctx.destination)

        oscillator.start(t)
        oscillator.stop(t + duration)
      })
      return true

    } catch (err) {
      console.warn('Audio alert blocked or unavailable:', err)
      return false
    }
  }

  const unlockAudio = () => {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      if (!AudioContext) return
      const ctx = audioCtxRef.current || new AudioContext()
      audioCtxRef.current = ctx
      const resumeResult = ctx.resume()
      if (resumeResult && typeof resumeResult.then === 'function') {
        resumeResult
          .then(() => {
            if (ctx.state === 'running') {
              audioUnlockedRef.current = true
              if (pendingAlertsRef.current.length > 0) {
                const queued = [...pendingAlertsRef.current]
                pendingAlertsRef.current = []
                queued.forEach((failure) => playAlertSound(failure))
              }
              showSnackbar('Sound alerts enabled', 'generic')
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

  const processClassificationAlerts = (nextFailures) => {
    const chronological = [...nextFailures].reverse()

    chronological.forEach((failure) => {
      const key = getFailureKey(failure)
      const currentCategory = failure.category || failure.failure_type
      const previousCategory = playedRef.current[key]

      if (shouldPlayForFailure(failure, previousCategory)) {
        playAlertSound(failure)
        const label = currentCategory || 'Unknown'
        const message = failure.error || failure.error_message || 'Failure detected'
        const variant = getSoundProfile(failure).label
        showSnackbar(`Failure detected · ${label}: ${message}`, variant)
      }

      playedRef.current[key] = currentCategory
      seenRef.current[key] = true
    })
  }

  const loadStatus = async () => {
    try {
      const data = await fetchBotStatus()
      const nextFailures = data.failures || []
      setBots(data.bots || {})
      setFailures(nextFailures)
      setLastUpdate(new Date().toLocaleString())

      if (nextFailures.length > 0) {
        processClassificationAlerts(nextFailures)
      }
    } catch (error) {
      console.error('Error loading status:', error)
    }
  }

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 3000)
    const gestureHandler = () => unlockAudio()
    window.addEventListener('pointerdown', gestureHandler)
    window.addEventListener('keydown', gestureHandler)
    return () => {
      clearInterval(interval)
      window.removeEventListener('pointerdown', gestureHandler)
      window.removeEventListener('keydown', gestureHandler)
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
