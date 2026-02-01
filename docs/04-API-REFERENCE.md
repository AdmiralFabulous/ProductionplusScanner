# API Reference Documentation

**Version:** 1.0  
**Last Updated:** February 2026  
**Base URLs:**
- Pattern Factory API: `http://localhost:8000/api/v1`
- EYESON API: `https://api.eyeson.io/api/v1`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Pattern Factory API](#pattern-factory-api)
   - [Authentication Endpoints](#pattern-factory-authentication)
   - [Order Management](#order-management)
   - [File Downloads](#file-downloads)
   - [Queue Management](#queue-management)
4. [EYESON API](#eyeson-api)
   - [Sessions](#sessions)
   - [Measurements](#measurements)
   - [Voice](#voice)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)

---

## Overview

This document provides comprehensive API reference for the SameDaySuits production scanning system. It covers two main APIs:

1. **Pattern Factory API** - Manages order processing, pattern generation, and file downloads
2. **EYESON API** - Handles body scan sessions, measurement extraction, and voice guidance

### Common Headers

All API requests should include the following headers:

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes (for JSON endpoints) |
| `Authorization` | `Bearer <token>` | Yes (protected endpoints) |
| `Accept` | `application/json` | Yes |

---

## Authentication

### JWT Token Flow

The APIs use JWT (JSON Web Tokens) for authentication:

1. Obtain access token via `/auth/login` or `/auth/token`
2. Include token in `Authorization: Bearer <token>` header
3. Token expires after 1 hour (3600 seconds)
4. Use refresh token to obtain new access token

### Token Response Format

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "def50200a8b2c3d4e5f6..."
}
```

---

## Pattern Factory API

Base URL: `http://localhost:8000/api/v1`

---

### Pattern Factory Authentication

#### POST /auth/login

Authenticate user and obtain JWT tokens.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "def50200a8b2c3d4e5f6..."
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Authentication successful |
| 400 | Invalid request format |
| 401 | Invalid credentials |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure_password"
  }'
```

---

#### POST /auth/refresh

Refresh an expired access token using the refresh token.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |

**Request Body:**

```json
{
  "refresh_token": "def50200a8b2c3d4e5f6..."
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "new_refresh_token_..."
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Token refreshed successfully |
| 400 | Invalid request format |
| 401 | Invalid or expired refresh token |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "def50200a8b2c3d4e5f6..."
  }'
```

---

### Order Management

#### POST /orders

Create a new order with body measurements. Triggers the pattern generation pipeline.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer <token>` |

**Request Body Schema:**

```json
{
  "order_id": "SDS-20260201-0001-A",    // Optional, auto-generated if not provided
  "customer_id": "cust_12345",
  "garment_type": "jacket",               // Enum: "tee", "jacket", "trousers", "cargo"
  "fit_type": "slim",                     // Enum: "slim", "regular", "classic"
  "priority": "normal",                   // Enum: "rush", "high", "normal", "low"
  "measurements": {
    // P0 Measurements (Critical - ±0.5-1cm)
    "Cg": { "value": 102.5, "unit": "cm", "confidence": 0.92 },  // Chest Girth
    "Wg": { "value": 88.3, "unit": "cm", "confidence": 0.89 },   // Waist Girth
    "Hg": { "value": 98.7, "unit": "cm", "confidence": 0.91 },   // Hip Girth
    "Sh": { "value": 46.2, "unit": "cm", "confidence": 0.94 },   // Shoulder Width
    "Al": { "value": 64.8, "unit": "cm", "confidence": 0.88 },   // Arm Length
    "Bw": { "value": 38.5, "unit": "cm", "confidence": 0.90 },   // Back Width
    "Nc": { "value": 39.4, "unit": "cm", "confidence": 0.93 },   // Neck Circumference
    // P1 Measurements (Important - ±1-2cm)
    "Bi": { "value": 32.1, "unit": "cm", "confidence": 0.85 },   // Bicep Girth
    "Wc": { "value": 17.8, "unit": "cm", "confidence": 0.87 },   // Wrist Circumference
    "Il": { "value": 82.4, "unit": "cm", "confidence": 0.86 },   // Inseam Length
    "Th": { "value": 58.3, "unit": "cm", "confidence": 0.84 },   // Thigh Girth
    "Kn": { "value": 38.9, "unit": "cm", "confidence": 0.83 },   // Knee Girth
    "Ca": { "value": 37.2, "unit": "cm", "confidence": 0.82 }    // Calf Girth
  },
  "scan_metadata": {
    "device_type": "photogrammetry",      // Enum: "photogrammetry", "lidar", "structured_light"
    "vertex_count": 50000,
    "capture_timestamp": "2026-02-01T08:30:00Z",
    "confidence": 0.88
  }
}
```

**Response (201 Created):**

```json
{
  "order_id": "SDS-20260201-0001-A",
  "status": "scan_received",
  "customer_id": "cust_12345",
  "garment_type": "jacket",
  "fit_type": "slim",
  "measurements": { /* ... */ },
  "created_at": "2026-02-01T08:30:15Z",
  "files_available": {
    "plt": false,
    "pds": false,
    "dxf": false
  }
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 201 | Order created successfully |
| 400 | Invalid request data |
| 401 | Unauthorized - invalid token |
| 422 | Validation error |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X POST "http://localhost:8000/api/v1/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "customer_id": "cust_12345",
    "garment_type": "jacket",
    "fit_type": "slim",
    "priority": "normal",
    "measurements": {
      "Cg": { "value": 102.5, "unit": "cm", "confidence": 0.92 },
      "Wg": { "value": 88.3, "unit": "cm", "confidence": 0.89 },
      "Hg": { "value": 98.7, "unit": "cm", "confidence": 0.91 }
    }
  }'
```

---

#### GET /orders/{order_id}

Retrieve complete order details.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | string | Order identifier (e.g., SDS-20260201-0001-A) |

**Response (200 OK):**

```json
{
  "order_id": "SDS-20260201-0001-A",
  "status": "pattern_ready",
  "customer_id": "cust_12345",
  "garment_type": "jacket",
  "fit_type": "slim",
  "measurements": { /* ... */ },
  "created_at": "2026-02-01T08:30:15Z",
  "files_available": {
    "plt": true,
    "pds": true,
    "dxf": true
  }
}
```

**Order Status Values:**

| Status | Description |
|--------|-------------|
| `draft` | Initial order created |
| `paid` | Payment confirmed |
| `scan_received` | Measurements uploaded |
| `processing` | Pattern being generated |
| `pattern_ready` | Pattern files ready |
| `cutting` | Sent to cutter queue |
| `pattern_cut` | Fabric cut complete |
| `error` | Processing failed |

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized |
| 404 | Order not found |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/orders/SDS-20260201-0001-A" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### GET /orders/{order_id}/status

Get order processing status with file availability.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | string | Order identifier |

**Response (200 OK):**

```json
{
  "order_id": "SDS-20260201-0001-A",
  "status": "pattern_ready",
  "files_available": {
    "plt": true,
    "pds": true,
    "dxf": true
  },
  "processing_time_ms": 12450,
  "fabric_length_cm": 285.5,
  "fabric_utilization": 0.87
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized |
| 404 | Order not found |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/orders/SDS-20260201-0001-A/status" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### DELETE /orders/{order_id}

Cancel and delete an order.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | string | Order identifier |

**Response (200 OK):**

```json
{
  "order_id": "SDS-20260201-0001-A",
  "status": "cancelled",
  "message": "Order cancelled successfully"
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Order cancelled |
| 400 | Cannot cancel (already processed) |
| 401 | Unauthorized |
| 404 | Order not found |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X DELETE "http://localhost:8000/api/v1/orders/SDS-20260201-0001-A" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### File Downloads

#### GET /orders/{order_id}/plt

Download HPGL cutter file (.plt format).

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |
| `Accept` | `application/octet-stream` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | string | Order identifier |

**Response (200 OK):**

Binary file content (HPGL format)

**Response Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/octet-stream` |
| `Content-Disposition` | `attachment; filename="SDS-20260201-0001-A.plt"` |

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | File downloaded |
| 401 | Unauthorized |
| 404 | Order or file not found |
| 409 | File not ready yet |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/orders/SDS-20260201-0001-A/plt" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  --output "SDS-20260201-0001-A.plt"
```

---

#### GET /orders/{order_id}/pds

Download Optitex PDS pattern file.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |
| `Accept` | `application/octet-stream` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | string | Order identifier |

**Response (200 OK):**

Binary file content (Optitex PDS format)

**Response Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/octet-stream` |
| `Content-Disposition` | `attachment; filename="SDS-20260201-0001-A.pds"` |

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | File downloaded |
| 401 | Unauthorized |
| 404 | Order or file not found |
| 409 | File not ready yet |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/orders/SDS-20260201-0001-A/pds" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  --output "SDS-20260201-0001-A.pds"
```

---

#### GET /orders/{order_id}/dxf

Download DXF CAD file.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |
| `Accept` | `application/octet-stream` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | string | Order identifier |

**Response (200 OK):**

Binary file content (DXF format)

**Response Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/octet-stream` |
| `Content-Disposition` | `attachment; filename="SDS-20260201-0001-A.dxf"` |

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | File downloaded |
| 401 | Unauthorized |
| 404 | Order or file not found |
| 409 | File not ready yet |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/orders/SDS-20260201-0001-A/dxf" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  --output "SDS-20260201-0001-A.dxf"
```

---

### Queue Management

#### GET /queue/status

Get cutter queue status and metrics.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

**Response (200 OK):**

```json
{
  "pending_jobs": 12,
  "processing_jobs": 3,
  "completed_jobs": 145,
  "failed_jobs": 2,
  "average_wait_time_ms": 45000
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "http://localhost:8000/api/v1/queue/status" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

#### POST /queue/{order_id}/priority

Update order priority in the queue.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `Authorization` | `Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `order_id` | string | Order identifier |

**Request Body:**

```json
{
  "priority": "rush"   // Enum: "rush", "high", "normal", "low"
}
```

**Response (200 OK):**

```json
{
  "order_id": "SDS-20260201-0001-A",
  "priority": "rush",
  "queue_position": 1,
  "estimated_start": "2026-02-01T09:00:00Z"
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Priority updated |
| 400 | Invalid priority level |
| 401 | Unauthorized |
| 404 | Order not found |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X POST "http://localhost:8000/api/v1/queue/SDS-20260201-0001-A/priority" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{"priority": "rush"}'
```

---

## EYESON API

Base URL: `https://api.eyeson.io/api/v1`

---

### Sessions

#### POST /sessions

Create a new body scan session.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |

**Request Body:**

```json
{
  "user_id": "user_12345",              // Optional
  "scan_mode": "video",                 // Enum: "video", "dual_image"
  "language": "en",                     // ISO 639-1 language code
  "device_info": {
    "type": "mobile",
    "os": "iOS 17.0",
    "camera": "12MP"
  }
}
```

**Response (201 Created):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "initiated",
  "scan_mode": "video",
  "language": "en",
  "websocket_url": "wss://api.eyeson.io/ws/550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2026-02-01T09:30:00Z",
  "created_at": "2026-02-01T08:30:00Z"
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 201 | Session created |
| 400 | Invalid request |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X POST "https://api.eyeson.io/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_mode": "video",
    "language": "en",
    "user_id": "user_12345"
  }'
```

---

#### POST /sessions/{id}/calibrate

Submit calibration image with ArUco marker.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `multipart/form-data` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Session ID (UUID) |

**Request Body (multipart/form-data):**

| Field | Type | Description |
|-------|------|-------------|
| `marker_image` | file | Image containing ArUco calibration marker |
| `height_cm` | number | User height in cm (optional, for validation) |

**Response (200 OK):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "calibration": {
    "marker_size_cm": 14.0,
    "scale_factor": 0.035,
    "marker_corners": [[100, 200], [300, 200], [300, 400], [100, 400]],
    "confidence": 0.95,
    "height_estimate_cm": 175.0
  },
  "status": "calibrating",
  "message": "Calibration successful. Ready for capture."
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Calibration successful |
| 400 | Invalid image or session state |
| 404 | Session not found |
| 422 | Marker detection failed |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X POST "https://api.eyeson.io/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/calibrate" \
  -F "marker_image=@calibration_photo.jpg" \
  -F "height_cm=175"
```

---

#### POST /sessions/{id}/upload

Upload scan media (video or images).

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `multipart/form-data` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | string | Session ID (UUID) |

**Request Body (multipart/form-data):**

For VIDEO mode:
| Field | Type | Description |
|-------|------|-------------|
| `video` | file | Scan video file (MP4) |

For DUAL_IMAGE mode:
| Field | Type | Description |
|-------|------|-------------|
| `front_image` | file | Front view image |
| `side_image` | file | Side view image |

**Response (200 OK):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "capturing",
  "message": "Media uploaded successfully. Processing started.",
  "estimated_seconds": 30
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Upload successful |
| 400 | Invalid media or session state |
| 404 | Session not found |
| 413 | File too large |
| 500 | Internal server error |

**Example cURL (Video):**

```bash
curl -X POST "https://api.eyeson.io/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/upload" \
  -F "video=@scan_video.mp4"
```

**Example cURL (Dual Image):**

```bash
curl -X POST "https://api.eyeson.io/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000/upload" \
  -F "front_image=@front_view.jpg" \
  -F "side_image=@side_view.jpg"
```

---

### Measurements

#### GET /measurements/{session_id}

Retrieve body measurements for a completed scan session.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Session ID (UUID) |

**Response (200 OK):**

```json
{
  "measurement_id": "meas_550e8400",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_12345",
  "created_at": "2026-02-01T08:30:30Z",
  
  "chest_girth": {
    "value": 102.5,
    "unit": "cm",
    "confidence": 0.92,
    "method": "auto",
    "accuracy_grade": "P0"
  },
  "waist_girth": {
    "value": 88.3,
    "unit": "cm",
    "confidence": 0.89,
    "method": "auto",
    "accuracy_grade": "P0"
  },
  "hip_girth": {
    "value": 98.7,
    "unit": "cm",
    "confidence": 0.91,
    "method": "auto",
    "accuracy_grade": "P0"
  },
  "shoulder_width": {
    "value": 46.2,
    "unit": "cm",
    "confidence": 0.94,
    "method": "auto",
    "accuracy_grade": "P0"
  },
  "arm_length": {
    "value": 64.8,
    "unit": "cm",
    "confidence": 0.88,
    "method": "auto",
    "accuracy_grade": "P0"
  },
  "back_length": {
    "value": 48.5,
    "unit": "cm",
    "confidence": 0.90,
    "method": "auto",
    "accuracy_grade": "P0"
  },
  "neck_girth": {
    "value": 39.4,
    "unit": "cm",
    "confidence": 0.93,
    "method": "auto",
    "accuracy_grade": "P0"
  },
  
  "bicep_girth": {
    "value": 32.1,
    "unit": "cm",
    "confidence": 0.85,
    "method": "auto",
    "accuracy_grade": "P1"
  },
  "wrist_girth": {
    "value": 17.8,
    "unit": "cm",
    "confidence": 0.87,
    "method": "auto",
    "accuracy_grade": "P1"
  },
  "inseam": {
    "value": 82.4,
    "unit": "cm",
    "confidence": 0.86,
    "method": "auto",
    "accuracy_grade": "P1"
  },
  "thigh_girth": {
    "value": 58.3,
    "unit": "cm",
    "confidence": 0.84,
    "method": "auto",
    "accuracy_grade": "P1"
  },
  "knee_girth": {
    "value": 38.9,
    "unit": "cm",
    "confidence": 0.83,
    "method": "auto",
    "accuracy_grade": "P1"
  },
  "calf_girth": {
    "value": 37.2,
    "unit": "cm",
    "confidence": 0.82,
    "method": "auto",
    "accuracy_grade": "P1"
  },
  
  "overall_confidence": 0.88,
  "figure_deviations": [],
  "mesh_url": "https://storage.eyeson.io/meshes/mesh_550e8400.ply"
}
```

**Accuracy Grades:**

| Grade | Accuracy | Measurements |
|-------|----------|--------------|
| P0 | ±0.5-1cm | Chest, Waist, Hip, Shoulder, Arm, Back, Neck |
| P1 | ±1-2cm | Bicep, Wrist, Inseam, Thigh, Knee, Calf |

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Unauthorized |
| 404 | Session or measurements not found |
| 409 | Processing not complete |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "https://api.eyeson.io/api/v1/measurements/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### Voice

#### POST /voice/synthesize

Synthesize speech from text using open source TTS.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |

**Request Body:**

```json
{
  "text": "Welcome to EYESON BodyScan. Please stand still for the scan.",
  "voice": "af_bella",              // Optional, defaults to system voice
  "speed": 1.0,                     // Optional, 0.5 to 2.0
  "stream": false                   // Optional, stream audio chunks
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "audio_url": "/api/v1/voice/audio/12345678",
  "duration_seconds": 3.5,
  "voice_used": "af_bella",
  "cached": false
}
```

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Synthesis successful |
| 400 | Invalid request |
| 413 | Text too long (max 500 chars) |
| 500 | Synthesis failed |

**Example cURL:**

```bash
curl -X POST "https://api.eyeson.io/api/v1/voice/synthesize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to EYESON BodyScan. Please stand still.",
    "voice": "af_bella",
    "speed": 1.0
  }'
```

---

#### GET /voice/prompts/{language}

Get voice prompt library for scan guidance.

**Request Headers:**

| Header | Value |
|--------|-------|
| `Accept` | `application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `language` | string | ISO 639-1 language code (e.g., "en", "es", "fr") |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `section` | string | Optional filter: "welcome", "capture", "error", etc. |

**Response (200 OK):**

```json
{
  "language": "en",
  "prompts": {
    "welcome": "Welcome to EYESON BodyScan. I'm your AI guide. In the next 90 seconds, I'll help you capture your measurements with professional accuracy. Let's begin.",
    "consent": "Your privacy matters. Your video is processed securely and deleted within 24 hours. Only your measurements are stored. Tap continue to proceed.",
    "device_setup": "First, place your phone against a wall or on a stable surface, about 6 feet from where you'll stand. Make sure the camera can see your full body.",
    "calibration": "Great! Now place the calibration card on the floor where you'll stand. It helps us measure accurately. Hold it flat and visible to the camera.",
    "positioning": "Perfect! Step back onto the card. Stand naturally with arms slightly away from your body. Look straight ahead. You should see a green skeleton overlay. When ready, the scan will begin automatically.",
    "capture_start": "Excellent position! Starting scan in 3, 2, 1. Please turn slowly to your left. Keep turning... nice and steady.",
    "capture_progress_1": "Keep turning, you're doing great. About halfway there.",
    "capture_progress_2": "Almost complete. Maintain your posture.",
    "capture_complete": "Perfect! Scan complete. Now let me process your measurements. This takes about 20 seconds.",
    "processing": "Building your 3D model... extracting measurements... nearly done.",
    "results": "All done! Your measurements are ready. You can review them on screen or have them sent to your tailor.",
    "error_lighting": "I notice the lighting is a bit dim. Try moving closer to a window or turning on more lights, then tap retry.",
    "error_position": "I can't see your full body. Please step back a bit further and make sure you're completely in the camera view.",
    "error_speed": "You turned a bit too quickly. Let's try again - turn slowly and steadily, like a rotating display.",
    "error_general": "Something didn't work quite right. Let's try that step again. Tap retry when ready."
  }
}
```

**Supported Languages:**

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish |
| `fr` | French |

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 404 | Language not available |
| 500 | Internal server error |

**Example cURL:**

```bash
curl -X GET "https://api.eyeson.io/api/v1/voice/prompts/en"
```

---

#### POST /voice/prompts/{language}/{prompt_id}/speak

Speak a predefined prompt (combines retrieval + TTS).

**Request Headers:**

| Header | Value |
|--------|-------|
| `Accept` | `audio/wav` |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `language` | string | ISO 639-1 language code |
| `prompt_id` | string | Prompt identifier (e.g., "welcome", "capture_start") |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `voice` | string | Optional voice ID |
| `speed` | number | Optional speed (0.5 to 2.0, default 1.0) |

**Response (200 OK):**

Binary audio data (WAV format)

**Response Headers:**

| Header | Value |
|--------|-------|
| `Content-Type` | `audio/wav` |
| `Content-Disposition` | `inline; filename="welcome_en.wav"` |
| `X-Prompt-Text` | First 100 chars of prompt text |

**Response Codes:**

| Code | Description |
|------|-------------|
| 200 | Audio synthesized |
| 404 | Language or prompt not found |
| 500 | Synthesis failed |

**Example cURL:**

```bash
curl -X POST "https://api.eyeson.io/api/v1/voice/prompts/en/welcome/speak?speed=1.0" \
  --output "welcome.wav"
```

---

## Error Codes

### HTTP Status Codes

| Code | Name | Description |
|------|------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no body |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid auth but insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource state conflict |
| 413 | Payload Too Large | Request body exceeds limit |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_MEASUREMENT",
    "message": "Chest girth measurement is outside valid range",
    "details": {
      "field": "measurements.Cg.value",
      "provided": 250.5,
      "valid_range": "40-200 cm"
    }
  }
}
```

---

## Rate Limiting

API endpoints are rate-limited to ensure fair usage:

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Session Creation | 20 requests | 1 minute |
| Measurements | 100 requests | 1 minute |
| File Downloads | 10 requests | 1 minute |
| Voice Synthesis | 30 requests | 1 minute |

**Rate Limit Headers:**

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed |
| `X-RateLimit-Remaining` | Requests remaining in window |
| `X-RateLimit-Reset` | Timestamp when limit resets |

---

## WebSocket API

### Real-time Session Updates

Connect to WebSocket for real-time session status updates.

**URL:** `wss://api.eyeson.io/ws/{session_id}?token={access_token}`

**Connection:**

```javascript
const ws = new WebSocket('wss://api.eyeson.io/ws/550e8400-e29b-41d4-a716-446655440000?token=eyJhbG...');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Status:', data.status, 'Progress:', data.progress_percent);
};
```

**Message Format:**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percent": 65,
  "current_stage": "3D reconstruction and measurement extraction",
  "estimated_completion": "2026-02-01T08:31:00Z"
}
```

---

## Additional Resources

- **OpenAPI Spec:** `/docs` (Swagger UI) or `/openapi.json`
- **Postman Collection:** Available at `/docs/postman-collection.json`
- **SDKs:**
  - JavaScript/TypeScript: `@samedaysuits/eyeson-sdk`
  - Python: `pip install eyeson-client`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-01 | Initial API reference |
