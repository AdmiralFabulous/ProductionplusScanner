import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

export interface Session {
  session_id: string
  status: string
  scan_mode: 'video' | 'dual_image'
  language: string
  websocket_url: string
  expires_at: string
  created_at: string
}

export interface CalibrationData {
  scale_factor: number
  confidence: number
  marker_corners?: number[][]
  height_estimate_cm?: number
}

/**
 * Create a new scan session
 */
export async function createSession(
  language: string = 'en',
  scanMode: 'video' | 'dual_image' = 'video'
): Promise<Session> {
  const response = await axios.post(`${API_BASE}/sessions`, {
    language,
    scan_mode: scanMode,
  })
  return response.data
}

/**
 * Get session details
 */
export async function getSession(sessionId: string): Promise<Session> {
  const response = await axios.get(`${API_BASE}/sessions/${sessionId}`)
  return response.data
}

/**
 * Submit calibration image
 */
export async function calibrateSession(
  sessionId: string,
  imageFile: File,
  heightCm?: number
): Promise<{
  session_id: string
  calibration: CalibrationData
  status: string
  message: string
}> {
  const formData = new FormData()
  formData.append('marker_image', imageFile)
  if (heightCm) {
    formData.append('height_cm', heightCm.toString())
  }

  const response = await axios.post(
    `${API_BASE}/sessions/${sessionId}/calibrate`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}

/**
 * Upload scan video
 */
export async function uploadVideo(
  sessionId: string,
  videoBlob: Blob
): Promise<{
  session_id: string
  status: string
  message: string
  estimated_seconds: number
}> {
  const formData = new FormData()
  formData.append('video', videoBlob, 'scan.mp4')

  const response = await axios.post(
    `${API_BASE}/sessions/${sessionId}/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )
  return response.data
}

/**
 * Get processing progress
 */
export async function getProgress(sessionId: string): Promise<{
  session_id: string
  status: string
  progress_percent: number
  estimated_completion: string | null
  current_stage: string
}> {
  const response = await axios.get(`${API_BASE}/sessions/${sessionId}/progress`)
  return response.data
}

/**
 * Cancel session
 */
export async function cancelSession(sessionId: string): Promise<void> {
  await axios.post(`${API_BASE}/sessions/${sessionId}/cancel`)
}
