# PRODUCTION-SCANNER

**EYESON Scanner + SameDaySuits Pattern Factory Integration**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Version:** 1.0  
**Last Updated:** 2026-02-01  
**Operations Manual:** [SUIT_AI_Master_Operations_Manual_v6_7_1.md](./docs/../reference/)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/AdmiralFabulous/PRODUCTION-SCANNER.git
cd PRODUCTION-SCANNER

# 2. Configure environment
copy .env.example .env
# Edit .env with your settings

# 3. Start the full stack
docker-compose up -d

# 4. Access the application
echo "EYESON Frontend: http://localhost:5173"
echo "Pattern Factory API: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
```

---

## What is PRODUCTION-SCANNER?

**PRODUCTION-SCANNER** is a unified platform combining **EYESON** (browser-based body scanning) with **Pattern Factory** (automated pattern generation) to create a seamless end-to-end bespoke garment manufacturing pipeline.

### The Complete Flow

```
Customer → 90s Scan → 28 Measurements → Pattern Factory → Cutter
                ↑                           ↓
         Kokoro TTS Voice            HPGL/PLT Output
        (Open Source, $14k/yr        Jindex UPC Inkjet
         savings vs ElevenLabs)      (TCP Port 9100)
```

### Key Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Scan-to-Pattern Time | < 5 minutes | ✅ |
| Measurement Accuracy (P0) | ±0.5-1cm | ✅ |
| Measurement Accuracy (P1) | ±1-2cm | ✅ |
| Voice AI Languages | 6 (en, es, fr, de, zh, ar) | ✅ |
| Cutter Throughput | 60+ patterns/hour | ✅ |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRODUCTION-SCANNER SYSTEM                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐         ┌─────────────────┐         ┌───────────────┐ │
│  │   EYESON        │         │   INTEGRATION   │         │   PATTERN     │ │
│  │   SCANNER       │────────▶│   LAYER         │────────▶│   FACTORY     │ │
│  │                 │  HTTPS  │                 │  HTTPS  │               │ │
│  │  • MediaPipe    │         │  • JWT Auth     │         │  • Nesting    │ │
│  │  • Kokoro TTS   │         │  • Transform    │         │  • HPGL Gen   │ │
│  │  • 28 Measures  │         │  • State Mgmt   │         │  • Cutter     │ │
│  └─────────────────┘         └─────────────────┘         └───────────────┘ │
│           │                                                        │       │
│           │                                                        ▼       │
│           │                                               ┌──────────────┐ │
│           │                                               │   JINDEX     │ │
│           │                                               │   CUTTER     │ │
│           │                                               │   TCP:9100   │ │
│           │                                               └──────────────┘ │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────┐                                                         │
│  │   CUSTOMER      │                                                         │
│  │   BROWSER       │                                                         │
│  │                 │                                                         │
│  │  90-Second Scan │                                                         │
│  └─────────────────┘                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Backend API** | FastAPI | 0.109+ |
| **Frontend** | React + TypeScript + Vite | 18+ / 5.0+ |
| **Pose Detection** | MediaPipe | 0.10+ |
| **TTS (Voice)** | Kokoro-82M + Piper | Apache 2.0 / MIT |
| **State Management** | Zustand | 4.5+ |
| **Authentication** | JWT (1-hour expiry) | RFC 7519 |
| **Cutter Protocol** | RAW TCP | Port 9100 |

---

## Directory Structure

```
PRODUCTION-SCANNER/
├── README.md                          # ← You are here
├── INTEGRATION_ARCHITECTURE.md        # Heavy integration documentation
├── docker-compose.yml                 # Full-stack orchestration
├── .env.example                       # Environment template
│
├── eyeson/                            # EYESON Scanner (browser-based)
│   ├── backend/                       # FastAPI (port 8001)
│   │   ├── src/api/                   # 6 API modules
│   │   │   ├── auth.py               # JWT authentication
│   │   │   ├── sessions.py           # Scan session management
│   │   │   ├── measurements.py       # 28-measurement extraction
│   │   │   ├── voice.py              # Kokoro TTS endpoints
│   │   │   └── webhooks.py           # External integrations
│   │   ├── src/services/
│   │   │   └── tts_service.py        # Kokoro-82M + Piper
│   │   └── requirements.txt
│   │
│   ├── frontend/                      # React + Vite (port 5173)
│   │   ├── src/components/           # 7 scan flow screens
│   │   │   ├── WelcomeScreen.tsx
│   │   │   ├── PositioningScreen.tsx
│   │   │   ├── CaptureScreen.tsx     # MediaPipe integration
│   │   │   ├── ProcessingScreen.tsx
│   │   │   ├── ResultsScreen.tsx
│   │   │   ├── ReviewScreen.tsx
│   │   │   └── CompleteScreen.tsx
│   │   ├── src/services/
│   │   │   ├── patternFactoryApi.ts  # Pattern Factory client
│   │   │   └── sessionApi.ts         # Session management
│   │   ├── src/utils/
│   │   │   └── measurementMapping.ts # 28-measurement mapper
│   │   └── package.json
│   │
│   └── docs/
│       ├── BUILD_NOTES.md
│       ├── PATTERN_FACTORY_INTEGRATION.md
│       └── ADR-001-Open-Source-TTS.md
│
├── pattern-factory/                   # Pattern Factory v6.4.3 (port 8000)
│   ├── src/api/
│   │   └── web_api.py                # FastAPI endpoints
│   ├── src/core/
│   │   ├── pipeline.py               # Black Box pipeline
│   │   ├── scaler.py                 # Measurement scaler
│   │   └── resilient_cutter_queue.py # WAL-based queue
│   ├── src/nesting/
│   │   └── algorithms.py             # 8 nesting algorithms
│   ├── src/workers/
│   │   ├── nesting_worker.py         # Background nesting
│   │   └── jindex_cutter.py          # TCP cutter interface
│   ├── docs/
│   │   ├── SYSTEM_ARCHITECTURE.md
│   │   └── SOP_COMPLETE.md
│   └── tests/
│
└── docs/                              # Comprehensive documentation
    ├── 01-SYSTEM-OVERVIEW.md          # Architecture diagrams
    ├── 02-MEASUREMENT-MAPPING.md      # 28-measurement spec
    ├── 03-ORDER-STATE-MACHINE.md      # 27-state flow
    ├── 04-API-REFERENCE.md            # All endpoints
    ├── 05-SECURITY-AUTH.md            # JWT, CORS, TLS
    └── 06-TROUBLESHOOTING.md          # Common issues
