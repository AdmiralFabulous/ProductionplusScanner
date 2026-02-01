import { useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { useScanStore } from './store/scanStore'
import WelcomeScreen from './components/WelcomeScreen'
import ConsentScreen from './components/ConsentScreen'
import DeviceSetupScreen from './components/DeviceSetupScreen'
import CalibrationScreen from './components/CalibrationScreen'
import CaptureScreen from './components/CaptureScreen'
import ProcessingScreen from './components/ProcessingScreen'
import ResultsScreen from './components/ResultsScreen'
import VoicePlayer from './components/VoicePlayer'

function App() {
  const navigate = useNavigate()
  const { currentStep, setStep, reset } = useScanStore()

  // Handle navigation based on step
  useEffect(() => {
    const stepRoutes: Record<string, string> = {
      welcome: '/',
      consent: '/consent',
      setup: '/setup',
      calibrate: '/calibrate',
      capture: '/capture',
      processing: '/processing',
      results: '/results',
    }

    const route = stepRoutes[currentStep]
    if (route && window.location.pathname !== route) {
      navigate(route)
    }
  }, [currentStep, navigate])

  return (
    <div className="h-full flex flex-col bg-eyeson-dark">
      {/* Global Voice Player */}
      <VoicePlayer />

      {/* Main Content */}
      <main className="flex-1 relative overflow-hidden">
        <Routes>
          <Route path="/" element={<WelcomeScreen />} />
          <Route path="/consent" element={<ConsentScreen />} />
          <Route path="/setup" element={<DeviceSetupScreen />} />
          <Route path="/calibrate" element={<CalibrationScreen />} />
          <Route path="/capture" element={<CaptureScreen />} />
          <Route path="/processing" element={<ProcessingScreen />} />
          <Route path="/results" element={<ResultsScreen />} />
        </Routes>
      </main>

      {/* Progress Indicator */}
      <StepIndicator />
    </div>
  )
}

function StepIndicator() {
  const { currentStep, steps } = useScanStore()
  const currentIndex = steps.indexOf(currentStep)
  const progress = ((currentIndex + 1) / steps.length) * 100

  return (
    <div className="bg-eyeson-surface border-t border-slate-700 px-4 py-3 safe-area-bottom">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-slate-400">
          Step {currentIndex + 1} of {steps.length}
        </span>
        <span className="text-sm font-medium text-primary-400">
          {Math.round(progress)}%
        </span>
      </div>
      <div className="h-1 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary-500 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}

export default App
