"""
Notification Microservice
=========================
Handles sending notifications via various channels.
"""

from fastapi import FastAPI, HTTPException, status, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone
from enum import Enum
import asyncio


# =============================================================================
# Models
# =============================================================================

class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class NotificationCreate(BaseModel):
    user_id: int
    channel: NotificationChannel
    subject: str
    message: str
    metadata: Optional[Dict] = None


class NotificationTemplate(BaseModel):
    template_id: str
    channel: NotificationChannel
    user_id: int
    variables: Dict[str, str]


# =============================================================================
# In-Memory Storage
# =============================================================================

class NotificationDatabase:
    """Simple in-memory notification storage."""
    
    def __init__(self):
        self._notifications: Dict[str, Dict] = {}
        self._counter = 0
        
        # Templates
        self._templates = {
            "welcome": {
                "subject": "Welcome to our service, {name}!",
                "message": "Hello {name}, thank you for joining us!",
            },
            "order_confirmed": {
                "subject": "Order #{order_id} Confirmed",
                "message": "Your order #{order_id} has been confirmed. Total: ${total}",
            },
            "order_shipped": {
                "subject": "Order #{order_id} Shipped",
                "message": "Your order #{order_id} has been shipped. Tracking: {tracking}",
            },
            "password_reset": {
                "subject": "Password Reset Request",
                "message": "Click here to reset your password: {reset_link}",
            },
        }
    
    def create(self, data: Dict) -> Dict:
        self._counter += 1
        notification_id = f"notif_{self._counter}"
        
        notification = {
            "id": notification_id,
            "user_id": data["user_id"],
            "channel": data["channel"],
            "subject": data["subject"],
            "message": data["message"],
            "metadata": data.get("metadata", {}),
            "status": NotificationStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sent_at": None,
        }
        self._notifications[notification_id] = notification
        return notification
    
    def get(self, notification_id: str) -> Optional[Dict]:
        return self._notifications.get(notification_id)
    
    def get_all(self) -> List[Dict]:
        return list(self._notifications.values())
    
    def get_by_user(self, user_id: int) -> List[Dict]:
        return [
            n for n in self._notifications.values()
            if n["user_id"] == user_id
        ]
    
    def update_status(self, notification_id: str, new_status: str) -> Optional[Dict]:
        if notification_id not in self._notifications:
            return None
        
        notification = self._notifications[notification_id]
        notification["status"] = new_status
        
        if new_status == NotificationStatus.SENT.value:
            notification["sent_at"] = datetime.now(timezone.utc).isoformat()
        
        return notification
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        return self._templates.get(template_id)


db = NotificationDatabase()


# =============================================================================
# Notification Senders
# =============================================================================

class NotificationSender:
    """Base notification sender."""
    
    async def send(self, notification: Dict) -> bool:
        """Send notification. Override in subclasses."""
        raise NotImplementedError


class EmailSender(NotificationSender):
    """Email notification sender."""
    
    async def send(self, notification: Dict) -> bool:
        # Simulate sending email
        print(f"📧 Sending email to user {notification['user_id']}")
        print(f"   Subject: {notification['subject']}")
        print(f"   Message: {notification['message'][:50]}...")
        await asyncio.sleep(0.5)  # Simulate network delay
        return True


class SMSSender(NotificationSender):
    """SMS notification sender."""
    
    async def send(self, notification: Dict) -> bool:
        # Simulate sending SMS
        print(f"📱 Sending SMS to user {notification['user_id']}")
        print(f"   Message: {notification['message'][:50]}...")
        await asyncio.sleep(0.3)
        return True


class PushSender(NotificationSender):
    """Push notification sender."""
    
    async def send(self, notification: Dict) -> bool:
        # Simulate push notification
        print(f"🔔 Sending push notification to user {notification['user_id']}")
        print(f"   Title: {notification['subject']}")
        await asyncio.sleep(0.2)
        return True


class WebhookSender(NotificationSender):
    """Webhook notification sender."""
    
    async def send(self, notification: Dict) -> bool:
        # Simulate webhook call
        webhook_url = notification.get("metadata", {}).get("webhook_url", "default_url")
        print(f"🌐 Sending webhook to {webhook_url}")
        await asyncio.sleep(0.4)
        return True


