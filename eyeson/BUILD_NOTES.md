# EYESON Build Notes

## Project Overview

**EYESON** - Enterprise BodyScan Platform  
**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2026-02-01

---

## Repository Structure

```
eyeson-production/
├── backend/                    # FastAPI + Open Source TTS
│   ├── src/
│   │   ├── api/               # API endpoints
│   │   ├── services/          # TTS service (Kokoro-82M)
│   │   └── core/              # Configuration
│   └── requirements.txt
├── frontend/                  # React + MediaPipe
│   ├── src/
│   │   ├── components/        # 7 scan screens
│   │   ├── services/          # API clients
│   │   ├── store/             # Zustand state
│   │   └── utils/             # Measurement mapping
│   └── package.json
└── docs/
    ├── PATTERN_FACTORY_INTEGRATION.md
    ├── ADR-001-Open-Source-TTS.md
    └── BUILD_NOTES.md (this file)
```

---

## Backend Integration

### SameDaySuits Pattern Factory Connection

**Backend Location:**  
`D:\SameDaySuits\_SameDaySuits\PILLARS_SAMEDAYSUITS\XX-EXPERIMENTS\REVERSE-ENGINEER-PDS\production`

**Operations Manual:**  
`D:\SameDaySuits\_SameDaySuits\DOCUMENTATION\SUIT_AI_Master_Operations_Manual_v6_7_1.md`

### Key Integration Points

| Component | Pattern Factory Ref | Implementation |
|-----------|---------------------|----------------|
| **Authentication** | Section 2.5 - Security Layer | JWT tokens (1-hour expiry) |
| **Order State Machine** | Section 1.2 - 27 States | S02→S03→S04→S05→S06→S07 |
| **Measurements** | Section 13 - Database Schema | 28-measurement JSON format |
| **File Downloads** | Section 6 - DXF Holy Grail | PLT, PDS, DXF formats |
| **API Endpoints** | `src/api/web_api.py` | POST /orders, GET /orders/{id}/plt |

### Measurement Code Mapping

**Pattern Factory Format:** (ref: ops manual Section 13)

| Code | Measurement | EYESON Field |
|------|-------------|--------------|
| `Cg` | Chest Girth | `chest_girth` |
| `Wg` | Waist Girth | `waist_girth` |
| `Hg` | Hip Girth | `hip_girth` |
| `Sh` | Shoulder Width | `shoulder_width` |
| `Al` | Arm Length | `arm_length` |
| `Bw` | Back Width | `back_width` |
| `Nc` | Neck Circumference | `neck_girth` |
| `Bi` | Bicep Girth | `bicep_girth` |
| `Wc` | Wrist Circumference | `wrist_girth` |
| `Il` | Inseam Length | `inseam` |
| `Th` | Thigh Girth | `thigh_girth` |
| `Kn` | Knee Girth | `knee_girth` |
| `Ca` | Calf Girth | `calf_girth` |

**Implementation:** `frontend/src/utils/measurementMapping.ts`

---

## Quick Start

### 1. Start Pattern Factory Backend

```bash
cd D:\SameDaySuits\_SameDaySuits\PILLARS_SAMEDAYSUITS\XX-EXPERIMENTS\REVERSE-ENGINEER-PDS\production

# Using Docker
docker-compose up -d

# Or Python directly
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/api/web_api.py
```

Backend runs at: `http://localhost:8000`

### 2. Start EYESON Frontend

```bash
cd eyeson-production\frontend

npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

### 3. Test the Flow

1. Open `http://localhost:5173`
2. Select language → Continue
3. Accept consent
4. Follow device setup instructions
5. Allow camera permissions
6. Complete calibration
7. **See real-time skeleton overlay!**
8. Record 30-second video
9. Watch processing animation
10. **Download PLT/PDS/DXF files**

---

## Environment Configuration

### Frontend `.env.local`

```bash
# Pattern Factory API
VITE_PATTERN_FACTORY_URL=http://localhost:8000

# Supabase (optional - for direct DB access)
VITE_SUPABASE_URL=your-supabase-url
VITE_SUPABASE_ANON_KEY=your-anon-key

# Stitch (optional - for design generation)
STITCH_API_KEY=your-stitch-key
```

### Backend `.env`

```bash
# See backend/.env.example for full configuration
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
```

---

## Architecture Decisions

### Open Source TTS (Kokoro-82M)

**Decision:** Replace proprietary ElevenLabs with open source  
**Rationale:** 
- Cost: $0 vs $0.12/scan
- Privacy: Self-hosted
- Latency: 200ms vs 800ms

**Ref:** `docs/ADR-001-Open-Source-TTS.md`

### Browser-Based Scanning

