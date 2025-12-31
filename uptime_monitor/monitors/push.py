"""
Push-based passive monitor.
"""

from datetime import datetime, timedelta
from uptime_monitor.monitors.base import Monitor, MonitorResult, MonitorStatus
from uptime_monitor.database import get_session, PushMonitor as PushMonitorModel
import logging

logger = logging.getLogger(__name__)


class PushMonitor(Monitor):
    """
    Push-based passive monitor.

    This monitor doesn't actively check anything. Instead, it waits for
    external systems to push status updates via the API. If no push is
    received within the expected interval + grace period, the monitor
    is marked as down.
    """

    def check(self) -> MonitorResult:
        """
        Check if push monitor has received recent updates.

        Returns:
            MonitorResult based on last push time
        """
        expected_interval = self.config.get('expected_interval', 86400)  # Default 24 hours
        grace_period = self.config.get('grace_period', 3600)  # Default 1 hour
        require_payload = self.config.get('require_payload', False)

        try:
            session = get_session()

            # Find push monitor record by name
            # Note: This requires the monitor to be in the database first
            from uptime_monitor.database import MonitorModel

            monitor = session.query(MonitorModel).filter_by(name=self.name).first()

            if not monitor:
                return MonitorResult(
                    status=MonitorStatus.UNKNOWN,
                    error_message="Monitor not found in database"
                )

            push_monitor = session.query(PushMonitorModel).filter_by(
                monitor_id=monitor.id
            ).first()

            if not push_monitor:
                # Push monitor not initialized yet - this is the first check
                # Initialize it now
                import secrets
                push_monitor = PushMonitorModel(
                    monitor_id=monitor.id,
                    secret_key=secrets.token_urlsafe(32),
                    expected_interval=expected_interval,
                    grace_period=grace_period
                )
                session.add(push_monitor)
                session.commit()

                return MonitorResult(
                    status=MonitorStatus.UNKNOWN,
                    error_message="Push monitor initialized, waiting for first push",
                    metadata={
                        'secret_key': push_monitor.secret_key,
                        'push_url': f'/api/push/{monitor.id}/{push_monitor.secret_key}'
                    }
                )

            # Check if push is overdue
            if not push_monitor.last_push_at:
                # No push received yet
                return MonitorResult(
                    status=MonitorStatus.UNKNOWN,
                    error_message="No push received yet",
                    metadata={
                        'secret_key': push_monitor.secret_key,
                        'push_url': f'/api/push/{monitor.id}/{push_monitor.secret_key}'
                    }
                )

            # Calculate deadline
            deadline = push_monitor.last_push_at + timedelta(seconds=expected_interval + grace_period)
            now = datetime.utcnow()

            if now > deadline:
                # Push is overdue
                overdue_seconds = int((now - deadline).total_seconds())
                return MonitorResult(
                    status=MonitorStatus.DOWN,
                    error_message=f"No push received in {expected_interval + grace_period}s (overdue by {overdue_seconds}s)",
                    metadata={
                        'last_push_at': push_monitor.last_push_at.isoformat(),
                        'deadline': deadline.isoformat(),
                        'overdue_seconds': overdue_seconds
                    }
                )
            else:
                # Push is on time
                time_until_deadline = int((deadline - now).total_seconds())
                return MonitorResult(
                    status=MonitorStatus.UP,
                    metadata={
                        'last_push_at': push_monitor.last_push_at.isoformat(),
                        'next_deadline': deadline.isoformat(),
                        'time_until_deadline_seconds': time_until_deadline
                    }
                )

        except Exception as e:
            logger.error(f"Push monitor '{self.name}' check failed: {e}")
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Push monitor check failed: {str(e)}"
            )
        finally:
            if 'session' in locals():
                session.close()