```

---

## Key Integration Points

### 1. Measurement Mapping (28 Codes)

EYESON extracts 28 body measurements which are transformed to Pattern Factory format:

| EYESON Field | Pattern Factory | Description |
|--------------|-----------------|-------------|
| `chest_girth` | **Cg** | Chest circumference |
| `waist_girth` | **Wg** | Waist circumference |
| `hip_girth` | **Hg** | Hip circumference |
| `shoulder_width` | **Sh** | Shoulder width |
| `arm_length` | **Al** | Arm length |
| ... | ... | (22 more) |

**Reference:** [02-MEASUREMENT-MAPPING.md](./docs/02-MEASUREMENT-MAPPING.md)

### 2. 27-State Order Machine

```
S01 ORDER_CREATED → S02 RECEIVED → S03 SCAN_RECEIVED → S04 PROCESSING
                                                             ↓
S06 CUTTING → S07 PATTERN_CUT → S08 STAGING → S09 QA → S14 READY_FOR_PICKUP
   ↑                                                              ↓
S05 PATTERN_READY ← S04a VALIDATION                            S15 PICKED_UP
```

**EYESON Integration:**
- `S02 → S03`: When EYESON POSTs new order
- `S04 → S05`: When EYESON polls and `files_available.plt=true`

**Reference:** [03-ORDER-STATE-MACHINE.md](./docs/03-ORDER-STATE-MACHINE.md)

### 3. JWT Authentication (1-Hour Expiry)

```typescript
// EYESON → Pattern Factory authentication
const response = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});
const { access_token, expires_in } = await response.json();
// Use token in: Authorization: Bearer ${access_token}
```

**Reference:** [05-SECURITY-AUTH.md](./docs/05-SECURITY-AUTH.md)

---

## Integration Architecture

For detailed integration documentation, see **[INTEGRATION_ARCHITECTURE.md](./INTEGRATION_ARCHITECTURE.md)** which includes:

- Complete data flow diagrams
- API contract specifications
- Sequence diagrams for scan-to-cutter flow
- Error handling matrix
- Performance requirements

---

## Running Locally

### Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- 4GB RAM minimum
- Ports: 5173, 8000, 8001

### Development Mode

```bash
# 1. Start infrastructure services
docker-compose up -d redis postgres

