"""
EYESON - Scan Session API Endpoints

Manages the lifecycle of body scan sessions including:
- Session creation
- Video/image upload
- Calibration
- Status tracking
- Results retrieval
"""

import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from pydantic import BaseModel, Field

from src.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store (replace with Redis in production)
sessions_store = {}


class ScanMode(str, Enum):
    """Scan capture modes."""
    VIDEO = "video"
    DUAL_IMAGE = "dual_image"


class SessionStatus(str, Enum):
    """Session status states."""
    INITIATED = "initiated"
    CALIBRATING = "calibrating"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class CalibrationData(BaseModel):
    """Calibration data from ArUco marker detection."""
    marker_size_cm: float = Field(default=14.0)
    scale_factor: float
    marker_corners: Optional[List[List[float]]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    height_estimate_cm: Optional[float] = None


class SessionCreateRequest(BaseModel):
    """Create scan session request."""
    user_id: Optional[str] = None
    scan_mode: ScanMode = Field(default=ScanMode.VIDEO)
    language: str = Field(default="en", pattern="^[a-z]{2}$")
    device_info: Optional[dict] = None


class SessionResponse(BaseModel):
    """Session response."""
    session_id: str
    status: SessionStatus
    scan_mode: ScanMode
    language: str
    websocket_url: str
    expires_at: datetime
    created_at: datetime


class SessionDetailResponse(SessionResponse):
    """Detailed session response."""
    calibration: Optional[CalibrationData] = None
    video_url: Optional[str] = None
    progress_percent: int = 0
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreateRequest):
    """
    Initialize a new scan session.
    
    Creates a session record and returns session ID for subsequent operations.
    """
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    session_data = {
        "session_id": session_id,
        "user_id": request.user_id,
        "status": SessionStatus.INITIATED,
        "scan_mode": request.scan_mode,
        "language": request.language,
        "device_info": request.device_info,
        "websocket_url": f"wss://api.eyeson.io/ws/{session_id}",
        "created_at": now,
        "expires_at": now + timedelta(hours=1),
        "calibration": None,
        "video_url": None,
        "progress_percent": 0,
        "measurements": None,
        "error_message": None,
    }
    
    sessions_store[session_id] = session_data
    
    logger.info(f"Session created: {session_id} (mode: {request.scan_mode}, lang: {request.language})")
    
    return SessionResponse(
        session_id=session_id,
        status=SessionStatus.INITIATED,
        scan_mode=request.scan_mode,
        language=request.language,
        websocket_url=session_data["websocket_url"],
        expires_at=session_data["expires_at"],
        created_at=session_data["created_at"]
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """
    Get session details and current status.
    """
    if session_id not in sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = sessions_store[session_id]
    
    # Check if expired
    if datetime.utcnow() > session["expires_at"]:
        session["status"] = SessionStatus.EXPIRED
    
    return SessionDetailResponse(
        session_id=session["session_id"],
        status=session["status"],
        scan_mode=session["scan_mode"],
        language=session["language"],
        websocket_url=session["websocket_url"],
        expires_at=session["expires_at"],
        created_at=session["created_at"],
        calibration=session.get("calibration"),
        video_url=session.get("video_url"),
        progress_percent=session.get("progress_percent", 0),
        error_message=session.get("error_message")
    )


@router.post("/sessions/{session_id}/calibrate")
async def calibrate_session(
    session_id: str,
    marker_image: UploadFile = File(..., description="Image containing ArUco marker"),
    height_cm: Optional[float] = Form(None, description="User height in cm for validation")
):
    """
    Submit calibration data for a session.
    
    Upload an image containing the ArUco calibration marker.
    System will detect marker and calculate scale factor.
    """
    if session_id not in sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = sessions_store[session_id]
    
    if session["status"] != SessionStatus.INITIATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not in INITIATED state (current: {session['status']})"
        )
    
    # TODO: Implement actual ArUco marker detection
    # For now, return mock calibration data
    
    calibration = CalibrationData(
        marker_size_cm=settings.calibration_marker_size_cm,
        scale_factor=0.035,  # pixels to cm
        confidence=0.95,
        height_estimate_cm=height_cm or 175.0
    )
    
    session["calibration"] = calibration.model_dump()
    session["status"] = SessionStatus.CALIBRATING
    
    logger.info(f"Session {session_id} calibrated: scale={calibration.scale_factor:.4f}")
    
    return {
        "session_id": session_id,
        "calibration": calibration,
        "status": session["status"],
        "message": "Calibration successful. Ready for capture."
    }