**Technology Stack:**
- React 18 + TypeScript
- MediaPipe Pose (33 landmarks)
- MediaRecorder API
- WebSocket for real-time updates

**Flow:**
```
Welcome → Consent → Setup → Calibration → Capture → Processing → Results
   8s       7s       10s       12s          30s       20s        10s
                                                        ↓
                                              Submit to Pattern Factory
                                                        ↓
                                              Download PLT/PDS/DXF
```

---

## API Integration

### Authentication Flow

```typescript
// 1. Login
const { access_token } = await login(email, password)

// 2. All requests include JWT
Authorization: Bearer <access_token>

// 3. Auto-refresh on 401
// Implemented in axios interceptor
```

**Ref:** ops manual Section 2.5 - JWT with 1-hour expiry

### Order Submission

```typescript
// Transform measurements
const pfMeasurements = transformToPatternFactory(eyesonMeasurements)

// Submit order
const order = await submitOrder({
  customer_id: 'customer-123',
  garment_type: 'jacket',
  fit_type: 'regular',
  measurements: pfMeasurements,
})

// Poll for files
await pollForFiles(order.order_id, (status) => {
  if (status.files_available.plt) {
    // Download ready
  }
})
```

**Ref:** ops manual Section 1.2 - Order State Machine

---

## Testing

### Manual Test Checklist

- [ ] Welcome screen loads
- [ ] Language selector works
- [ ] Camera permissions requested
- [ ] MediaPipe pose detected
- [ ] Green skeleton overlay appears
- [ ] 30-second recording works
- [ ] Order submitted to Pattern Factory
- [ ] Files generated and downloadable

### API Test Commands

```bash
# Health check
curl http://localhost:8000/api/health

# Submit test order
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "customer_id": "test-customer",
    "garment_type": "jacket",
    "fit_type": "regular",
    "measurements": {
      "Cg": {"value": 102.5, "unit": "cm", "confidence": 0.95}
    }
  }'
```

---

## Deployment

### Production Checklist

- [ ] Set `VITE_PATTERN_FACTORY_URL` to production API
- [ ] Configure CORS on Pattern Factory
- [ ] Enable TLS 1.3 (ref: ops manual Section 2.5)
- [ ] Set up rate limiting (100 req/min)
- [ ] Configure JWT secret rotation
- [ ] Enable database encryption at rest

### Build Commands

```bash
# Frontend production build
cd frontend
npm run build

# Backend deployment
cd backend
docker build -t eyeson-backend .
docker push eyeson-backend:latest
```

---

## Troubleshooting

### Camera Not Working
- Ensure HTTPS in production (required for getUserMedia)
- Check browser permissions
- Verify CORS settings on backend

### Pattern Factory Connection Failed
- Verify backend is running: `curl http://localhost:8000/api/health`
- Check `VITE_PATTERN_FACTORY_URL` in `.env.local`
- Review CORS configuration in backend

### Measurements Not Submitting
- Check JWT token expiry (auto-refresh implemented)
- Verify all 13 primary measurements present
- Review browser console for API errors

---

## References

### Documentation

| Document | Path | Purpose |
|----------|------|---------|
| **Operations Manual** | `DOCUMENTATION\SUIT_AI_Master_Operations_Manual_v6_7_1.md` | System architecture, API specs |
| **Pattern Factory Backend** | `REVERSE-ENGINEER-PDS\production\docs\SYSTEM_ARCHITECTURE.md` | Backend architecture |
| **Pattern Factory API** | `REVERSE-ENGINEER-PDS\production\src\api\web_api.py` | FastAPI routes |
| **Integration Guide** | `docs\PATTERN_FACTORY_INTEGRATION.md` | This integration |
| **Architecture Decision** | `docs\ADR-001-Open-Source-TTS.md` | TTS selection rationale |

### External References

- **MediaPipe Pose:** https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
- **Kokoro-82M:** https://huggingface.co/onnx-community/Kokoro-82M-ONNX
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/

---

## Git History

```
790cc77 feat(integration): integrate with Pattern Factory backend
540ab11 docs(changelog): add Phase 2 frontend details
df3c1a2 feat(frontend): complete React frontend with MediaPipe
d346e9e docs(stitch): add Stitch usage guide
af44d15 fix(api): pydantic v2 compatibility
373a7e9 docs(adr): add architecture decision record
d403ddc docs(project): add LICENSE, CONTRIBUTING
099b7f2 feat(api): add core API endpoints
f011059 feat(voice): implement open source TTS
```

---

## Contact

**Repository:** https://github.com/AdmiralFabulous/EYESON  
**Backend:** SameDaySuits Pattern Factory v6.4.3  
**Operations:** SUIT_AI_Master_Operations_Manual_v6_7_1.md
