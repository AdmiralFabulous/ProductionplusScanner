import { useEffect, useRef, useCallback } from 'react'
import { useScanStore } from '../store/scanStore'
import { speakPrompt } from '../services/voiceApi'

export default function VoicePlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const {
    language,
    voiceEnabled,
    voiceSpeed,
    lastVoicePrompt,
    setLastVoicePrompt,
    currentStep,
  } = useScanStore()

  // Play voice prompt
  const playPrompt = useCallback(async (promptId: string) => {
    if (!voiceEnabled || lastVoicePrompt === promptId) return

    try {
      const audioBlob = await speakPrompt(language, promptId, voiceSpeed)
      const audioUrl = URL.createObjectURL(audioBlob)
      
      if (audioRef.current) {
        audioRef.current.src = audioUrl
        await audioRef.current.play()
        setLastVoicePrompt(promptId)
      }
    } catch (error) {
      console.error('Voice playback failed:', error)
    }
  }, [language, voiceEnabled, voiceSpeed, lastVoicePrompt, setLastVoicePrompt])

  // Auto-play prompts based on current step
  useEffect(() => {
    const stepPrompts: Record<string, string> = {
      welcome: 'welcome',
      consent: 'consent',
      setup: 'device_setup',
      calibrate: 'calibration',
      capture: 'capture_start',
      processing: 'processing',
      results: 'results',
    }

    const promptId = stepPrompts[currentStep]
    if (promptId) {
      // Small delay for better UX
      const timer = setTimeout(() => {
        playPrompt(promptId)
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [currentStep, playPrompt])

  return (
    <audio
      ref={audioRef}
      className="hidden"
      preload="auto"
    />
  )
}
