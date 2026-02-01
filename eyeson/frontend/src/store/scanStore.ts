import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type ScanStep = 
  | 'welcome' 
  | 'consent' 
  | 'setup' 
  | 'calibrate' 
  | 'capture' 
  | 'processing' 
  | 'results'

export interface CalibrationData {
  scaleFactor: number
  confidence: number
  markerDetected: boolean
}

export interface Measurement {
  name: string
  value: number
  unit: string
  confidence: number
  grade: 'P0' | 'P1'
}

interface ScanState {
  // Current step
  currentStep: ScanStep
  steps: ScanStep[]
  setStep: (step: ScanStep) => void
  nextStep: () => void
  previousStep: () => void
  reset: () => void

  // Session
  sessionId: string | null
  setSessionId: (id: string) => void

  // Language
  language: string
  setLanguage: (lang: string) => void

  // Calibration
  calibration: CalibrationData | null
  setCalibration: (data: CalibrationData) => void

  // Capture
  videoBlob: Blob | null
  setVideoBlob: (blob: Blob) => void
  captureProgress: number
  setCaptureProgress: (progress: number) => void

  // Processing
  processingProgress: number
  setProcessingProgress: (progress: number) => void
  processingMessage: string
  setProcessingMessage: (message: string) => void

  // Results
  measurements: Measurement[]
  setMeasurements: (measurements: Measurement[]) => void
  meshUrl: string | null
  setMeshUrl: (url: string) => void

  // Voice
  voiceEnabled: boolean
  setVoiceEnabled: (enabled: boolean) => void
  voiceSpeed: number
  setVoiceSpeed: (speed: number) => void
  lastVoicePrompt: string
  setLastVoicePrompt: (prompt: string) => void

  // Errors
  error: string | null
  setError: (error: string | null) => void
}

const initialState = {
  currentStep: 'welcome' as ScanStep,
  steps: ['welcome', 'consent', 'setup', 'calibrate', 'capture', 'processing', 'results'] as ScanStep[],
  sessionId: null,
  language: 'en',
  calibration: null,
  videoBlob: null,
  captureProgress: 0,
  processingProgress: 0,
  processingMessage: '',
  measurements: [],
  meshUrl: null,
  voiceEnabled: true,
  voiceSpeed: 1.0,
  lastVoicePrompt: '',
  error: null,
}

export const useScanStore = create<ScanState>()(
  persist(
    (set, get) => ({
      ...initialState,

      setStep: (step) => set({ currentStep: step }),

      nextStep: () => {
        const { currentStep, steps } = get()
        const currentIndex = steps.indexOf(currentStep)
        if (currentIndex < steps.length - 1) {
          set({ currentStep: steps[currentIndex + 1] })
        }
      },

      previousStep: () => {
        const { currentStep, steps } = get()
        const currentIndex = steps.indexOf(currentStep)
        if (currentIndex > 0) {
          set({ currentStep: steps[currentIndex - 1] })
        }
      },

      reset: () => set({ ...initialState, steps: get().steps }),

      setSessionId: (id) => set({ sessionId: id }),
      setLanguage: (lang) => set({ language: lang }),
      setCalibration: (data) => set({ calibration: data }),
      setVideoBlob: (blob) => set({ videoBlob: blob }),
      setCaptureProgress: (progress) => set({ captureProgress: progress }),
      setProcessingProgress: (progress) => set({ processingProgress: progress }),
      setProcessingMessage: (message) => set({ processingMessage: message }),
      setMeasurements: (measurements) => set({ measurements }),
      setMeshUrl: (url) => set({ meshUrl: url }),
      setVoiceEnabled: (enabled) => set({ voiceEnabled: enabled }),
      setVoiceSpeed: (speed) => set({ voiceSpeed: speed }),
      setLastVoicePrompt: (prompt) => set({ lastVoicePrompt: prompt }),
      setError: (error) => set({ error }),
    }),
    {
      name: 'eyeson-scan-storage',
      partialize: (state) => ({
        language: state.language,
        voiceEnabled: state.voiceEnabled,
        voiceSpeed: state.voiceSpeed,
      }),
    }
  )
)
