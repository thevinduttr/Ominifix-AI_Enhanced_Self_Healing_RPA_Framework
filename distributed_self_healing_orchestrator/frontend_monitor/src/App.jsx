import { useState, useEffect, useRef } from 'react'
import Header from './components/Header'
import BotsTable from './components/BotsTable'
import ChartsPanel from './components/ChartsPanel'
import { fetchBotStatus } from './services/api'

const ERROR_TYPE_BY_ID = {
  '0': 'UI_SELECTOR_CHANGED',
  '1': 'ELEMENT_NOT_VISIBLE',
  '2': 'TIMEOUT_ERROR',
  '3': 'APPLICATION_UPDATE',
  '4': 'NETWORK_ERROR',
  '5': 'BOT_LOGIC_ERROR',
  '6': 'ENV_CONFIG_ERROR',
  '7': 'AUTHENTICATION_ERROR',
  '8': 'UNKNOWN',
}

const SOUND_PROFILES = {
  UI_SELECTOR_CHANGED: {
    label: 'UI selector changed tone',
    tones: [740, 660],
    durationMs: 140,
    variant: 'ui',
  },
  ELEMENT_NOT_VISIBLE: {
    label: 'Element not visible tone',
    tones: [520, 390],
    durationMs: 170,
    variant: 'assert',
  },
  TIMEOUT_ERROR: {
    label: 'Timeout error tone',
    tones: [350, 350, 350],
    durationMs: 120,
    variant: 'assert',
  },
  APPLICATION_UPDATE: {
    label: 'Application update tone',
    tones: [820, 720, 620],
    durationMs: 100,
    variant: 'ui',
  },
  NETWORK_ERROR: {
    label: 'Network error tone',
    tones: [600, 520],
    durationMs: 180,
    variant: 'network',
  },
  BOT_LOGIC_ERROR: {
    label: 'Bot logic error tone',
    tones: [430, 520, 430],
    durationMs: 140,
    variant: 'generic',
  },
  ENV_CONFIG_ERROR: {
    label: 'Environment config error tone',
    tones: [300, 460],
    durationMs: 180,
    variant: 'generic',
  },
  AUTHENTICATION_ERROR: {
    label: 'Authentication error tone',
    tones: [960, 640, 960],
    durationMs: 110,
    variant: 'generic',
  },
  UNKNOWN: {
    label: 'Unknown error tone',
    tones: [900],
    durationMs: 150,
    variant: 'generic',
  },
}

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
  const loadStatusRef = useRef(null)
  const unlockAudioRef = useRef(null)

  const resolveErrorType = (failure) => {
    const raw =
      failure?.category ??
      failure?.failure_type ??
      failure?.metadata?.error_type ??
      failure?.metadata?.classification

    if (raw == null) return 'UNKNOWN'

    const rawStr = String(raw).trim()
    if (ERROR_TYPE_BY_ID[rawStr]) {
      return ERROR_TYPE_BY_ID[rawStr]
    }

    const normalized = rawStr.toUpperCase().replace(/\s+/g, '_')
    if (SOUND_PROFILES[normalized]) {
      return normalized
    }

    return 'UNKNOWN'
  }

  const getSoundProfile = (failure) => {
    const errorType = resolveErrorType(failure)
    return SOUND_PROFILES[errorType] || SOUND_PROFILES.UNKNOWN
  }

  const enqueuePendingAlert = (failure) => {
    pendingAlertsRef.current.push(failure)
    if (pendingAlertsRef.current.length > 20) {
      pendingAlertsRef.current.shift()
    }
  }

  const flushPendingAlerts = () => {
    if (!audioUnlockedRef.current || !audioCtxRef.current || pendingAlertsRef.current.length === 0) {
      return
    }

    const queued = [...pendingAlertsRef.current]
    pendingAlertsRef.current = []
    queued.forEach((failure) => playAlertSound(failure))
  }

  const playAlertSound = async (failure) => {
    try {
      let ctx = audioCtxRef.current

      if (!ctx || ctx.state !== 'running') {
        await unlockAudio(false)
        ctx = audioCtxRef.current
      }

      if (!ctx || ctx.state !== 'running') {
        enqueuePendingAlert(failure)
        if (!audioHintShownRef.current) {
          audioHintShownRef.current = true
          showSnackbar('Click anywhere to enable sound alerts', 'generic')
        }
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

  const unlockAudio = async (showEnabledMessage = true) => {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      if (!AudioContext) return false
      const ctx = audioCtxRef.current || new AudioContext()
      audioCtxRef.current = ctx

      if (ctx.state !== 'running') {
        await ctx.resume()
      }

      if (ctx.state === 'running') {
        audioUnlockedRef.current = true
        flushPendingAlerts()
        if (showEnabledMessage) {
          showSnackbar('Sound alerts enabled', 'generic')
        }
        return true
      }
      return false
    } catch {
      // If this fails, we'll retry on next gesture.
      return false
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
    const category = resolveErrorType(failure)
    if (!category) return false
    if (category === 'PENDING' || category === 'UNKNOWN') return false
    return previousCategory !== category
  }

  const processClassificationAlerts = (nextFailures) => {
    const chronological = [...nextFailures].reverse()

    chronological.forEach((failure) => {
      const key = getFailureKey(failure)
      const currentCategory = resolveErrorType(failure)
      const previousCategory = playedRef.current[key]

      if (shouldPlayForFailure(failure, previousCategory)) {
        playAlertSound(failure)
        const label = currentCategory || 'Unknown'
        const message = failure.error || failure.error_message || 'Failure detected'
        const profile = getSoundProfile(failure)
        showSnackbar(`Failure detected · ${label}: ${message}`, profile.variant)
      }

      playedRef.current[key] = currentCategory
      seenRef.current[key] = true
    })
  }

  const loadStatus = async () => {
    try {
      const data = await fetchBotStatus()
      const nextFailures = (data.failures || []).map((failure) => {
        const profile = getSoundProfile(failure)
        return {
          ...failure,
          metadata: {
            ...(failure.metadata || {}),
            sound: profile.label,
          },
        }
      })
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

  loadStatusRef.current = loadStatus
  unlockAudioRef.current = unlockAudio

  useEffect(() => {
    loadStatusRef.current?.()
    const interval = setInterval(() => loadStatusRef.current?.(), 3000)
    const gestureHandler = () => {
      unlockAudioRef.current?.(true)
    }
    window.addEventListener('pointerdown', gestureHandler)
    window.addEventListener('keydown', gestureHandler)
    return () => {
      clearInterval(interval)
      window.removeEventListener('pointerdown', gestureHandler)
      window.removeEventListener('keydown', gestureHandler)
    }
  }, [])

  const handleUserGesture = () => {
    unlockAudio(true)
  }

  const handleFailureClick = async (failure) => {
    await playAlertSound(failure)
    const label = resolveErrorType(failure)
    const message = failure.error || failure.error_message || 'Failure detected'
    const profile = getSoundProfile(failure)
    showSnackbar(`Failure detected · ${label}: ${message}`, profile.variant)
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
