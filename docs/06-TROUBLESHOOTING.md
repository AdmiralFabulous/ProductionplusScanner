# Troubleshooting Guide

**Document Version:** 1.0  
**Last Updated:** 2026-02-01  
**Applicable Systems:** Production Scanner, Pattern Factory, EYESON Backend

---

## Table of Contents

1. [Common Issues Overview](#1-common-issues-overview)
2. [Camera Permission Issues](#2-camera-permission-issues)
3. [API Connection Failures](#3-api-connection-failures)
4. [Measurement Validation Errors](#4-measurement-validation-errors)
5. [File Generation Issues](#5-file-generation-issues)
6. [TTS Issues](#6-tts-issues)
7. [Debug Commands](#7-debug-commands)
8. [Support Contacts and Escalation](#8-support-contacts-and-escalation)

---

## 1. Common Issues Overview

| Issue | Symptoms | Quick Fix | Section |
|-------|----------|-----------|---------|
| Camera Access Denied | Black screen, "Allow camera" prompt appears repeatedly | Check browser permissions, reset site settings | [2.1](#21-browser-camera-access-denied) |
| Pattern Factory Unreachable | "Service unavailable" error, connection timeout | Verify Docker containers are running | [3.1](#31-pattern-factory-unreachable) |
| JWT Token Expired | 401 Unauthorized errors, redirects to login | Refresh token or re-authenticate | [3.2](#32-jwt-token-expired) |
| Confidence Below Threshold | "Low measurement confidence" warning | Adjust lighting, reposition subject | [4.1](#41-confidence-below-threshold) |
| PLT File Not Generated | Download link missing, 404 on PLT endpoint | Check cutter service logs | [5.1](#51-plt-file-not-generated) |
| Kokoro Model Not Loaded | TTS silent, "Model not found" in logs | Download model weights | [6.1](#61-kokoro-model-not-loaded) |
| iOS Safari Black Screen | Camera preview black, no error message | Use HTTPS, check iOS version | [2.3](#23-ios-safari-specific-issues) |
| CORS Errors | Browser console shows CORS policy errors | Verify API origin whitelist | [3.3](#33-cors-errors) |
| Queue Timeout | Pattern generation hangs, no response | Check queue processor status | [5.3](#53-queue-timeout) |
| Audio Not Playing | No sound output, volume icon shows mute | Check audio permissions, browser autoplay | [6.3](#63-audio-not-playing) |

---

## 2. Camera Permission Issues

### 2.1 Browser Camera Access Denied

**Symptoms:**
- Black screen instead of camera preview
- "Allow camera access" prompt appears repeatedly
- Error: `NotAllowedError: Permission denied`

**Resolution Steps:**

1. **Check Browser Permissions:**
   - Chrome: Click lock icon in address bar → Site Settings → Camera → Allow
   - Firefox: Click lock icon → Permissions → Camera → Allow
   - Safari: Preferences → Websites → Camera → Allow

2. **Reset Site Permissions:**
   ```javascript
   // Clear stored permissions in browser console
   navigator.permissions.query({name: 'camera'}).then(result => {
     console.log('Camera permission:', result.state);
   });
   ```

3. **Verify HTTPS:**
   - Camera API requires secure context (HTTPS or localhost)
   - Check URL starts with `https://`

4. **Restart Browser:**
   - Close all browser windows and reopen
   - Try incognito/private mode as test

**Prevention:**
- Implement permission check before camera initialization
- Show user-friendly instructions when permission denied

---

### 2.2 Black Screen During Capture

**Symptoms:**
- Camera permission granted but preview is black
- Green activity light on camera (indicating active stream)
- No error messages in console

**Resolution Steps:**

1. **Check Camera Selection:**
   ```javascript
   // List available cameras
   navigator.mediaDevices.enumerateDevices()
     .then(devices => {
       const cameras = devices.filter(d => d.kind === 'videoinput');
       console.log('Available cameras:', cameras);
     });
   ```

2. **Force Camera Restart:**
   ```javascript
   // Stop and restart video stream
   if (stream) {
     stream.getTracks().forEach(track => track.stop());
   }
   navigator.mediaDevices.getUserMedia({ video: true })
     .then(newStream => {
       videoElement.srcObject = newStream;
     });
   ```

3. **Check for Conflicting Apps:**
   - Close Zoom, Teams, or other apps using camera
   - Check Windows Camera app isn't running

4. **Driver Issues:**
   - Update camera drivers in Device Manager
   - Try external USB camera if available

---

### 2.3 iOS Safari Specific Issues

**Symptoms:**
- Black screen on iPhone/iPad Safari
- Camera works in Chrome but not Safari
- iOS version-specific failures

**Resolution Steps:**

1. **HTTPS Requirement:**
   - iOS strictly requires HTTPS for camera access
   - Self-signed certificates may not work

2. **Check iOS Version:**
   - iOS 14.3+ required for modern camera API
   - Settings → General → About → Software Version

3. **Safari Settings:**
   - Settings → Safari → Camera → Allow
   - Disable "Prevent Cross-Site Tracking" if needed

4. **Viewport Meta Tag:**
   ```html
   <!-- Required for iOS camera -->
   <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
   ```

5. **Camera Selection Constraint:**
   ```javascript
   // Use environment-facing camera on iOS
   const constraints = {
     video: {
       facingMode: { exact: 'environment' } // or 'user' for front
     }
   };
   ```

---

### 2.4 Android Chrome Specific Issues

**Symptoms:**
- Camera preview rotated 90 degrees
- Flash not working
- Poor performance on older devices

**Resolution Steps:**

1. **Rotation Fix:**
   ```javascript
   // Handle device orientation
   screen.orientation.lock('portrait').catch(console.error);
   ```

2. **Camera Constraints:**
   ```javascript
   const constraints = {
     video: {
       facingMode: 'environment',
       width: { ideal: 1920 },
       height: { ideal: 1080 }
     }
   };
   ```

3. **Clear Chrome Cache:**
   - Chrome → Settings → Privacy → Clear Browsing Data
   - Select "Cached images and files"

4. **Hardware Acceleration:**
   - Chrome → Settings → Advanced → System
   - Enable "Use hardware acceleration when available"

---

## 3. API Connection Failures

### 3.1 Pattern Factory Unreachable

**Symptoms:**
- Error: "Pattern Factory service unavailable"
- Connection timeout after 30 seconds
- Docker container status shows `Exited`

**Resolution Steps:**

1. **Check Container Status:**
   ```bash
   docker-compose ps
   ```

2. **Restart Pattern Factory:**
   ```bash
   docker-compose restart pattern-factory
   ```

3. **Check Health Endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "pattern-factory",
     "version": "1.0.0"
   }
   ```

4. **View Logs:**
   ```bash
   docker-compose logs -f pattern-factory
   ```

5. **Check Port Availability:**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   
   # Kill process if needed
   taskkill /PID <PID> /F
   ```

6. **Network Connectivity:**
   ```bash
   # Test from inside container
   docker exec -it pattern-factory ping localhost
   ```

---

### 3.2 JWT Token Expired

**Symptoms:**
- HTTP 401 Unauthorized responses
- Error: "Token has expired"
- Redirected to login page unexpectedly

**Resolution Steps:**

1. **Check Token Expiry:**
   ```javascript
   // Decode JWT payload (base64)
   const payload = JSON.parse(atob(token.split('.')[1]));
   const expiry = new Date(payload.exp * 1000);
   console.log('Token expires:', expiry);
   ```

2. **Refresh Token:**
   ```bash
   curl -X POST http://localhost:8000/auth/refresh \
     -H "Authorization: Bearer <refresh_token>"
   ```

3. **Re-authenticate:**
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "<password>"}'
   ```

4. **Token Configuration:**
   - Check `JWT_EXPIRY_MINUTES` in `.env`
   - Default: 60 minutes
   - Increase for development: 1440 (24 hours)

5. **Implement Auto-Refresh:**
   ```javascript
   // Add interceptor to refresh token before expiry
   axios.interceptors.response.use(
     response => response,
     async error => {
       if (error.response?.status === 401) {
         await refreshToken();
         return axios.request(error.config);
       }
       return Promise.reject(error);
     }
   );
   ```

---

### 3.3 CORS Errors

**Symptoms:**
- Browser console: "CORS policy: No 'Access-Control-Allow-Origin' header"
- Preflight request fails with 403
- API works from curl but not browser

**Resolution Steps:**

1. **Check CORS Configuration:**
   ```bash
   curl -I -X OPTIONS http://localhost:8000/api/measurements \
     -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST"
   ```

2. **Update Allowed Origins:**
   ```python
   # In Pattern Factory config
   CORS_ORIGINS = [
       "http://localhost:3000",
       "https://scanner.production.local",
       "https://scanner.samedaysuits.com"
   ]
   ```

3. **Wildcard (Development Only):**
   ```python
   # config/development.py
   CORS_ORIGINS = ["*"]
   ```

4. **Nginx Proxy Headers:**
   ```nginx
   location / {
       add_header 'Access-Control-Allow-Origin' '*' always;
       add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
       add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
   }
   ```

---

### 3.4 Network Timeout

**Symptoms:**
- Request hangs indefinitely
- Error: "Network timeout"
- Intermittent failures during peak hours

**Resolution Steps:**

1. **Increase Timeout:**
   ```javascript
   axios.defaults.timeout = 60000; // 60 seconds
   ```

2. **Check Network Latency:**
   ```bash
   ping -t pattern-factory.local
   ```

3. **Check Server Load:**
   ```bash
   docker stats pattern-factory
   ```

4. **Implement Retry Logic:**
   ```javascript
   const axiosRetry = require('axios-retry');
   axiosRetry(axios, {
     retries: 3,
     retryDelay: axiosRetry.exponentialDelay,
     retryCondition: (error) => {
       return axiosRetry.isNetworkOrIdempotentRequestError(error) ||
              error.response?.status === 504;
     }
   });
   ```

5. **Check Firewall Rules:**
   ```bash
   # Windows Firewall
   netsh advfirewall firewall show rule name=all | findstr 8000
   ```

---

## 4. Measurement Validation Errors

### 4.1 Confidence Below Threshold

**Symptoms:**
- Warning: "Low measurement confidence (0.45 < 0.70)"
- Measurements flagged as unreliable
- Pattern generation blocked

**Resolution Steps:**

1. **Adjust Confidence Threshold:**
   ```python
   # Temporarily lower threshold for testing
   CONFIDENCE_THRESHOLD = 0.60  # Default: 0.70
   ```

2. **Check Lighting Conditions:**
   - Minimum 500 lux recommended
   - Avoid backlighting
   - Use diffused lighting

3. **Subject Positioning:**
   - Stand 2 meters from camera
   - Ensure full body visible
   - Arms slightly away from body

4. **Camera Quality:**
   - Minimum 1080p resolution
   - Check focus is sharp
   - Clean camera lens

5. **Re-capture:**
   ```javascript
   // Trigger new capture
   measurementService.recapture({
     reason: 'low_confidence',
     previous_confidence: 0.45
   });
   ```

---

### 4.2 Out of Range Values

**Symptoms:**
- Error: "Chest measurement 250cm exceeds maximum (150cm)"
- Negative values in measurements
- Unrealistic proportions detected

**Resolution Steps:**

1. **Check Measurement Ranges:**
   ```python
   MEASUREMENT_RANGES = {
       'chest_girth': (60, 150),    # cm
       'waist_girth': (50, 140),
       'hip_girth': (60, 150),
       'shoulder_width': (30, 70),
       'neck_girth': (30, 55),
       'sleeve_length': (50, 90),
       'inseam': (60, 110)
   }
   ```

2. **Validate Input:**
   ```python
   def validate_measurement(name: str, value: float) -> bool:
       min_val, max_val = MEASUREMENT_RANGES.get(name, (0, 999))
       if not (min_val <= value <= max_val):
           raise ValueError(
               f"{name} ({value}cm) outside valid range "
               f"[{min_val}-{max_val}cm]"
           )
       return True
   ```

3. **Check Units:**
   - Verify measurements are in centimeters
   - Convert if received in inches: `cm = inches * 2.54`

4. **Review Calibration:**
   - Re-run calibration procedure
   - Check reference object size

---

### 4.3 Missing Measurements

**Symptoms:**
- Error: "Required measurement 'bicep_girth' missing"
- Incomplete measurement set
- Pattern generation fails

**Resolution Steps:**

1. **Check Required Measurements:**
   ```python
   REQUIRED_MEASUREMENTS = [
       'chest_girth', 'waist_girth', 'hip_girth',
       'shoulder_width', 'neck_girth', 'sleeve_length',
       'inseam', 'wrist_girth'
   ]
   ```

2. **Check Detection Model:**
   ```bash
   docker-compose logs measurement-service | grep "detection failed"
   ```

3. **Manual Entry:**
   ```json
   {
     "measurements": {
       "chest_girth": 102.5,
       "waist_girth": 88.0,
       "hip_girth": 98.0,
       "bicep_girth": 32.0  // Manually added
     }
   }
   ```

4. **Update Detection Model:**
   - Download latest model weights
   - Restart measurement service

---

### 4.4 Invalid Garment Type

**Symptoms:**
- Error: "Garment type 'tuxedo_shorts' not supported"
- Pattern generation fails at garment selection
- Dropdown shows no options

**Resolution Steps:**

1. **Check Supported Garments:**
   ```python
   SUPPORTED_GARMENTS = [
       'suit_2pc', 'suit_3pc', 'tuxedo_2pc', 'tuxedo_3pc',
       'blazer', 'trousers', 'waistcoat', 'overcoat'
   ]
   ```

2. **Validate Garment Code:**
   ```python
   def validate_garment_type(garment: str) -> str:
       garment = garment.lower().strip()
       if garment not in SUPPORTED_GARMENTS:
           raise ValueError(
               f"Unsupported garment: {garment}. "
               f"Supported: {', '.join(SUPPORTED_GARMENTS)}"
           )
       return garment
   ```

3. **Check Database:**
   ```sql
   SELECT garment_code, garment_name FROM garments WHERE active = 1;
   ```

4. **Update Garment List:**
   ```bash
   # Refresh garment cache
   curl -X POST http://localhost:8000/admin/refresh-garments
   ```

---

## 5. File Generation Issues

### 5.1 PLT File Not Generated

**Symptoms:**
- Download link returns 404
- Pattern status shows "processing" indefinitely
- No PLT files in output directory

**Resolution Steps:**

1. **Check Pattern Status:**
   ```bash
   curl http://localhost:8000/patterns/<order_id>/status
   ```

2. **Verify Output Directory:**
   ```bash
   # Inside container
   docker exec pattern-factory ls -la /app/output/
   
   # Check permissions
   docker exec pattern-factory chmod 777 /app/output/
   ```

3. **Check Disk Space:**
   ```bash
   docker system df
   docker exec pattern-factory df -h
   ```

4. **Review Pattern Logs:**
   ```bash
   docker-compose logs pattern-factory | grep -i "plt\|error\|exception"
   ```

5. **Manual Generation Test:**
   ```bash
   curl -X POST http://localhost:8000/patterns/generate \
     -H "Content-Type: application/json" \
     -d '{
       "order_id": "TEST001",
       "garment_type": "suit_2pc",
       "measurements": {"chest_girth": 102.5}
     }'
   ```

---

### 5.2 PDS Download Fails

**Symptoms:**
- Error: "PDS file not found"
- Download starts but file is corrupted
- PDS format incompatible with Optitex

**Resolution Steps:**

1. **Check PDS Generation:**
   ```bash
   curl http://localhost:8000/patterns/<order_id>/pds
   ```

2. **Verify PDS Format:**
   ```python
   # Validate PDS file header
   def validate_pds(file_path: str) -> bool:
       with open(file_path, 'rb') as f:
           header = f.read(4)
           return header == b'PDS\x00'  # Expected magic bytes
   ```

3. **Check Optitex Version:**
   - PDS format may vary by Optitex version
   - Verify compatibility with O25

4. **Re-export PDS:**
   ```bash
   curl -X POST http://localhost:8000/patterns/<order_id>/export-pds
   ```

---

### 5.3 Queue Timeout

**Symptoms:**
- Pattern generation hangs at "Queued"
- Queue status shows stale jobs
- No worker processing

**Resolution Steps:**

1. **Check Queue Status:**
   ```bash
   curl http://localhost:8000/queue/status
   ```
   Expected response:
   ```json
   {
     "pending": 2,
     "processing": 1,
     "completed": 45,
     "failed": 0,
     "workers": 4
   }
   ```

2. **Restart Queue Worker:**
   ```bash
   docker-compose restart queue-worker
   ```

3. **Clear Stuck Jobs:**
   ```bash
   curl -X POST http://localhost:8000/queue/clear-stuck
   ```

4. **Monitor Queue:**
   ```bash
   # Watch queue in real-time
   watch -n 2 'curl -s http://localhost:8000/queue/status'
   ```

5. **Scale Workers:**
   ```bash
   docker-compose up -d --scale queue-worker=8
   ```

---

### 5.4 Cutter Connection Failed

**Symptoms:**
- Error: "Unable to connect to cutter"
- PLT files queued but not sent
- Cutter status shows offline

**Resolution Steps:**

1. **Check Cutter Status:**
   ```bash
   curl http://localhost:8000/cutter/status
   ```

2. **Verify Network Connection:**
   ```bash
   ping <cutter-ip-address>
   telnet <cutter-ip-address> <port>
   ```

3. **Check Cutter Service:**
   ```bash
   docker-compose restart cutter-service
   ```

4. **Verify Cutter Configuration:**
   ```yaml
   # docker-compose.yml
   cutter-service:
     environment:
       - CUTTER_IP=192.168.1.100
       - CUTTER_PORT=9100
       - CUTTER_PROTOCOL=hpgl
   ```

5. **Test Cutter Connection:**
   ```bash
   curl -X POST http://localhost:8000/cutter/test-connection
   ```

---

## 6. TTS Issues

### 6.1 Kokoro Model Not Loaded

**Symptoms:**
- TTS service returns 503
- Error: "Kokoro model not initialized"
- Fallback to Piper not triggered

**Resolution Steps:**

1. **Check Model Files:**
   ```bash
   docker exec tts-service ls -la /app/models/kokoro/
   ```
   Expected files:
   - `kokoro-v1.0.onnx`
   - `voices.bin`
   - `config.json`

2. **Download Model:**
   ```bash
   docker exec -it tts-service python -c "
   from kokoro import download_model
   download_model('v1.0', '/app/models/kokoro/')
   "
   ```

3. **Verify Model Loading:**
   ```bash
   curl http://localhost:8002/health
   ```
   Expected response:
   ```json
   {
     "status": "healthy",
     "model": "kokoro-v1.0",
     "loaded": true,
     "voices": ["af", "am", "bf", "bm"]
   }
   ```

4. **Restart TTS Service:**
   ```bash
   docker-compose restart tts-service
   ```

5. **Use Alternative Voice:**
   ```bash
   curl -X POST http://localhost:8002/tts \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Welcome to Same Day Suits",
       "voice": "af",  # Try different voice
       "speed": 1.0
     }'
   ```

---

### 6.2 Piper Fallback Not Working

**Symptoms:**
- Kokoro fails but Piper doesn't activate
- Error: "No TTS engine available"
- Silent audio output

**Resolution Steps:**

1. **Check Piper Installation:**
   ```bash
   docker exec tts-service piper --version
   ```

2. **Verify Piper Models:**
   ```bash
   docker exec tts-service ls -la /app/models/piper/
   ```

3. **Test Piper Directly:**
   ```bash
   docker exec tts-service bash -c "
   echo 'Test speech' | piper --model /app/models/piper/en_US-amy-medium.onnx --output_file /tmp/test.wav
   "
   ```

4. **Enable Fallback:**
   ```python
   # In TTS service config
   TTS_FALLBACK_ENABLED = True
   FALLBACK_ENGINE = 'piper'
   ```

5. **Update Fallback Priority:**
   ```python
   TTS_ENGINES = [
       ('kokoro', 'v1.0'),
       ('piper', 'en_US-amy-medium'),
       ('piper', 'en_US-lessac-medium')
   ]
   ```

---

### 6.3 Audio Not Playing

**Symptoms:**
- TTS generates but no sound heard
- Audio element shows loading indefinitely
- Volume icon indicates mute

**Resolution Steps:**

1. **Check Audio Permissions:**
   - Browser: Site settings → Sound → Allow
   - Windows: Volume Mixer → Browser → Not muted

2. **Test Audio Element:**
   ```javascript
   const audio = new Audio('/api/tts/speech.wav');
   audio.play().catch(e => console.error('Audio error:', e));
   ```

3. **Check Audio Format:**
   ```bash
   # Verify WAV format
   file speech.wav
   # Expected: RIFF (little-endian) data, WAVE audio
   ```

4. **Browser Autoplay Policy:**
   ```javascript
   // User interaction required for autoplay
   document.getElementById('startBtn').addEventListener('click', () => {
     audioContext.resume().then(() => {
       playSpeech();
     });
   });
   ```

5. **Check Audio Output:**
   ```bash
   # Windows
   Get-AudioDevice -List | Where-Object {$_.Type -eq 'Playback'}
   ```

---

### 6.4 Language Not Supported

**Symptoms:**
- Error: "Language 'fr' not supported"
- TTS reverts to English
- Garbled output for non-ASCII text

**Resolution Steps:**

1. **Check Supported Languages:**
   ```bash
   curl http://localhost:8002/languages
   ```
   Supported:
   - `en` - English (US/UK)
   - `es` - Spanish
   - `fr` - French (if model available)

2. **Language-Specific Models:**
   ```bash
   # Download French model
   curl -X POST http://localhost:8002/models/download \
     -d '{"language": "fr", "voice": "siwis-medium"}'
   ```

3. **Fallback to English:**
   ```python
   def synthesize(text: str, lang: str = 'en'):
       if lang not in SUPPORTED_LANGUAGES:
           logger.warning(f"Language {lang} not supported, using en")
           lang = 'en'
       return tts_engine.synthesize(text, lang)
   ```

4. **Character Encoding:**
   ```python
   # Ensure UTF-8 encoding
   text = text.encode('utf-8').decode('utf-8')
   ```

---

## 7. Debug Commands

### 7.1 Check Pattern Factory Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "pattern-factory",
  "version": "1.0.0",
  "timestamp": "2026-02-01T11:45:00Z",
  "dependencies": {
    "database": "connected",
    "queue": "operational",
    "storage": "accessible"
  }
}
```

---

### 7.2 Check EYESON Backend

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "eyeson-backend",
  "version": "2.1.0",
  "active_sessions": 5,
  "camera_status": "operational"
}
```

---

### 7.3 Check Cutter Queue

```bash
curl http://localhost:8000/queue/status
```

Expected response:
```json
{
  "queue_name": "cutter-jobs",
  "pending": 0,
  "processing": 1,
  "completed": 156,
  "failed": 2,
  "workers": [
    {"id": "worker-1", "status": "busy", "job_id": "job_123"},
    {"id": "worker-2", "status": "idle"}
  ],
  "last_processed": "2026-02-01T11:40:00Z"
}
```

---

### 7.4 View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f pattern-factory

# Last 100 lines
docker-compose logs --tail=100 pattern-factory

# With timestamps
docker-compose logs -f -t pattern-factory

# Filter for errors
docker-compose logs -f | grep -i error

# Save to file
docker-compose logs > logs_$(date +%Y%m%d_%H%M%S).txt
```

---

### 7.5 Additional Debug Commands

```bash
# Check container resource usage
docker stats

# Inspect container
docker inspect pattern-factory

# Execute commands in container
docker exec -it pattern-factory /bin/bash

# Check environment variables
docker exec pattern-factory env | grep -i app_

# Test database connection
docker exec pattern-factory python -c "
import psycopg2
conn = psycopg2.connect('postgresql://user:pass@db:5432/scanner')
print('Database connected')
conn.close()
"

# Check disk usage
docker system df -v

# Prune unused resources
docker system prune -f
```

---

## 8. Support Contacts and Escalation

### 8.1 Internal Support Team

| Role | Contact | Email | Hours |
|------|---------|-------|-------|
| L1 Support | Help Desk | support@samedaysuits.com | 24/7 |
| L2 Technical | DevOps Team | devops@samedaysuits.com | Mon-Fri 08:00-20:00 IST |
| L3 Engineering | Platform Team | platform@samedaysuits.com | Mon-Fri 09:00-18:00 IST |
| Security | Security Team | security@samedaysuits.com | 24/7 (Critical) |

### 8.2 Escalation Matrix

| Severity | Definition | Response Time | Escalation Path |
|----------|------------|---------------|-----------------|
| **P1 - Critical** | Production down, no patterns generating | 15 minutes | L1 → L2 (5 min) → L3 (15 min) |
| **P2 - High** | Major feature degraded, workarounds exist | 1 hour | L1 → L2 (30 min) → L3 (1 hour) |
| **P3 - Medium** | Minor feature issue, business continues | 4 hours | L1 → L2 (4 hours) |
| **P4 - Low** | Cosmetic issues, questions | 24 hours | L1 |

### 8.3 External Vendor Contacts

| Vendor | Service | Contact | Escalation |
|--------|---------|---------|------------|
| Optitex | Pattern Software | support@optitex.com | +1-xxx-xxx-xxxx |
| Docker | Container Platform | https://support.docker.com | Online portal |
| Cloudflare | DNS/CDN | support@cloudflare.com | Enterprise support |

### 8.4 Emergency Procedures

**Production System Down:**
1. Page on-call engineer: `+91-xxx-xxxx-xxxx`
2. Post in `#production-incidents` Slack channel
3. Create incident in PagerDuty
4. Notify stakeholders per communication plan

**Data Breach:**
1. Contact Security Team immediately: `security@samedaysuits.com`
2. Do NOT restart services
3. Preserve logs and system state
4. Follow incident response playbook

### 8.5 Documentation References

| Document | Location | Description |
|----------|----------|-------------|
| API Reference | `/docs/01-API-REFERENCE.md` | Complete API documentation |
| Deployment Guide | `/docs/02-DEPLOYMENT.md` | Installation and setup |
| Architecture | `/docs/03-ARCHITECTURE.md` | System design and components |
| Security | `/docs/04-SECURITY.md` | Security policies and procedures |
| Maintenance | `/docs/05-MAINTENANCE.md` | Routine maintenance tasks |

---

## Appendix A: Error Code Reference

| Code | Description | Category |
|------|-------------|----------|
| `E1001` | Camera permission denied | Camera |
| `E1002` | Camera hardware not found | Camera |
| `E2001` | Pattern Factory connection failed | API |
| `E2002` | JWT token invalid | API |
| `E2003` | CORS policy violation | API |
| `E3001` | Measurement confidence low | Validation |
| `E3002` | Measurement out of range | Validation |
| `E3003` | Missing required measurement | Validation |
| `E4001` | PLT generation failed | File Generation |
| `E4002` | PDS export failed | File Generation |
| `E4003` | Queue timeout | File Generation |
| `E5001` | Kokoro model not loaded | TTS |
| `E5002` | Audio playback failed | TTS |
| `E5003` | Language not supported | TTS |

---

## Appendix B: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│              PRODUCTION SCANNER - QUICK FIXES              │
├─────────────────────────────────────────────────────────────┤
│ Camera Black Screen:  F5 → Check permissions → Use HTTPS   │
│ API 401 Error:        Refresh token → Re-login             │
│ Pattern Timeout:      docker-compose restart queue-worker  │
│ Low Confidence:       Adjust lighting → Recapture          │
│ PLT Missing:          Check logs → Verify disk space       │
│ TTS Silent:           Check model → Test fallback          │
├─────────────────────────────────────────────────────────────┤
│ Emergency Contacts:                                         │
│   L1 Support:     support@samedaysuits.com                 │
│   L2 DevOps:      devops@samedaysuits.com                  │
│   On-Call:        +91-xxx-xxxx-xxxx                        │
└─────────────────────────────────────────────────────────────┘
```

---

*Document maintained by SameDaySuits Platform Team*  
*For updates, submit PR to: `docs/06-TROUBLESHOOTING.md`*