# Sender registry
SENDERS = {
    NotificationChannel.EMAIL: EmailSender(),
    NotificationChannel.SMS: SMSSender(),
    NotificationChannel.PUSH: PushSender(),
    NotificationChannel.WEBHOOK: WebhookSender(),
}


# =============================================================================
# App
# =============================================================================

app = FastAPI(
    title="Notification Service",
    description="Notification management microservice",
    version="1.0.0",
)


# =============================================================================
# Background Tasks
# =============================================================================

async def process_notification(notification_id: str):
    """Process and send a notification."""
    notification = db.get(notification_id)
    if not notification:
        return
    
    channel = notification["channel"]
    sender = SENDERS.get(NotificationChannel(channel))
    
    if not sender:
        db.update_status(notification_id, NotificationStatus.FAILED.value)
        return
    
    try:
        success = await sender.send(notification)
        
        if success:
            db.update_status(notification_id, NotificationStatus.SENT.value)
        else:
            db.update_status(notification_id, NotificationStatus.FAILED.value)
            
    except Exception as e:
        print(f"Error sending notification: {e}")
        db.update_status(notification_id, NotificationStatus.FAILED.value)


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "service": "Notification Service",
        "version": "1.0.0",
        "channels": [c.value for c in NotificationChannel],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "notification"}


@app.get("/notifications")
async def list_notifications(
    user_id: Optional[int] = None,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """List notifications."""
    print(f"[{x_correlation_id}] Listing notifications")
    
    if user_id:
        return db.get_by_user(user_id)
    return db.get_all()


@app.get("/notifications/{notification_id}")
async def get_notification(
    notification_id: str,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Get notification by ID."""
    notification = db.get(notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found"
        )
    return notification


@app.post("/notifications", status_code=status.HTTP_201_CREATED)
async def send_notification(
    data: NotificationCreate,
    background_tasks: BackgroundTasks,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Send a notification."""
    print(f"[{x_correlation_id}] Creating notification for user {data.user_id}")
    
    notification = db.create({
        "user_id": data.user_id,
        "channel": data.channel.value,
        "subject": data.subject,
        "message": data.message,
        "metadata": data.metadata,
    })
    
    # Process notification in background
    background_tasks.add_task(process_notification, notification["id"])
    
    return notification


@app.post("/notifications/template", status_code=status.HTTP_201_CREATED)
async def send_templated_notification(
    data: NotificationTemplate,
    background_tasks: BackgroundTasks,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Send a notification using a template."""
    print(f"[{x_correlation_id}] Sending template notification: {data.template_id}")
    
    template = db.get_template(data.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{data.template_id}' not found"
        )
    
    # Render template
    try:
        subject = template["subject"].format(**data.variables)
        message = template["message"].format(**data.variables)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing template variable: {e}"
        )
    
    notification = db.create({
        "user_id": data.user_id,
        "channel": data.channel.value,
        "subject": subject,
        "message": message,
        "metadata": {"template_id": data.template_id},
    })
    
    background_tasks.add_task(process_notification, notification["id"])
    
    return notification


@app.get("/templates")
async def list_templates():
    """List available templates."""
    return {
        template_id: {
            "id": template_id,
            "subject": template["subject"],
            "message": template["message"],
        }
        for template_id, template in db._templates.items()
    }


# =============================================================================
# Bulk Operations
# =============================================================================

@app.post("/notifications/bulk", status_code=status.HTTP_202_ACCEPTED)
async def send_bulk_notifications(
    notifications: List[NotificationCreate],
    background_tasks: BackgroundTasks,
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
):
    """Send multiple notifications at once."""
    print(f"[{x_correlation_id}] Sending {len(notifications)} bulk notifications")
    
    created = []
    for data in notifications:
        notification = db.create({
            "user_id": data.user_id,
            "channel": data.channel.value,
            "subject": data.subject,
            "message": data.message,
            "metadata": data.metadata,
        })
        background_tasks.add_task(process_notification, notification["id"])
        created.append(notification)
    
    return {
        "accepted": len(created),
        "notifications": [n["id"] for n in created],
    }


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ================================================
    Notification Service
    ================================================
    
    Endpoints:
    - GET /notifications - List notifications
    - GET /notifications/{id} - Get notification
    - POST /notifications - Send notification
    - POST /notifications/template - Send from template
    - POST /notifications/bulk - Send bulk
    - GET /templates - List templates
    
    Channels: email, sms, push, webhook
    ================================================
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8003)
