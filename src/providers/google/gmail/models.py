"""Gmail data models."""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class GmailAttachment:
    """Gmail attachment model."""
    filename: str
    mime_type: str
    attachment_id: str
    size: Optional[int] = None
    data: Optional[bytes] = None


@dataclass
class GmailMessage:
    """Gmail message model."""
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    body: str
    date: Optional[datetime] = None
    attachments: List[GmailAttachment] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.attachments is None:
            self.attachments = [] 