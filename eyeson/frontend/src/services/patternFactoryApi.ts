/**
 * EYESON - SameDaySuits Pattern Factory Integration
 * 
 * INTEGRATION NOTES (ref: SUIT_AI_Master_Operations_Manual_v6_7_1.md):
 * - Base URL: Pattern Factory API (production backend)
 * - Auth: JWT tokens (1-hour expiry, ref: Section 2.5 Security Layer)
 * - Order ID Format: SDS-YYYYMMDD-NNNN-R (ref: Section 1.2 Order State Machine)
 * - Measurements: 28-point measurement set (ref: Section 13 Database Schema)
 * - State Machine: 27 states from DRAFT → PATTERN_CUT (ref: Section 1.2)
 */

import axios, { AxiosInstance, AxiosError } from 'axios'

// Pattern Factory API Configuration
// ref: ops manual Section 2.5 - API endpoints
const API_BASE = import.meta.env.VITE_PATTERN_FACTORY_URL || 'http://localhost:8000'
const API_VERSION = '/api/v1'

// JWT Token Management
// ref: ops manual Section 2.5 - JWT authentication with 1-hour expiry
let accessToken: string | null = localStorage.getItem('access_token')
let refreshToken: string | null = localStorage.getItem('refresh_token')

/**
 * Axios instance with JWT auth interceptor
 * ref: ops manual Section 2.5 Security Layer
 */
