import { useState } from 'react'
import { useScanStore } from '../store/scanStore'
import { createSession } from '../services/sessionApi'
import { Camera, Clock, Shield, Sparkles } from 'lucide-react'

export default function WelcomeScreen() {
  const [isLoading, setIsLoading] = useState(false)
  const { setStep, setSessionId, setLanguage, language } = useScanStore()

  const handleStart = async () => {
    setIsLoading(true)
    try {
      const session = await createSession(language)
      setSessionId(session.session_id)
      setStep('consent')
    } catch (error) {
      console.error('Failed to create session:', error)
      // For demo, continue anyway
      setStep('consent')
    } finally {
      setIsLoading(false)
    }
  }

  const languages = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'fr', name: 'Français' },
    { code: 'de', name: 'Deutsch' },
    { code: 'zh', name: '中文' },
  ]

  return (
    <div className="h-full flex flex-col items-center justify-center px-6 py-8">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="w-24 h-24 mx-auto mb-4 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl flex items-center justify-center shadow-lg">
          <Camera className="w-12 h-12 text-white" />
        </div>
        <h1 className="text-3xl font-bold text-white mb-2">EYESON</h1>
        <p className="text-slate-400">BodyScan</p>
      </div>

      {/* Tagline */}
      <h2 className="text-2xl font-semibold text-white text-center mb-6">
        Professional measurements
        <br />
        in 90 seconds
      </h2>

      {/* Features */}
      <div className="grid grid-cols-2 gap-4 w-full max-w-sm mb-8">
        <FeatureCard
          icon={<Clock className="w-5 h-5" />}
          title="90 Seconds"
          description="Quick & easy"
        />
        <FeatureCard
          icon={<Shield className="w-5 h-5" />}
          title="Secure"
          description="Privacy first"
        />
        <FeatureCard
          icon={<Sparkles className="w-5 h-5" />}
          title="1cm Accuracy"
          description="Professional grade"
        />
        <FeatureCard
          icon={<Camera className="w-5 h-5" />}
          title="No App"
          description="Browser only"
        />
      </div>

      {/* Language Selector */}
      <div className="mb-6">
        <label className="block text-sm text-slate-400 mb-2 text-center">
          Select Language
        </label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary-500"
        >
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      {/* Start Button */}
      <button
        onClick={handleStart}
        disabled={isLoading}
        className="btn-primary w-full max-w-sm flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Starting...
          </>
        ) : (
          'Start Scan'
        )}
      </button>

      {/* Footer */}
      <p className="mt-6 text-sm text-slate-500 text-center">
        Works on any device • No installation required
      </p>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="bg-eyeson-surface rounded-xl p-4 border border-slate-700 text-center">
      <div className="text-primary-400 mb-2 flex justify-center">{icon}</div>
      <h3 className="font-semibold text-white text-sm">{title}</h3>
      <p className="text-xs text-slate-400">{description}</p>
    </div>
  )
}
