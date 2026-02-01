import { useEffect, useState } from 'react'
import { useScanStore } from '../store/scanStore'
import { getProgress } from '../services/sessionApi'
import { Cpu, Loader2, CheckCircle } from 'lucide-react'

const PROCESSING_STAGES = [
  { percent: 10, message: 'Extracting frames from video...' },
  { percent: 30, message: 'Detecting body pose...' },
  { percent: 50, message: 'Building 3D model...' },
  { percent: 70, message: 'Extracting measurements...' },
  { percent: 90, message: 'Finalizing results...' },
  { percent: 100, message: 'Complete!' },
]

export default function ProcessingScreen() {
  const [stage, setStage] = useState(0)
  const { setStep, nextStep, sessionId, setProcessingProgress, setProcessingMessage } = useScanStore()

  // Simulate processing progress (in real app, poll API)
  useEffect(() => {
    let currentStage = 0
    
    const interval = setInterval(() => {
      if (currentStage < PROCESSING_STAGES.length - 1) {
        currentStage++
        setStage(currentStage)
        setProcessingProgress(PROCESSING_STAGES[currentStage].percent)
        setProcessingMessage(PROCESSING_STAGES[currentStage].message)
        
        if (currentStage === PROCESSING_STAGES.length - 1) {
          // Processing complete
          setTimeout(() => {
            nextStep()
          }, 1500)
        }
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [nextStep, setProcessingProgress, setProcessingMessage])

  // Poll actual API if session exists
  useEffect(() => {
    if (!sessionId) return

    const pollProgress = async () => {
      try {
        const result = await getProgress(sessionId)
        setProcessingProgress(result.progress_percent)
        setProcessingMessage(result.current_stage)
        
        if (result.status === 'completed') {
          nextStep()
        }
      } catch (err) {
        console.error('Progress poll failed:', err)
      }
    }

    const interval = setInterval(pollProgress, 2000)
    return () => clearInterval(interval)
  }, [sessionId, nextStep, setProcessingProgress, setProcessingMessage])

  const currentStage = PROCESSING_STAGES[stage]
  const progress = currentStage.percent

  return (
    <div className="h-full flex flex-col items-center justify-center px-6">
      {/* Animated Icon */}
      <div className="mb-8 relative">
        <div className="w-32 h-32 bg-primary-500/20 rounded-full flex items-center justify-center">
          <Cpu className="w-16 h-16 text-primary-400 animate-pulse" />
        </div>
        
        {/* Orbiting dots */}
        <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s' }}>
          <div className="w-3 h-3 bg-primary-400 rounded-full absolute top-0 left-1/2 -translate-x-1/2" />
        </div>
        <div className="absolute inset-0 animate-spin" style={{ animationDuration: '4s', animationDirection: 'reverse' }}>
          <div className="w-2 h-2 bg-eyeson-accent rounded-full absolute bottom-4 left-4" />
        </div>
      </div>

      {/* Progress Text */}
      <h2 className="text-2xl font-bold text-white text-center mb-2">
        Processing Your Scan
      </h2>
      <p className="text-slate-400 text-center mb-8">
        {currentStage.message}
      </p>

      {/* Progress Bar */}
      <div className="w-full max-w-md mb-4">
        <div className="flex justify-between text-sm text-slate-400 mb-2">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-eyeson-accent transition-all duration-1000"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Stage Indicators */}
      <div className="flex gap-2 mt-4">
        {PROCESSING_STAGES.map((s, i) => (
          <div
            key={i}
            className={`w-2 h-2 rounded-full transition-all duration-300 ${
              i <= stage ? 'bg-primary-400 w-4' : 'bg-slate-700'
            }`}
          />
        ))}
      </div>

      {/* Estimated Time */}
      <p className="mt-8 text-sm text-slate-500">
        Estimated time: ~20 seconds
      </p>
    </div>
  )
}
