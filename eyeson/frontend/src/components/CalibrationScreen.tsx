import { useState, useRef, useEffect, useCallback } from 'react'
import { useScanStore } from '../store/scanStore'
import { calibrateSession } from '../services/sessionApi'
import { Camera, Check, AlertCircle } from 'lucide-react'

export default function CalibrationScreen() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [markerDetected, setMarkerDetected] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { setStep, nextStep, previousStep, sessionId, setCalibration } = useScanStore()

  // Start camera
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: 1280, height: 720 }
        })
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          setIsStreaming(true)
        }
      } catch (err) {
        console.error('Camera access failed:', err)
        setError('Camera access denied. Please allow camera permissions.')
      }
    }

    startCamera()

    return () => {
      const stream = videoRef.current?.srcObject as MediaStream
      stream?.getTracks().forEach(track => track.stop())
    }
  }, [])

  // Simulate ArUco marker detection (in real app, use OpenCV.js)
  useEffect(() => {
    if (!isStreaming) return

    const interval = setInterval(() => {
      // Mock detection - in real app, process video frame with OpenCV
      const detected = Math.random() > 0.3 // 70% chance for demo
      setMarkerDetected(detected)
    }, 1000)

    return () => clearInterval(interval)
  }, [isStreaming])

  // Capture and submit calibration
  const handleCalibrate = useCallback(async () => {
    if (!sessionId) {
      setError('No session found. Please start over.')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      // Capture frame from video
      const canvas = document.createElement('canvas')
      canvas.width = 640
      canvas.height = 480
      const ctx = canvas.getContext('2d')
      
      if (videoRef.current && ctx) {
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)
        
        // Convert to blob
        const blob = await new Promise<Blob>((resolve) => {
          canvas.toBlob((b) => resolve(b!), 'image/jpeg', 0.9)
        })
        
        const file = new File([blob], 'calibration.jpg', { type: 'image/jpeg' })
        
        // Submit to API
        const result = await calibrateSession(sessionId, file)
        
        setCalibration({
          scaleFactor: result.calibration.scale_factor,
          confidence: result.calibration.confidence,
          markerDetected: true
        })
        
        nextStep()
      }
    } catch (err) {
      console.error('Calibration failed:', err)
      setError('Calibration failed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }, [sessionId, setCalibration, nextStep])

  return (
    <div className="h-full flex flex-col">
      {/* Camera Preview */}
      <div className="relative flex-1 bg-black">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover"
          style={{ transform: 'scaleX(-1)' }}
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
        />
        
        {/* Marker Detection Overlay */}
        {markerDetected && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="border-4 border-eyeson-accent rounded-lg p-8 animate-pulse">
              <Check className="w-12 h-12 text-eyeson-accent mx-auto" />
              <p className="text-white font-semibold mt-2">Marker Detected!</p>
            </div>
          </div>
        )}

        {/* Instructions Overlay */}
        <div className="absolute top-0 left-0 right-0 p-4 bg-gradient-to-b from-black/80 to-transparent">
          <h2 className="text-white font-semibold text-center">
            Place Calibration Card on Floor
          </h2>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-eyeson-surface border-t border-slate-700 p-6 safe-area-bottom">
        {error && (
          <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-3 mb-4 flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-200">{error}</p>
          </div>
        )}

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Camera className="w-5 h-5 text-primary-400" />
              <span className="text-sm text-slate-300">
                {markerDetected ? 'Ready to calibrate' : 'Looking for marker...'}
              </span>
            </div>
            {markerDetected && (
              <span className="text-eyeson-accent text-sm font-medium">Detected</span>
            )}
          </div>

          <button
            onClick={handleCalibrate}
            disabled={!markerDetected || isSubmitting}
            className="btn-primary w-full disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Calibrating...
              </>
            ) : (
              'Continue'
            )}
          </button>

          <button
            onClick={previousStep}
            className="btn-secondary w-full"
          >
            Go Back
          </button>
        </div>
      </div>
    </div>
  )
}
