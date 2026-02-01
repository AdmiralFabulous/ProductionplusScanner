import { useEffect, useState } from 'react'
import { useScanStore } from '../store/scanStore'
import { 
  submitOrder, 
  getOrderStatus, 
  downloadPLT, 
  downloadPDS, 
  downloadDXF,
  pollForFiles 
} from '../services/patternFactoryApi'
import { transformToPatternFactory, calculateSizeCode } from '../utils/measurementMapping'
import { Ruler, Download, RotateCcw, Share2, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react'

// INTEGRATION NOTE (ref: SUIT_AI_Master_Operations_Manual_v6_7_1.md):
// This screen submits measurements to the Pattern Factory and polls for 
// generated files (PLT, PDS, DXF) following the 27-state order state machine.

export default function ResultsScreen() {
  const [showConfidences, setShowConfidences] = useState(false)
  const [orderId, setOrderId] = useState<string | null>(null)
  const [orderStatus, setOrderStatus] = useState<string>('idle')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [filesAvailable, setFilesAvailable] = useState({ plt: false, pds: false, dxf: false })
  const [error, setError] = useState<string | null>(null)
  
  const { 
    measurements, 
    setMeasurements, 
    setStep, 
    reset,
    calibration,
    sessionId,
  } = useScanStore()

  // Submit order to Pattern Factory
  useEffect(() => {
    if (measurements.length === 0 || orderId) return

    const submitToPatternFactory = async () => {
      setIsSubmitting(true)
      setError(null)

      try {
        // Transform EYESON measurements to Pattern Factory format
        // ref: ops manual Section 13 - Measurement JSON Schema
        const pfMeasurements = transformToPatternFactory(measurements)

        // Submit order
        // ref: ops manual Section 1.2 - Order State Machine: S02 → S03
        const order = await submitOrder({
          customer_id: sessionId || 'anonymous',
          garment_type: 'jacket',  // Could be made selectable
          fit_type: 'regular',
          priority: 'normal',
          measurements: pfMeasurements,
          scan_metadata: {
            device_type: 'photogrammetry',
            vertex_count: 6890,  // SMPL mesh vertices
            capture_timestamp: new Date().toISOString(),
            confidence: measurements.reduce((acc, m) => acc + m.confidence, 0) / measurements.length,
          },
        })

        setOrderId(order.order_id)
        setOrderStatus(order.status)

        // Poll for file generation
        // ref: ops manual Section 2.8 - Async processing pattern
        setIsGenerating(true)
        await pollForFiles(
          order.order_id,
          (status) => {
            setOrderStatus(status.status)
            setFilesAvailable(status.files_available)
          },
          2000  // Poll every 2 seconds
        )

      } catch (err) {
        console.error('Order submission failed:', err)
        setError('Failed to submit order to Pattern Factory. Please try again.')
      } finally {
        setIsSubmitting(false)
        setIsGenerating(false)
      }
    }

    submitToPatternFactory()
  }, [measurements, orderId, sessionId])

  // Handle file downloads
  const handleDownload = async (type: 'plt' | 'pds' | 'dxf') => {
    if (!orderId) return

    try {
      let blob: Blob
      let filename: string

      switch (type) {
        case 'plt':
          // ref: ops manual Section 3 - Cutter file format (HPGL)
          blob = await downloadPLT(orderId)
          filename = `${orderId}.plt`
          break
        case 'pds':
          blob = await downloadPDS(orderId)
          filename = `${orderId}.pds`
          break
        case 'dxf':
          // ref: ops manual Section 6 - DXF Output Specification
          blob = await downloadDXF(orderId)
          filename = `${orderId}.dxf`
          break
      }

      // Trigger download
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

    } catch (err) {
      console.error('Download failed:', err)
      setError(`Failed to download ${type.toUpperCase()} file`)
    }
  }

  const handleNewScan = () => {
    reset()
    setStep('welcome')
  }

  // Calculate overall confidence
  const overallConfidence = measurements.length > 0
    ? measurements.reduce((acc, m) => acc + m.confidence, 0) / measurements.length
    : 0

  // Calculate size from chest measurement
  const chestMeasurement = measurements.find(m => 
    m.name.toLowerCase().includes('chest')
  )
  const sizeInfo = chestMeasurement 
    ? calculateSizeCode(chestMeasurement.value)
    : { code: 'L', name: 'Large' }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-eyeson-surface border-b border-slate-700 p-4 safe-area-top">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Your Measurements</h1>
            <p className="text-sm text-slate-400">
              {measurements.length} measurements captured
            </p>
          </div>
          <div className="text-right">
            <div className="flex items-center gap-1 text-eyeson-accent">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">
                {Math.round(overallConfidence * 100)}% confidence
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Size: {sizeInfo.code} ({sizeInfo.name})
            </p>
          </div>
        </div>
      </div>

      {/* Order Status */}
      {(isSubmitting || isGenerating) && (
        <div className="bg-primary-500/20 border border-primary-500/30 p-4 m-4 rounded-lg">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-primary-400 animate-spin" />
            <div>
              <p className="text-white font-medium">
                {isSubmitting ? 'Submitting to Pattern Factory...' : 'Generating pattern files...'}
              </p>
              <p className="text-sm text-slate-400">
                Order: {orderId || 'Creating...'} • Status: {orderStatus}
              </p>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/20 border border-red-500/30 p-4 m-4 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-red-200 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Measurements List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid gap-3">
          {measurements.map((measurement, index) => (
            <MeasurementCard
              key={index}
              measurement={measurement}
              showConfidence={showConfidences}
            />
          ))}
        </div>

        {/* Pattern Files Section */}
        {filesAvailable.plt && (
          <div className="mt-6 bg-eyeson-surface rounded-xl p-4 border border-slate-700">
            <h3 className="font-semibold text-white mb-3">Pattern Files</h3>
            <div className="grid grid-cols-3 gap-2">
              <FileDownloadButton
                type="PLT"
                description="Cutter File"
                available={filesAvailable.plt}
                onClick={() => handleDownload('plt')}
              />
              <FileDownloadButton
                type="PDS"
                description="Optitex Pattern"
                available={filesAvailable.pds}
                onClick={() => handleDownload('pds')}
              />
              <FileDownloadButton
                type="DXF"
                description="CAD Format"
                available={filesAvailable.dxf}
                onClick={() => handleDownload('dxf')}
              />
            </div>
          </div>
        )}

        {/* 3D Preview Placeholder */}
        <div className="mt-6 bg-eyeson-surface rounded-xl p-4 border border-slate-700">
          <h3 className="font-semibold text-white mb-3">3D Body Model</h3>
          <div className="aspect-square bg-slate-800 rounded-lg flex items-center justify-center">
            <div className="text-center">
              <div className="w-32 h-32 mx-auto mb-2 border-2 border-dashed border-slate-600 rounded-lg flex items-center justify-center">
                <Ruler className="w-12 h-12 text-slate-500" />
              </div>
              <p className="text-sm text-slate-400">3D viewer coming soon</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="bg-eyeson-surface border-t border-slate-700 p-4 safe-area-bottom">
        <div className="flex items-center justify-between mb-4">
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={showConfidences}
              onChange={(e) => setShowConfidences(e.target.checked)}
              className="rounded border-slate-600 bg-slate-800 text-primary-500"
            />
            Show confidence scores
          </label>
        </div>

        <button
          onClick={handleNewScan}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          New Scan
        </button>
      </div>
    </div>
  )
}

function MeasurementCard({
  measurement,
  showConfidence,
}: {
  measurement: {
    name: string
    value: number
    unit: string
    confidence: number
    grade: 'P0' | 'P1'
  }
  showConfidence: boolean
}) {
  const confidenceColor = measurement.confidence >= 0.9 
    ? 'bg-green-500' 
    : measurement.confidence >= 0.75 
      ? 'bg-yellow-500' 
      : 'bg-red-500'

  return (
    <div className="bg-eyeson-surface rounded-xl p-4 border border-slate-700 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full ${confidenceColor}`} />
        <div>
          <h3 className="font-medium text-white">{measurement.name}</h3>
          {showConfidence && (
            <p className="text-xs text-slate-400">
              Confidence: {Math.round(measurement.confidence * 100)}%
              {' '}• {measurement.grade}
            </p>
          )}
        </div>
      </div>
      <div className="text-right">
        <p className="text-lg font-semibold text-white">
          {measurement.value.toFixed(1)}
          <span className="text-sm text-slate-400 ml-1">{measurement.unit}</span>
        </p>
      </div>
    </div>
  )
}

function FileDownloadButton({
  type,
  description,
  available,
  onClick,
}: {
  type: string
  description: string
  available: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={!available}
      className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg p-3 text-center transition-colors"
    >
      <Download className="w-5 h-5 text-primary-400 mx-auto mb-1" />
      <p className="text-xs font-medium text-white">{type}</p>
      <p className="text-xs text-slate-500">{description}</p>
    </button>
  )
}