@router.post("/sessions/{session_id}/upload")
async def upload_scan_media(
    session_id: str,
    background_tasks: BackgroundTasks,
    video: Optional[UploadFile] = File(None, description="Scan video (for video mode)"),
    front_image: Optional[UploadFile] = File(None, description="Front image (for dual-image mode)"),
    side_image: Optional[UploadFile] = File(None, description="Side image (for dual-image mode)")
):
    """
    Upload scan media (video or images).
    
    For VIDEO mode: Upload video file
    For DUAL_IMAGE mode: Upload front and side images
    """
    if session_id not in sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = sessions_store[session_id]
    
    if session["status"] != SessionStatus.CALIBRATING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session must be in CALIBRATING state (current: {session['status']})"
        )
    
    # Validate upload based on scan mode
    if session["scan_mode"] == ScanMode.VIDEO:
        if not video:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video file required for VIDEO mode"
            )
        # TODO: Validate and store video
        session["video_url"] = f"s3://{settings.storage_bucket}/videos/{session_id}.mp4"
        
    elif session["scan_mode"] == ScanMode.DUAL_IMAGE:
        if not front_image or not side_image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both front_image and side_image required for DUAL_IMAGE mode"
            )
        # TODO: Validate and store images
        session["video_url"] = f"s3://{settings.storage_bucket}/images/{session_id}/"
    
    # Update status and start processing
    session["status"] = SessionStatus.CAPTURING
    
    # Trigger async processing
    background_tasks.add_task(_process_scan, session_id)
    
    logger.info(f"Session {session_id} media uploaded, processing started")
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "message": "Media uploaded successfully. Processing started.",
        "estimated_seconds": 30
    }


@router.get("/sessions/{session_id}/progress")
async def get_session_progress(session_id: str):
    """
    Get current processing progress for a session.
    
    Returns progress percentage and estimated completion time.
    """
    if session_id not in sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = sessions_store[session_id]
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "progress_percent": session.get("progress_percent", 0),
        "estimated_completion": session.get("estimated_completion"),
        "current_stage": _get_stage_description(session["status"])
    }


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(session_id: str):
    """
    Cancel an active session.
    
    Stops processing and cleans up resources.
    """
    if session_id not in sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = sessions_store[session_id]
    
    # Can only cancel active sessions
    if session["status"] in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.EXPIRED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel session in {session['status']} state"
        )
    
    session["status"] = SessionStatus.FAILED
    session["error_message"] = "Cancelled by user"
    
    logger.info(f"Session {session_id} cancelled")
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "message": "Session cancelled successfully"
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and all associated data.
    
    Removes session record and triggers cleanup of stored media.
    """
    if session_id not in sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # TODO: Trigger async cleanup of stored files
    
    del sessions_store[session_id]
    
    logger.info(f"Session {session_id} deleted")
    
    return {
        "session_id": session_id,
        "message": "Session deleted successfully"
    }


async def _process_scan(session_id: str):
    """
    Background task to process scan media.
    
    This would integrate with the ML service in production.
    """
    if session_id not in sessions_store:
        return
    
    session = sessions_store[session_id]
    
    try:
        # Update status
        session["status"] = SessionStatus.PROCESSING
        session["progress_percent"] = 0
        
        # Simulate processing stages
        # In production, this would call the ML service
        
        # Stage 1: Video preprocessing (0-20%)
        session["progress_percent"] = 10
        await asyncio.sleep(2)
        
        # Stage 2: Frame extraction (20-40%)
        session["progress_percent"] = 30
        await asyncio.sleep(3)
        
        # Stage 3: 3D reconstruction (40-70%)
        session["progress_percent"] = 50
        await asyncio.sleep(5)
        
        # Stage 4: Measurement extraction (70-90%)
        session["progress_percent"] = 80
        await asyncio.sleep(4)
        
        # Stage 5: Results compilation (90-100%)
        session["progress_percent"] = 100
        session["status"] = SessionStatus.COMPLETED
        
        logger.info(f"Session {session_id} processing completed")
        
    except Exception as e:
        logger.error(f"Session {session_id} processing failed: {e}")
        session["status"] = SessionStatus.FAILED
        session["error_message"] = str(e)


def _get_stage_description(status: SessionStatus) -> str:
    """Get human-readable description for session status."""
    descriptions = {
        SessionStatus.INITIATED: "Session initialized, waiting for calibration",
        SessionStatus.CALIBRATING: "Calibration in progress",
        SessionStatus.CAPTURING: "Media uploaded, starting processing",
        SessionStatus.PROCESSING: "3D reconstruction and measurement extraction",
        SessionStatus.COMPLETED: "Scan complete, results available",
        SessionStatus.FAILED: "Processing failed",
        SessionStatus.EXPIRED: "Session expired"
    }
    return descriptions.get(status, "Unknown")


