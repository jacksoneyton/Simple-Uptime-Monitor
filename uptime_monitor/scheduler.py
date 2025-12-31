"""
Monitoring scheduler - coordinates monitor execution and manages incidents.
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from uptime_monitor.config import get_config
from uptime_monitor.database import (
    get_session, MonitorModel, CheckResult as CheckResultModel,
    Incident, NotificationLog
)
from uptime_monitor.monitors.base import Monitor, MonitorStatus
from uptime_monitor.monitors.http import HTTPMonitor
from uptime_monitor.monitors.tcp import TCPMonitor
from uptime_monitor.monitors.ping import PingMonitor
from uptime_monitor.monitors.dns import DNSMonitor
from uptime_monitor.monitors.websocket import WebSocketMonitor
from uptime_monitor.monitors.docker_health import DockerMonitor
from uptime_monitor.monitors.push import PushMonitor
from uptime_monitor.notifications.base import Notifier, NotificationContext, NotificationEvent
from uptime_monitor.notifications.email import EmailNotifier
from uptime_monitor.notifications.discord import DiscordNotifier
from uptime_monitor.notifications.slack import SlackNotifier

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """Coordinates monitor execution and incident management"""

    MONITOR_CLASSES = {
        'http': HTTPMonitor,
        'tcp': TCPMonitor,
        'ping': PingMonitor,
        'dns': DNSMonitor,
        'websocket': WebSocketMonitor,
        'docker': DockerMonitor,
        'push': PushMonitor
    }

    NOTIFIER_CLASSES = {
        'email': EmailNotifier,
        'discord': DiscordNotifier,
        'slack': SlackNotifier
    }

    def __init__(self, max_workers: int = 10):
        """
        Initialize scheduler.

        Args:
            max_workers: Maximum number of concurrent monitor checks
        """
        self.config = get_config()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.monitors: Dict[str, Monitor] = {}
        self.notifiers: Dict[str, Notifier] = {}
        self.monitor_last_run: Dict[str, float] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Load monitors and notifiers
        self._load_monitors()
        self._load_notifiers()

    def _load_monitors(self) -> None:
        """Load monitors from configuration"""
        logger.info("Loading monitors from configuration...")

        for monitor_config in self.config.monitors:
            if not monitor_config.get('enabled', True):
                logger.info(f"Skipping disabled monitor: {monitor_config['name']}")
                continue

            try:
                monitor = self._create_monitor(monitor_config)
                self.monitors[monitor_config['name']] = monitor

                # Sync monitor to database
                self._sync_monitor_to_db(monitor_config)

            except Exception as e:
                logger.error(f"Failed to load monitor '{monitor_config['name']}': {e}")

        logger.info(f"Loaded {len(self.monitors)} monitors")

    def _create_monitor(self, monitor_config: dict) -> Monitor:
        """Create monitor instance from configuration"""
        monitor_type = monitor_config['type']
        monitor_class = self.MONITOR_CLASSES.get(monitor_type)

        if not monitor_class:
            raise ValueError(f"Unknown monitor type: {monitor_type}")

        return monitor_class(
            name=monitor_config['name'],
            config=monitor_config.get('config', {}),
            timeout=monitor_config.get('timeout', 10),
            retry_count=monitor_config.get('retry_count', 1),
            retry_delay=monitor_config.get('retry_delay', 5)
        )

    def _sync_monitor_to_db(self, monitor_config: dict) -> None:
        """Sync monitor configuration to database"""
        session = get_session()
        try:
            monitor = session.query(MonitorModel).filter_by(name=monitor_config['name']).first()

            if monitor:
                # Update existing
                monitor.type = monitor_config['type']
                monitor.enabled = monitor_config.get('enabled', True)
                monitor.group_name = monitor_config.get('group')
                monitor.interval = monitor_config.get('interval', self.config.get_default_interval())
                monitor.timeout = monitor_config.get('timeout', 10)
                monitor.retry_count = monitor_config.get('retry_count', 1)
                monitor.config = monitor_config.get('config', {})
                monitor.updated_at = datetime.utcnow()
            else:
                # Create new
                monitor = MonitorModel(
                    name=monitor_config['name'],
                    type=monitor_config['type'],
                    enabled=monitor_config.get('enabled', True),
                    group_name=monitor_config.get('group'),
                    interval=monitor_config.get('interval', self.config.get_default_interval()),
                    timeout=monitor_config.get('timeout', 10),
                    retry_count=monitor_config.get('retry_count', 1),
                    config=monitor_config.get('config', {})
                )
                session.add(monitor)

            session.commit()
        finally:
            session.close()

    def _load_notifiers(self) -> None:
        """Load notifiers from configuration"""
        logger.info("Loading notification channels...")

        for notif_config in self.config.notifications:
            try:
                notifier = self._create_notifier(notif_config)
                self.notifiers[notif_config['name']] = notifier
            except Exception as e:
                logger.error(f"Failed to load notifier '{notif_config['name']}': {e}")

        logger.info(f"Loaded {len(self.notifiers)} notification channels")

    def _create_notifier(self, notif_config: dict) -> Notifier:
        """Create notifier instance from configuration"""
        notif_type = notif_config['type']
        notifier_class = self.NOTIFIER_CLASSES.get(notif_type)

        if not notifier_class:
            raise ValueError(f"Unknown notifier type: {notif_type}")

        return notifier_class(
            name=notif_config['name'],
            config=notif_config.get('config', {}),
            enabled=notif_config.get('enabled', True)
        )

    def start(self) -> None:
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Monitor scheduler started")

    def stop(self) -> None:
        """Stop the scheduler"""
        if not self.running:
            return

        logger.info("Stopping monitor scheduler...")
        self.running = False

        if self.thread:
            self.thread.join(timeout=30)

        self.executor.shutdown(wait=True)
        logger.info("Monitor scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop"""
        logger.info("Scheduler loop starting...")

        while self.running:
            try:
                current_time = time.time()

                # Get monitor configs with their intervals
                for monitor_config in self.config.monitors:
                    if not monitor_config.get('enabled', True):
                        continue

                    monitor_name = monitor_config['name']

                    # Skip if monitor type is 'push' (passive monitoring)
                    if monitor_config['type'] == 'push':
                        # Push monitors still need to be checked for deadline expiration
                        pass

                    # Check if it's time to run this monitor
                    interval = monitor_config.get('interval', self.config.get_default_interval())
                    last_run = self.monitor_last_run.get(monitor_name, 0)

                    if current_time - last_run >= interval:
                        # Submit monitor check to thread pool
                        self.executor.submit(self._run_monitor_check, monitor_name, monitor_config)
                        self.monitor_last_run[monitor_name] = current_time

                # Sleep for 1 second (scheduler resolution)
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)  # Back off on error

        logger.info("Scheduler loop ended")

    def _run_monitor_check(self, monitor_name: str, monitor_config: dict) -> None:
        """
        Run a single monitor check.

        Args:
            monitor_name: Monitor name
            monitor_config: Monitor configuration
        """
        monitor = self.monitors.get(monitor_name)
        if not monitor:
            logger.error(f"Monitor '{monitor_name}' not found")
            return

        try:
            # Perform check with retry logic
            result = monitor.check_with_retry()

            # Save result to database
            self._save_check_result(monitor_name, result)

            # Check for state changes and handle incidents
            self._handle_state_change(monitor_name, monitor_config, result)

        except Exception as e:
            logger.error(f"Failed to run check for monitor '{monitor_name}': {e}")

    def _save_check_result(self, monitor_name: str, result) -> None:
        """Save check result to database"""
        session = get_session()
        try:
            # Get monitor from database
            monitor = session.query(MonitorModel).filter_by(name=monitor_name).first()
            if not monitor:
                logger.error(f"Monitor '{monitor_name}' not found in database")
                return

            # Create check result record
            check_result = CheckResultModel(
                monitor_id=monitor.id,
                timestamp=result.timestamp,
                status=result.status.value,
                response_time=result.response_time,
                status_code=result.status_code,
                error_message=result.error_message,
                metadata=result.metadata
            )

            session.add(check_result)
            session.commit()

        finally:
            session.close()

    def _handle_state_change(self, monitor_name: str, monitor_config: dict, result) -> None:
        """Handle monitor state changes and incidents"""
        session = get_session()
        try:
            # Get monitor from database
            monitor = session.query(MonitorModel).filter_by(name=monitor_name).first()
            if not monitor:
                return

            # Get last check result (before current one)
            last_result = session.query(CheckResultModel)\
                .filter_by(monitor_id=monitor.id)\
                .order_by(CheckResultModel.timestamp.desc())\
                .offset(1)\
                .first()

            current_status = result.status
            previous_status = MonitorStatus(last_result.status) if last_result else None

            # Check if state changed
            if previous_status and previous_status != current_status:
                logger.info(f"Monitor '{monitor_name}' state changed: {previous_status.value} -> {current_status.value}")

                # Handle state transitions
                if current_status == MonitorStatus.DOWN and previous_status == MonitorStatus.UP:
                    # Service went down - create incident
                    self._create_incident(session, monitor, result)
                    self._send_notifications(monitor_name, monitor_config, NotificationEvent.DOWN, result)

                elif current_status == MonitorStatus.UP and previous_status == MonitorStatus.DOWN:
                    # Service recovered - close incident
                    self._close_incident(session, monitor, result)
                    self._send_notifications(monitor_name, monitor_config, NotificationEvent.UP, result)

        finally:
            session.close()

    def _create_incident(self, session, monitor: MonitorModel, result) -> None:
        """Create a new incident"""
        incident = Incident(
            monitor_id=monitor.id,
            started_at=result.timestamp,
            notified=False
        )
        session.add(incident)
        session.commit()

        logger.warning(f"Incident created for monitor '{monitor.name}' (ID: {incident.id})")

    def _close_incident(self, session, monitor: MonitorModel, result) -> None:
        """Close an ongoing incident"""
        # Find ongoing incident
        incident = session.query(Incident)\
            .filter_by(monitor_id=monitor.id, ended_at=None)\
            .order_by(Incident.started_at.desc())\
            .first()

        if incident:
            incident.ended_at = result.timestamp
            incident.duration = int((incident.ended_at - incident.started_at).total_seconds())
            session.commit()

            logger.info(f"Incident {incident.id} closed for monitor '{monitor.name}' (duration: {incident.duration}s)")

    def _send_notifications(self, monitor_name: str, monitor_config: dict, event: NotificationEvent, result) -> None:
        """Send notifications for a monitor event"""
        # Check if this event should trigger notifications
        alert_on = monitor_config.get('alert_on', ['down', 'up'])
        if event.value not in alert_on:
            return

        # Get notification channel names
        notification_names = monitor_config.get('notifications', [])
        if not notification_names:
            return

        # Create notification context
        context = NotificationContext(
            monitor_name=monitor_name,
            event_type=event,
            status=result.status.value,
            message=result.error_message or f"Monitor is {result.status.value}",
            timestamp=result.timestamp,
            metadata=result.metadata or {}
        )

        # Send to each configured channel
        for notif_name in notification_names:
            notifier = self.notifiers.get(notif_name)
            if not notifier:
                logger.warning(f"Notifier '{notif_name}' not found")
                continue

            # Send notification (with retry)
            success = notifier.send_with_retry(context)

            # Log notification attempt
            self._log_notification(monitor_name, notif_name, notifier.config.get('type', 'unknown'), event, success)

    def _log_notification(self, monitor_name: str, notif_name: str, notif_type: str, event: NotificationEvent, success: bool) -> None:
        """Log notification attempt to database"""
        session = get_session()
        try:
            monitor = session.query(MonitorModel).filter_by(name=monitor_name).first()
            if not monitor:
                return

            # Get current incident if any
            incident = session.query(Incident)\
                .filter_by(monitor_id=monitor.id, ended_at=None)\
                .order_by(Incident.started_at.desc())\
                .first()

            log_entry = NotificationLog(
                incident_id=incident.id if incident else None,
                monitor_id=monitor.id,
                notification_type=notif_type,
                notification_name=notif_name,
                event_type=event.value,
                success=success
            )

            session.add(log_entry)
            session.commit()

        finally:
            session.close()
