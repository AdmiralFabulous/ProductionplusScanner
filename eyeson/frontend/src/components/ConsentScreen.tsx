import { useState } from 'react'
import { useScanStore } from '../store/scanStore'
import { Shield, Clock, Trash2, Lock } from 'lucide-react'

export default function ConsentScreen() {
  const [accepted, setAccepted] = useState(false)
  const { setStep, nextStep } = useScanStore()

  const handleContinue = () => {
    if (accepted) {
      nextStep()
    }
  }

  return (
    <div className="h-full flex flex-col px-6 py-8 overflow-y-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="w-16 h-16 mx-auto mb-4 bg-green-500/20 rounded-full flex items-center justify-center">
          <Shield className="w-8 h-8 text-green-400" />
        </div>
        <h1 className="text-2xl font-bold text-white text-center">
          Your Privacy Matters
        </h1>
      </div>

      {/* Privacy Points */}
      <div className="space-y-4 mb-6">
        <PrivacyPoint
          icon={<Clock className="w-5 h-5" />}
          title="24-Hour Retention"
          description="Your scan video is automatically deleted within 24 hours. We only keep your measurements."
        />
        <PrivacyPoint
          icon={<Lock className="w-5 h-5" />}
          title="Secure Processing"
          description="All data is encrypted in transit and at rest using industry-standard AES-256 encryption."
        />
        <PrivacyPoint
          icon={<Trash2 className="w-5 h-5" />}
          title="Full Control"
          description="You can request immediate deletion of all your data at any time from your account settings."
        />
      </div>

      {/* Data Usage */}
      <div className="bg-eyeson-surface rounded-xl p-4 border border-slate-700 mb-6">
        <h3 className="font-semibold text-white mb-3">What we collect:</h3>
        <ul className="space-y-2 text-sm text-slate-300">
          <li className="flex items-start gap-2">
            <span className="text-green-400">✓</span>
            Body measurements (28 points)
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-400">✓</span>
            3D body mesh (for visualization)
          </li>
          <li className="flex items-start gap-2">
            <span className="text-red-400">✗</span>
            Your scan video (deleted after processing)
          </li>
          <li className="flex items-start gap-2">
            <span className="text-red-400">✗</span>
            Personal identifiers beyond email
          </li>
        </ul>
      </div>

      {/* Consent Checkbox */}
      <label className="flex items-start gap-3 mb-6 cursor-pointer">
        <input
          type="checkbox"
          checked={accepted}
          onChange={(e) => setAccepted(e.target.checked)}
          className="mt-1 w-5 h-5 rounded border-slate-600 bg-slate-800 text-primary-500 focus:ring-primary-500"
        />
        <span className="text-sm text-slate-300">
          I understand and agree to the{' '}
          <a href="#" className="text-primary-400 hover:underline">
            Privacy Policy
          </a>{' '}
          and{' '}
          <a href="#" className="text-primary-400 hover:underline">
            Terms of Service
          </a>
        </span>
      </label>

      {/* Buttons */}
      <div className="mt-auto space-y-3">
        <button
          onClick={handleContinue}
          disabled={!accepted}
          className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue
        </button>
        <button
          onClick={() => setStep('welcome')}
          className="btn-secondary w-full"
        >
          Go Back
        </button>
      </div>
    </div>
  )
}

function PrivacyPoint({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-primary-400">
        {icon}
      </div>
      <div>
        <h3 className="font-semibold text-white">{title}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
    </div>
  )
}
