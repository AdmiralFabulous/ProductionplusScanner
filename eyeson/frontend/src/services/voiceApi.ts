import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

/**
 * Speak a predefined voice prompt
 */
export async function speakPrompt(
  language: string,
  promptId: string,
  speed: number = 1.0
): Promise<Blob> {
  const response = await axios.post(
    `${API_BASE}/voice/prompts/${language}/${promptId}/speak`,
    null,
    {
      params: { speed },
      responseType: 'blob',
    }
  )
  return response.data
}

/**
 * Synthesize custom text
 */
export async function synthesizeText(
  text: string,
  language: string = 'en',
  speed: number = 1.0
): Promise<Blob> {
  const response = await axios.post(
    `${API_BASE}/voice/synthesize`,
    { text, language, speed },
    { responseType: 'blob' }
  )
  return response.data
}

/**
 * Get available voices
 */
export async function getVoices(): Promise<{
  primary: Array<{ id: string; name: string; lang: string }>
  fallback: Array<{ id: string; name: string; lang: string }>
}> {
  const response = await axios.get(`${API_BASE}/voice/voices`)
  return response.data.voices
}

/**
 * Get voice prompts for a language
 */
export async function getVoicePrompts(language: string): Promise<{
  language: string
  prompts: Record<string, string>
}> {
  const response = await axios.get(`${API_BASE}/voice/prompts/${language}`)
  return response.data
}
