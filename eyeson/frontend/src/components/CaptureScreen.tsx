import { useState, useRef, useEffect, useCallback } from 'react'
import { useScanStore } from '../store/scanStore'
import { uploadVideo } from '../services/sessionApi'
import { Pose } from '@mediapipe/pose'
import { Camera } from '@mediapipe/camera_utils'
import { drawConnectors, drawLandmarks } from '@mediapipe/drawing_utils'
import { 
  Video, 
  StopCircle, 
  RefreshCw,
  Mic,
  MicOff,
  AlertCircle 
} from 'lucide-react'

const CAPTURE_DURATION = 30 // seconds
const FPS = 30

export default function CaptureScreen() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recordedChunksRef = useRef<Blob[]>([])
  const cameraRef = useRef<Camera | null>(null)
  const poseRef = useRef<Pose | null>(null)
  
  const [isCapturing, setIsCapturing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [timeLeft, setTimeLeft] = useState(CAPTURE_DURATION)
  const [poseDetected, setPoseDetected] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [voiceMuted, setVoiceMuted] = useState(false)
  
  const { 
    setStep, 
    nextStep, 
    previousStep, 
    sessionId, 
    setVideoBlob,
    setCaptureProgress 
  } = useScanStore()

  // Initialize MediaPipe Pose
  useEffect(() => {
    const pose = new Pose({
      locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
      }
    })

    pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    })

    pose.onResults((results) => {
      setPoseDetected(results.poseLandmarks != null)
      
      // Draw pose on canvas
      const canvas = canvasRef.current
      const video = videoRef.current
      if (canvas && video && results.poseLandmarks) {
        const ctx = canvas.getContext('2d')
        if (ctx) {
          canvas.width = video.videoWidth
          canvas.height = video.videoHeight
          
          ctx.clearRect(0, 0, canvas.width, canvas.height)
          
          // Draw connectors
          drawConnectors(ctx, results.poseLandmarks, Pose.POSE_CONNECTIONS, {
            color: '#10b981',
            lineWidth: 4
          })
          
          // Draw landmarks
          drawLandmarks(ctx, results.poseLandmarks, {
            color: '#10b981',
            lineWidth: 2,
            radius: 6
          })
        }
      }
    })

    poseRef.current = pose

    return () => {
      pose.close()
    }
  }, [])

  // Start camera and pose detection
  useEffect(() => {
    const video = videoRef.current
    const pose = poseRef.current
    
    if (!video || !pose) return

    const camera = new Camera(video, {
      onFrame: async () => {
        await pose.send({ image: video })
      },
      width: 640,
      height: 480
    })

    camera.start()
    cameraRef.current = camera

    return () => {
      camera.stop()
    }
  }, [])

  // Start recording
  const startCapture = useCallback(async () => {
    try {
      const stream = videoRef.current?.srcObject as MediaStream
      if (!stream) {
        setError('Camera not ready')
        return
      }

      recordedChunksRef.current = []
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp9'
      })

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' })
        setVideoBlob(blob)
        await submitVideo(blob)
      }

      mediaRecorder.start(1000) // Collect 1-second chunks
      mediaRecorderRef.current = mediaRecorder
      
      setIsCapturing(true)
      setTimeLeft(CAPTURE_DURATION)
    } catch (err) {
      console.error('Recording failed:', err)
      setError('Failed to start recording')
    }
  }, [setVideoBlob])

  // Stop recording
  const stopCapture = useCallback(() => {
    mediaRecorderRef.current?.stop()
    setIsCapturing(false)
  }, [])

  // Submit video to API
  const submitVideo = async (blob: Blob) => {
    if (!sessionId) {
      setError('No session found')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      // Convert webm to mp4 if needed (simplified - in production use ffmpeg.wasm)
      await uploadVideo(sessionId, blob)
      nextStep()
    } catch (err) {
      console.error('Upload failed:', err)
      setError('Failed to upload video. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Timer and progress
  useEffect(() => {
    if (!isCapturing) return

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        const newTime = prev - 1
        const newProgress = ((CAPTURE_DURATION - newTime) / CAPTURE_DURATION) * 100
        setProgress(newProgress)
        setCaptureProgress(newProgress)
        
        if (newTime <= 0) {
          stopCapture()
          return 0
        }
        return newTime
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [isCapturing, stopCapture, setCaptureProgress])

  return (
    <div className="h-full flex flex-col">
      {/* Camera Preview */}
      <div className="relative flex-1 bg-black">
        <video
          ref={videoRef}
          playsInline
          className="absolute inset-0 w-full h-full object-cover"
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full"
        />

        {/* Status Bar */}
        <div className="absolute top-0 left-0 right-0 p-4 bg-gradient-to-b from-black/80 to-transparent">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {poseDetected ? (
                <span className="text-eyeson-accent text-sm font-medium flex items-center gap-1">
                  <div className="w-2 h-2 bg-eyeson-accent rounded-full animate-pulse" />
                  Pose detected
                </span>
              ) : (
                <span className="text-eyeson-warning text-sm font-medium flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  No pose detected
                </span>
              )}
            </div>
            
            {isCapturing && (
              <div className="text-white font-mono text-xl">
                {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, '0')}
              </div>
            )}
          </div>
        </div>

        {/* Voice Toggle */}
        <button
          onClick={() => setVoiceMuted(!voiceMuted)}
          className="absolute top-16 right-4 p-2 bg-black/50 rounded-full text-white"
        >
          {voiceMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* Progress Ring */}
        {isCapturing && (
          <div className="absolute bottom-20 left-1/2 -translate-x-1/2">
            <svg className="w-20 h-20 -rotate-90">
              <circle
                cx="40"
                cy="40"
                r="36"
                fill="none"
                stroke="#334155"
                strokeWidth="4"
              />
              <circle
                cx="40"
                cy="40"
                r="36"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="4"
                strokeLinecap="round"
                strokeDasharray={`${progress * 2.26} 226`}
                className="transition-all duration-1000"
              />
            </svg>
          </div>
        )}

        {/* Instructions */}
        <div className="absolute bottom-20 left-0 right-0 text-center px-4">
          <p className="text-white text-lg font-medium">
            {isCapturing 
              ? 'Turn slowly in a circle' 
              : poseDetected 
                ? 'Stand still and tap Start' 
                : 'Position yourself in frame'
            }
          </p>
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

        <div className="flex items-center justify-center gap-4">
          {!isCapturing ? (
            <>
              <button
                onClick={startCapture}
                disabled={!poseDetected || isSubmitting}
                className="btn-primary flex items-center gap-2 disabled:opacity-50"
              >
                <Video className="w-5 h-5" />
                Start Scan
              </button>
              <button
                onClick={previousStep}
                className="btn-secondary flex items-center gap-2"
              >
                <RefreshCw className="w-5 h-5" />
                Back
              </button>
            </>
          ) : (
            <button
              onClick={stopCapture}
              className="btn-primary bg-red-600 hover:bg-red-700 flex items-center gap-2"
            >
              <StopCircle className="w-5 h-5" />
              Stop ({timeLeft}s)
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
