"""
Base monitor class that all monitor implementations inherit from.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


class MonitorStatus(Enum):
    """Monitor status enumeration"""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class MonitorResult:
    """Result of a monitor check"""
    status: MonitorStatus
    response_time: Optional[float] = None  # milliseconds
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'status': self.status.value,
            'response_time': self.response_time,
            'status_code': self.status_code,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class Monitor(ABC):
    """
    Abstract base class for all monitor types.

    Subclasses must implement the check() method which performs
    the actual monitoring check and returns a MonitorResult.
    """

    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        timeout: int = 10,
        retry_count: int = 1,
        retry_delay: int = 5
    ):
        """
        Initialize monitor.

        Args:
            name: Monitor name
            config: Monitor-specific configuration
            timeout: Check timeout in seconds
            retry_count: Number of retries on failure
            retry_delay: Delay between retries in seconds
        """
        self.name = name
        self.config = config
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    @abstractmethod
    def check(self) -> MonitorResult:
        """
        Perform the monitor check.

        This method must be implemented by all monitor subclasses.

        Returns:
            MonitorResult with status, response time, and metadata
        """
        pass

    def check_with_retry(self) -> MonitorResult:
        """
        Perform check with retry logic.

        Returns:
            MonitorResult from the check (last attempt if all fail)
        """
        last_result = None

        for attempt in range(1, self.retry_count + 1):
            try:
                logger.debug(f"Monitor '{self.name}': Attempt {attempt}/{self.retry_count}")
                result = self.check()

                # If check succeeded, return immediately
                if result.status == MonitorStatus.UP:
                    return result

                # Store result for potential return
                last_result = result

                # If not the last attempt, wait before retrying
                if attempt < self.retry_count:
                    logger.debug(f"Monitor '{self.name}': Check failed, retrying in {self.retry_delay}s")
                    time.sleep(self.retry_delay)

            except Exception as e:
                logger.error(f"Monitor '{self.name}': Check failed with exception: {e}")
                last_result = MonitorResult(
                    status=MonitorStatus.DOWN,
                    error_message=str(e)
                )

                # If not the last attempt, wait before retrying
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay)

        # Return the last result (either failed check or exception)
        return last_result if last_result else MonitorResult(
            status=MonitorStatus.UNKNOWN,
            error_message="No result from check"
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"