# 2. Start Pattern Factory
cd pattern-factory
pip install -r requirements.txt
uvicorn src.api.web_api:app --reload --port 8000

# 3. Start EYESON Backend (new terminal)
cd eyeson/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# 4. Start EYESON Frontend (new terminal)
cd eyeson/frontend
npm install
npm run dev
```

### Production Mode

```bash
# Start everything with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale nesting-worker=3
```

---

## API Endpoints

### Pattern Factory API (Port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | JWT authentication |
| POST | `/orders` | Create order with measurements |
| GET | `/orders/{id}/status` | Get order status |
| GET | `/orders/{id}/plt` | Download cutter file |
| GET | `/orders/{id}/pds` | Download PDS file |
| GET | `/orders/{id}/dxf` | Download DXF file |
| GET | `/queue/status` | Cutter queue status |

### EYESON API (Port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions` | Create scan session |
| POST | `/sessions/{id}/calibrate` | Submit calibration |
| POST | `/sessions/{id}/upload` | Upload scan video |
| GET | `/measurements/{session_id}` | Get measurements |
| POST | `/voice/synthesize` | Text-to-speech |
| GET | `/voice/prompts/{language}` | Get voice prompts |

**Full Reference:** [04-API-REFERENCE.md](./docs/04-API-REFERENCE.md)

---

## Cost Savings

| Service | Previous Cost | New Solution | Annual Savings |
|---------|--------------|--------------|----------------|
| TTS (Voice AI) | ElevenLabs $1,200/mo | Kokoro-82M (Apache 2.0) + Piper (MIT) | **$14,400/year** |

---

## Documentation

| Document | Description |
|----------|-------------|
| [INTEGRATION_ARCHITECTURE.md](./INTEGRATION_ARCHITECTURE.md) | Heavy integration documentation |
| [docs/01-SYSTEM-OVERVIEW.md](./docs/01-SYSTEM-OVERVIEW.md) | High-level architecture |
| [docs/02-MEASUREMENT-MAPPING.md](./docs/02-MEASUREMENT-MAPPING.md) | 28-measurement specification |
| [docs/03-ORDER-STATE-MACHINE.md](./docs/03-ORDER-STATE-MACHINE.md) | 27-state order flow |
| [docs/04-API-REFERENCE.md](./docs/04-API-REFERENCE.md) | Complete API documentation |
| [docs/05-SECURITY-AUTH.md](./docs/05-SECURITY-AUTH.md) | Security & authentication |
| [docs/06-TROUBLESHOOTING.md](./docs/06-TROUBLESHOOTING.md) | Common issues & solutions |

---

## GitHub Repositories

| Repository | URL | Description |
|------------|-----|-------------|
| **PRODUCTION-SCANNER** (this repo) | `https://github.com/AdmiralFabulous/PRODUCTION-SCANNER` | Unified integration |
| EYESON | `https://github.com/AdmiralFabulous/EYESON` | Browser scanner |
| Pattern Factory | `https://github.com/AdmiralFabulous/samedaysuits-pattern-factory` | Pattern generation |

---

## Contributing

Please read [CONTRIBUTING.md](./eyeson/CONTRIBUTING.md) for contribution guidelines.

---

## License

This project is licensed under the MIT License - see [LICENSE](./eyeson/LICENSE) file.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/AdmiralFabulous/PRODUCTION-SCANNER/issues)
- **Documentation:** See `/docs` folder
- **Operations Manual:** SUIT_AI_Master_Operations_Manual_v6_7_1.md

---

*Built with ❤️ by the SameDaySuits team*