const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE}${API_VERSION}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && originalRequest) {
      // Token expired - attempt refresh
      // ref: ops manual Section 2.5 - JWT refresh flow
      try {
        const response = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        
        accessToken = response.data.access_token
        localStorage.setItem('access_token', accessToken!)
        
        originalRequest.headers.Authorization = `Bearer ${accessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed - logout
        logout()
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)

// ============================================================================
// AUTHENTICATION
// ============================================================================

/**
 * Login with credentials
 * ref: ops manual Section 2.5 - JWT authentication
 */
export async function login(email: string, password: string): Promise<{
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}> {
  const response = await axios.post(`${API_BASE}/auth/login`, {
    email,
    password,
  })
  
  accessToken = response.data.access_token
  refreshToken = response.data.refresh_token
  
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('refresh_token', refreshToken)
  
  return response.data
}

/**
 * Logout and clear tokens
 */
export function logout(): void {
  accessToken = null
  refreshToken = null
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

/**
 * Get current auth status
 */
export function isAuthenticated(): boolean {
  return !!accessToken
}

// ============================================================================
// ORDER MANAGEMENT
// ============================================================================

/**
 * 28-Measurement Data Structure
 * ref: ops manual Section 13 Database Schema - Core measurements
 */
export interface Measurements {
  // Primary Measurements (13 core)
  Cg: { value: number; unit: 'cm'; confidence: number }  // Chest Girth
  Wg: { value: number; unit: 'cm'; confidence: number }  // Waist Girth
  Hg: { value: number; unit: 'cm'; confidence: number }  // Hip Girth
  Sh: { value: number; unit: 'cm'; confidence: number }  // Shoulder Width
  Al: { value: number; unit: 'cm'; confidence: number }  // Arm Length
  Bw: { value: number; unit: 'cm'; confidence: number }  // Back Width
  Nc: { value: number; unit: 'cm'; confidence: number }  // Neck Circumference
  Bi: { value: number; unit: 'cm'; confidence: number }  // Bicep Girth
  Wc: { value: number; unit: 'cm'; confidence: number }  // Wrist Circumference
  Il: { value: number; unit: 'cm'; confidence: number }  // Inseam Length
  Th: { value: number; unit: 'cm'; confidence: number }  // Thigh Girth
  Kn: { value: number; unit: 'cm'; confidence: number }  // Knee Girth
  Ca: { value: number; unit: 'cm'; confidence: number }  // Calf Girth
  
  // Secondary Measurements (15 derived)
  front_waist_length?: { value: number; unit: 'cm' }
  back_waist_length?: { value: number; unit: 'cm' }
  scye_depth?: { value: number; unit: 'cm' }
  half_back?: { value: number; unit: 'cm' }
  crotch_depth?: { value: number; unit: 'cm' }
  // ... additional 11 measurements as needed
}

/**
 * Order submission payload
 * ref: ops manual Section 1.2 Order State Machine - S03 SCAN_RECEIVED
 */
export interface OrderRequest {
  order_id?: string           // Auto-generated if not provided: SDS-YYYYMMDD-NNNN-R
  customer_id: string
  garment_type: 'tee' | 'jacket' | 'trousers' | 'cargo'
  fit_type: 'slim' | 'regular' | 'classic'
  priority: 'rush' | 'high' | 'normal' | 'low'
  measurements: Measurements
  scan_metadata?: {
    device_type: 'photogrammetry' | 'lidar' | 'structured_light'
    vertex_count: number
    capture_timestamp: string
    confidence: number
  }
}

/**
 * Order response
 * ref: ops manual Section 1.2 - Order state tracking
 */
export interface OrderResponse {
  order_id: string
  status: 'draft' | 'paid' | 'scan_received' | 'processing' | 
          'pattern_ready' | 'cutting' | 'pattern_cut' | 'error'
  customer_id: string
  garment_type: string
  fit_type: string
  measurements: Measurements
  created_at: string
  files_available: {
    plt: boolean
    pds: boolean
    dxf: boolean
  }
}

/**
 * Submit order with measurements
 * ref: ops manual Section 1.2 - Transition: S02 (PAID) → S03 (SCAN_RECEIVED)
 * Endpoint: POST /orders
 */
export async function submitOrder(order: OrderRequest): Promise<OrderResponse> {
  // Transform EYESON measurements to Pattern Factory format
  const payload = {
    ...order,
    status: 'scan_received',  // Auto-set state to trigger processing
  }
  
  const response = await api.post('/orders', payload)
  return response.data
}

/**
 * Get order details
 * ref: ops manual Section 1.2 - Order tracking
 * Endpoint: GET /orders/{id}
 */
export async function getOrder(orderId: string): Promise<OrderResponse> {
  const response = await api.get(`/orders/${orderId}`)
  return response.data
}

/**
 * Get order status
 * ref: ops manual Section 1.2 - State machine polling
 * Endpoint: GET /orders/{id}/status
 */
export async function getOrderStatus(orderId: string): Promise<{
  order_id: string
  status: string
  files_available: {
    plt: boolean
    pds: boolean
    dxf: boolean
  }
  processing_time_ms: number
  fabric_length_cm: number
  fabric_utilization: number
}> {
  const response = await api.get(`/orders/${orderId}/status`)
  return response.data
}

/**
 * Poll for file availability
 * ref: ops manual Section 2.8 - Async processing pattern
 */
export async function pollForFiles(
  orderId: string,
  onProgress?: (status: any) => void,
  intervalMs: number = 2000
): Promise<void> {
  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      try {
        const status = await getOrderStatus(orderId)
        onProgress?.(status)
        
        if (status.files_available.plt) {
          resolve()
        } else if (status.status === 'error') {
          reject(new Error('Order processing failed'))
        } else {
          setTimeout(checkStatus, intervalMs)
        }
      } catch (error) {
        reject(error)
      }
    }
    
    checkStatus()
  })
}

// ============================================================================
// FILE DOWNLOADS
// ============================================================================

/**
 * Download PLT cutter file
 * ref: ops manual Section 3 - Cutter file format (HPGL)
 * Endpoint: GET /orders/{id}/plt
 */
export async function downloadPLT(orderId: string): Promise<Blob> {
  const response = await api.get(`/orders/${orderId}/plt`, {
    responseType: 'blob',
  })
  return response.data
}

/**
 * Download PDS Optitex file
 * ref: ops manual Section 2.8 - Pattern Factory SOPs
 * Endpoint: GET /orders/{id}/pds
 */
export async function downloadPDS(orderId: string): Promise<Blob> {
  const response = await api.get(`/orders/${orderId}/pds`, {
    responseType: 'blob',
  })
  return response.data
}

/**
 * Download DXF CAD file
 * ref: ops manual Section 6 - DXF Output Specification (Holy Grail)
 * Endpoint: GET /orders/{id}/dxf
 */
export async function downloadDXF(orderId: string): Promise<Blob> {
  const response = await api.get(`/orders/${orderId}/dxf`, {
    responseType: 'blob',
  })
  return response.data
}

/**
 * List all order files
 * Endpoint: GET /orders/{id}/files
 */
export async function listOrderFiles(orderId: string): Promise<{
  order_id: string
  files: Array<{
    filename: string
    type: 'plt' | 'pds' | 'dxf' | 'json' | 'log'
    size_bytes: number
    created_at: string
  }>
}> {
  const response = await api.get(`/orders/${orderId}/files`)
  return response.data
}

// ============================================================================
// QUEUE MANAGEMENT
// ============================================================================

/**
 * Get queue status
 * ref: ops manual Section 2.8 - Queue management
 * Endpoint: GET /queue/status
 */
export async function getQueueStatus(): Promise<{
  pending_jobs: number
  processing_jobs: number
  completed_jobs: number
  failed_jobs: number
  average_wait_time_ms: number
}> {
  const response = await api.get('/queue/status')
  return response.data
}

// ============================================================================
// HEALTH & MONITORING
// ============================================================================

/**
 * Health check
 * ref: ops manual Section 2.7 - Health monitoring
 * Endpoint: GET /api/health
 */
export async function healthCheck(): Promise<{
  status: string
  version: string
  timestamp: string
}> {
  const response = await axios.get(`${API_BASE}/api/health`)
  return response.data
}

/**
 * Production metrics
 * ref: ops manual Section 2.7 - Observability
 * Endpoint: GET /api/metrics
 */
export async function getMetrics(): Promise<string> {
  const response = await api.get('/api/metrics')
  return response.data
}

// ============================================================================
// WEBSOCKET (Real-time Updates)
// ============================================================================

/**
 * WebSocket connection for real-time updates
 * ref: ops manual Section 2.6 - WebSocket for real-time status
 */
export function createWebSocketConnection(
  orderId: string,
  onMessage: (data: any) => void
): WebSocket {
  const wsUrl = `${API_BASE.replace('http', 'ws')}/ws?token=${accessToken}&order_id=${orderId}`
  const ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('WebSocket connected for order:', orderId)
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onMessage(data)
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
  
  ws.onclose = () => {
    console.log('WebSocket disconnected')
  }
  
  return ws
}
