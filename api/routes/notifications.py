"""
Notifications API Routes
Endpoints for viewing and managing trade notifications
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from services.notifications import get_notification_service, NotificationType

router = APIRouter()


class TestNotificationRequest(BaseModel):
    """Request model for sending test notification"""
    email: Optional[str] = None
    message: Optional[str] = "This is a test notification from ChartSense"


@router.get("/")
async def get_notifications(limit: int = Query(default=50, ge=1, le=200)):
    """
    Get notification history.

    Returns the most recent notifications sent by the bot.
    """
    service = get_notification_service()
    history = service.get_history(limit=limit)

    return {
        "notifications": history,
        "count": len(history),
        "email_enabled": service.email_enabled,
    }


@router.get("/status")
async def get_notification_status():
    """
    Get notification service status.

    Shows whether email notifications are configured and enabled.
    """
    service = get_notification_service()

    return {
        "email_enabled": service.email_enabled,
        "smtp_configured": bool(service.smtp_user),
        "recipients_configured": len([e for e in service.to_emails if e]) > 0,
        "history_count": len(service._history),
    }


@router.post("/test")
async def send_test_notification(request: TestNotificationRequest = None):
    """
    Send a test notification to verify configuration.

    Use this to test that email notifications are working.
    """
    service = get_notification_service()

    if not service.email_enabled:
        raise HTTPException(
            status_code=400,
            detail="Email notifications not configured. Set SMTP_USER, SMTP_PASSWORD, and NOTIFICATION_TO_EMAILS environment variables."
        )

    from services.notifications import Notification

    message = request.message if request else "This is a test notification from ChartSense"

    notification = Notification(
        type=NotificationType.ALERT,
        title="Test Notification",
        message=message,
        data={
            "test": True,
            "timestamp": "now"
        }
    )

    success = service.send(notification)

    if success:
        return {
            "success": True,
            "message": "Test notification sent successfully",
            "recipients": [e for e in service.to_emails if e]
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send test notification. Check SMTP settings."
        )


@router.delete("/history")
async def clear_notification_history():
    """
    Clear notification history.
    """
    service = get_notification_service()
    service._history = []

    return {
        "success": True,
        "message": "Notification history cleared"
    }
