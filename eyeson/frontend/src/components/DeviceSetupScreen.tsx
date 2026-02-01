import { useState, useEffect } from 'react'
import { useScanStore } from '../store/scanStore'
import { Smartphone, Move, AlertCircle, Check } from 'lucide-react'

export default function DeviceSetupScreen() {
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('portrait')
  const [distance, setDistance] = useState(6)
  const { setStep, nextStep, previousStep } = useScanStore()

  // Detect orientation
  useEffect(() => {
    const handleOrientation = () => {
      const isLandscape = window.innerWidth > window.innerHeight
      setOrientation(isLandscape ? 'landscape' : 'portrait')
    }

    handleOrientation()
    window.addEventListener('resize', handleOrientation)
    return () => window.removeEventListener('resize', handleOrientation)
  }, [])

  return (
    <div className="h-full flex flex-col px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white text-center">
          Device Setup
        </h1>
        <p className="text-slate-400 text-center">
          Position your device correctly
        </p>
      </div>

      {/* Orientation Warning */}
      {orientation === 'landscape' && (
        <div className="bg-eyeson-warning/20 border border-eyeson-warning/30 rounded-xl p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-eyeson-warning flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-eyeson-warning">Rotate Your Device</h3>
            <p className="text-sm text-slate-300">
              Please rotate your phone to portrait mode for the best scanning experience.
            </p>
          </div>
        </div>
      )}

      {/* Setup Instructions */}
      <div className="space-y-4 mb-6">
        <SetupStep
          number={1}
          icon={<Smartphone className="w-5 h-5" />}
          title="Place Against Wall"
          description="Lean your phone against a wall or place on a stable surface"
        />
        <SetupStep
          number={2}
          icon={<Move className="w-5 h-5" />}
          title={`Stand ${distance} Feet Back`}
          description="Make sure your full body is visible in the camera frame"
        />
        <SetupStep
          number={3}
          icon={<Check className="w-5 h-5" />}
          title="Ensure Good Lighting"
          description="Face a light source and avoid strong shadows"
        />
      </div>

      {/* Distance Slider */}
      <div className="bg-eyeson-surface rounded-xl p-4 border border-slate-700 mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-slate-400">Distance</span>
          <span className="text-sm font-semibold text-primary-400">
            {distance} ft
          </span>
        </div>
        <input
          type="range"
          min="4"
          max="10"
          step="0.5"
          value={distance}
          onChange={(e) => setDistance(parseFloat(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          <span>4 ft</span>
          <span>10 ft</span>
        </div>
      </div>

      {/* Visual Guide */}
      <div className="bg-eyeson-surface rounded-xl border border-slate-700 p-6 mb-6 flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-32 h-48 mx-auto mb-4 border-4 border-slate-600 rounded-2xl flex items-center justify-center bg-slate-800">
            <Smartphone className="w-12 h-12 text-slate-500" />
          </div>
          <p className="text-sm text-slate-400">Phone placement example</p>
        </div>
      </div>

      {/* Buttons */}
      <div className="space-y-3">
        <button
          onClick={nextStep}
          disabled={orientation === 'landscape'}
          className="btn-primary w-full disabled:opacity-50"
        >
          I'm Ready
        </button>
        <button
          onClick={previousStep}
          className="btn-secondary w-full"
        >
          Go Back
        </button>
      </div>
    </div>
  )
}

function SetupStep({
  number,
  icon,
  title,
  description,
}: {
  number: number
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center text-white font-semibold">
        {number}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-primary-400">{icon}</span>
          <h3 className="font-semibold text-white">{title}</h3>
        </div>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
    </div>
  )
}
