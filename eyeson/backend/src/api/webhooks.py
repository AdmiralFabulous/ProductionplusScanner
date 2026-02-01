"""
EYESON - Webhooks API Endpoints

Manage webhook subscriptions for real-time notifications.
Supports scan completion, measurement ready events.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from src.api.auth import get_current_active_user

router = APIRouter()


class WebhookEvent(str, Enum):
    """Available webhook events."""
    SCAN_STARTED = "scan.started"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"
    MEASUREMENTS_READY = "measurements.ready"
    PATTERN_GENERATED = "pattern.generated"


class WebhookCreateRequest(BaseModel):
    """Create webhook subscription request."""
    url: str = Field(..., description="Webhook endpoint URL")
    events: List[WebhookEvent] = Field(..., description="Events to subscribe to")
    secret: Optional[str] = Field(None, description="Secret for HMAC signature")
    active: bool = Field(default=True)


class WebhookResponse(BaseModel):
    """Webhook subscription response."""
    id: str
    url: str
    events: List[WebhookEvent]
    active: bool
    created_at: datetime
    last_delivery: Optional[datetime]
    last_failure: Optional[datetime]


class WebhookDelivery(BaseModel):
    """Webhook delivery record."""
    id: str
    webhook_id: str
    event: WebhookEvent
    payload: dict
    status: str  # delivered, failed, pending
    attempts: int
    delivered_at: Optional[datetime]
    error_message: Optional[str]


# Mock storage
webhooks_db = {}
deliveries_db = {}


@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: WebhookCreateRequest,
    user = Depends(get_current_active_user)
):
    """
    Create a new webhook subscription.
    
    Subscribe to events to receive real-time notifications.
    """
    import uuid
    
    webhook_id = str(uuid.uuid4())
    
    webhook = WebhookResponse(
        id=webhook_id,
        url=request.url,
        events=request.events,
        active=request.active,
        created_at=datetime.utcnow(),
        last_delivery=None,
        last_failure=None
    )
    
    webhooks_db[webhook_id] = webhook
    
    return webhook


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    user = Depends(get_current_active_user)
):
    """
    List all webhook subscriptions.
    """
    return list(webhooks_db.values())


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    user = Depends(get_current_active_user)
):
    """
    Get webhook subscription details.
    """
    if webhook_id not in webhooks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    return webhooks_db[webhook_id]


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    request: WebhookCreateRequest,
    user = Depends(get_current_active_user)
):
    """
    Update webhook subscription.
    """
    if webhook_id not in webhooks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    webhook = webhooks_db[webhook_id]
    webhook.url = request.url
    webhook.events = request.events
    webhook.active = request.active
    
    return webhook


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user = Depends(get_current_active_user)
):
    """
    Delete webhook subscription.
    """
    if webhook_id not in webhooks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    del webhooks_db[webhook_id]
    
    return {"message": "Webhook deleted successfully"}


@router.get("/webhooks/{webhook_id}/deliveries")
async def list_deliveries(
    webhook_id: str,
    limit: int = 20,
    user = Depends(get_current_active_user)
):
    """
    List delivery attempts for a webhook.
    
    View history of webhook deliveries and their status.
    """
    if webhook_id not in webhooks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    # Filter deliveries for this webhook
    webhook_deliveries = [
        d for d in deliveries_db.values()
        if d.webhook_id == webhook_id
    ]
    
    return webhook_deliveries[:limit]


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    user = Depends(get_current_active_user)
):
    """
    Send test webhook delivery.
    
    Useful for verifying endpoint configuration.
    """
    if webhook_id not in webhooks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    webhook = webhooks_db[webhook_id]
    
    # TODO: Actually send test webhook
    
    return {
        "message": "Test webhook sent",
        "webhook_id": webhook_id,
        "url": webhook.url,
        "test_payload": {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "This is a test webhook"
        }
    }


@router.post("/webhooks/{webhook_id}/replay/{delivery_id}")
async def replay_delivery(
    webhook_id: str,
    delivery_id: str,
    user = Depends(get_current_active_user)
):
    """
    Replay a failed webhook delivery.
    
    Useful for recovering from temporary failures.
    """
    if delivery_id not in deliveries_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery {delivery_id} not found"
        )
    
    delivery = deliveries_db[delivery_id]
    
    # TODO: Actually replay the delivery
    
    return {
        "message": "Delivery replayed",
        "delivery_id": delivery_id,
        "original_event": delivery.event
    }
