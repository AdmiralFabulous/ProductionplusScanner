# Architecture Decision Record (ADR) 001: Open Source Text-to-Speech

## Status
**Accepted** - Implemented in v1.0.0

## Context

The EYESON platform requires a Text-to-Speech (TTS) system to provide voice guidance during the 90-second body scan experience. The initial design specified using **ElevenLabs**, a commercial TTS service known for high-quality voice synthesis.

### Requirements for TTS:
- Latency: <500ms for short phrases
- Quality: Natural-sounding, not robotic
- Cost: Sustainable at scale
- Privacy: Data stays within our infrastructure
- Browser compatibility: Works in web environment
- Languages: English, Spanish, French, German, Chinese

## Decision

**Changed from proprietary ElevenLabs to fully open source TTS stack:**

### Primary: Kokoro-82M
- **License**: Apache 2.0 (fully open source)
- **Size**: 82M parameters
- **Latency**: ~100-300ms on CPU
- **Quality**: MOS 4.3 (near-human)
- **Format**: ONNX (browser and server compatible)
- **Repository**: `onnx-community/Kokoro-82M-ONNX`

### Fallback: Piper TTS
- **License**: MIT (fully open source)
- **Size**: 10-50M parameters
- **Latency**: ~50-200ms on CPU
- **Quality**: MOS 4.0 (natural)
- **Languages**: 30+ languages supported
- **Repository**: `rhasspy/piper`

## Consequences

### Positive

1. **Cost Reduction**
   - ElevenLabs: ~$0.08-0.10 per minute = ~$0.12 per scan
   - Open Source: $0 (self-hosted) = $0 per scan
   - **Savings**: ~$1,200/month at 10,000 scans

2. **Privacy & Compliance**
   - Voice data never leaves our infrastructure
   - No third-party API calls for TTS
   - Easier GDPR/SOC 2 compliance
   - No data retention concerns with external vendors

3. **Latency Improvement**
   - ElevenLabs: ~500-800ms (network roundtrip)
   - Kokoro: ~200ms (local inference)
   - **50-75% faster voice response**

4. **Reliability**
   - No dependency on external service availability
   - No rate limiting concerns
   - Works offline in air-gapped environments

5. **Customization**
   - Can fine-tune models for domain-specific vocabulary
   - Can add custom voices
   - Full control over voice characteristics

### Negative

1. **Infrastructure Complexity**
   - Must host and scale TTS inference ourselves
   - Requires GPU nodes for production load
   - Additional monitoring and maintenance

2. **Voice Quality Trade-off**
   - Kokoro-82M is excellent but not quite ElevenLabs quality
   - May notice slight difference in naturalness
   - Acceptable for guided instructions, not audiobooks

3. **Initial Setup**
   - Must download and cache models (~200MB)
   - ONNX Runtime configuration required
   - Voice prompt caching strategy needed

4. **Browser Limitations**
   - Full model too large for browser download
   - Requires server-side inference
   - WebRTC/WebSocket for streaming audio

## Mitigation Strategies

| Concern | Mitigation |
|---------|------------|
| Infrastructure | Use Triton Inference Server with auto-scaling |
| Quality | Implement caching to reuse common phrases |
| Setup | Pre-build Docker images with models baked in |
| Browser | Use WebSocket streaming for real-time audio |

## Implementation

### Architecture
```
Browser (React) ←→ FastAPI ←→ Kokoro-82M (ONNX Runtime)
                              ↓ (fallback)
                         Piper TTS (if needed)
```

### Code Changes
- `src/services/tts_service.py` - New TTS service with caching
- `src/api/voice.py` - Voice API endpoints
- `src/core/config.py` - TTS configuration options
- `requirements.txt` - Added onnxruntime, piper-tts

### Configuration
```python
TTS_MODEL=onnx-community/Kokoro-82M-ONNX
TTS_DEVICE=cpu  # or cuda
TTS_VOICE=af    # American Female
TTS_SPEED=1.0
TTS_CACHE_ENABLED=true
TTS_FALLBACK_MODEL=en_US-lessac-medium
```

## Alternatives Considered

### Alternative 1: Keep ElevenLabs
**Pros**: Best quality, simple API, managed service  
**Cons**: $0.12/scan, privacy concerns, latency, rate limits  
**Decision**: Rejected - cost and privacy issues

### Alternative 2: Use Coqui TTS
**Pros**: Open source, good quality  
**Cons**: Larger models (200M+), slower inference  
**Decision**: Rejected - too slow for real-time guidance

### Alternative 3: Use Web Speech API
**Pros**: Native browser API, free  
**Cons**: Limited browser support, quality varies, no control  
**Decision**: Rejected - inconsistent experience

## Related Decisions

- ADR-002: STT Provider Selection (Deepgram retained)
- ADR-003: ML Inference Architecture (Triton Inference Server)

## References

- [Kokoro-82M HuggingFace](https://huggingface.co/onnx-community/Kokoro-82M-ONNX)
- [Piper TTS GitHub](https://github.com/rhasspy/piper)
- [ONNX Runtime](https://onnxruntime.ai/)

## Date
2026-02-01

## Authors
- Architecture Team
- ML Engineering

## Approval
- [x] CTO
- [x] Lead Architect
- [x] Product Manager
