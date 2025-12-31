"""
Base notifier class that all notification implementations inherit from.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotificationEvent(Enum):
    """Types of notification events"""
    DOWN = "down"              # Service went down
    UP = "up"                  # Service recovered
    SSL_EXPIRE = "ssl_expire"  # SSL certificate expiring soon
    DEGRADED = "degraded"      # Service is degraded


@dataclass
class NotificationContext:
    """Context information for a notification"""
    monitor_name: str
    event_type: NotificationEvent
    status: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]
    incident_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'monitor_name': self.monitor_name,
            'event_type': self.event_type.value,
            'status': self.status,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'incident_id': self.incident_id
        }


class Notifier(ABC):
    """
    Abstract base class for all notification channels.

    Subclasses must implement the send() method which sends
    the notification through the specific channel.
    """

    def __init__(self, name: str, config: Dict[str, Any], enabled: bool = True):
        """
        Initialize notifier.

        Args:
            name: Notifier name (from config)
            config: Notifier-specific configuration
            enabled: Whether notifier is enabled
        """
        self.name = name
        self.config = config
        self.enabled = enabled

    @abstractmethod
    def send(self, context: NotificationContext) -> bool:
        """
        Send notification.

        Args:
            context: Notification context with all relevant information

        Returns:
            True if notification was sent successfully, False otherwise
        """
        pass

    def send_with_retry(self, context: NotificationContext, retry_count: int = 3) -> bool:
        """
        Send notification with retry logic.

        Args:
            context: Notification context
            retry_count: Number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Notifier '{self.name}' is disabled, skipping")
            return False

        for attempt in range(1, retry_count + 1):
            try:
                logger.info(f"Sending notification via '{self.name}' (attempt {attempt}/{retry_count})")
                success = self.send(context)

                if success:
                    logger.info(f"Notification sent successfully via '{self.name}'")
                    return True
                else:
                    logger.warning(f"Notification via '{self.name}' failed (attempt {attempt}/{retry_count})")

            except Exception as e:
                logger.error(f"Notification via '{self.name}' failed with exception: {e}")

            # Don't sleep after the last attempt
            if attempt < retry_count:
                import time
                time.sleep(2)  # Wait 2 seconds between retries

        logger.error(f"All notification attempts via '{self.name}' failed")
        return False

    def format_message(self, context: NotificationContext) -> str:
        """
        Format a basic notification message.

        Can be overridden by subclasses for custom formatting.

        Args:
            context: Notification context

        Returns:
            Formatted message string
        """
        event_emoji = {
            NotificationEvent.DOWN: "🔴",
            NotificationEvent.UP: "🟢",
            NotificationEvent.SSL_EXPIRE: "⚠️",
            NotificationEvent.DEGRADED: "🟡"
        }

        emoji = event_emoji.get(context.event_type, "ℹ️")

        message = f"{emoji} **{context.monitor_name}** - {context.event_type.value.upper()}\n\n"
        message += f"{context.message}\n\n"
        message += f"Time: {context.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

        if context.metadata:
            message += "\nDetails:\n"
            for key, value in context.metadata.items():
                message += f"- {key}: {value}\n"

        return message

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', enabled={self.enabled})>"
