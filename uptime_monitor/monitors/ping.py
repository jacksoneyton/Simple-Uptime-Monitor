"""
ICMP Ping monitor.
"""

from icmplib import ping as icmp_ping, NameLookupError, ICMPLibError
from uptime_monitor.monitors.base import Monitor, MonitorResult, MonitorStatus
import logging

logger = logging.getLogger(__name__)


class PingMonitor(Monitor):
    """ICMP Ping monitor"""

    def check(self) -> MonitorResult:
        """
        Perform ICMP ping check.

        Returns:
            MonitorResult with status and response time
        """
        host = self.config.get('host')
        packet_count = self.config.get('packet_count', 3)
        packet_size = self.config.get('packet_size', 56)

        if not host:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message="No host configured"
            )

        try:
            # Perform ping
            result = icmp_ping(
                address=host,
                count=packet_count,
                interval=0.2,
                timeout=self.timeout,
                payload_size=packet_size,
                privileged=False  # Use unprivileged mode (works without root)
            )

            # Check if any packets were received
            if result.packets_received > 0:
                return MonitorResult(
                    status=MonitorStatus.UP,
                    response_time=result.avg_rtt,  # Average RTT in milliseconds
                    metadata={
                        'host': host,
                        'packets_sent': result.packets_sent,
                        'packets_received': result.packets_received,
                        'packet_loss': result.packet_loss,
                        'min_rtt': result.min_rtt,
                        'avg_rtt': result.avg_rtt,
                        'max_rtt': result.max_rtt,
                        'jitter': result.jitter
                    }
                )
            else:
                return MonitorResult(
                    status=MonitorStatus.DOWN,
                    error_message=f"No packets received from {host} (100% packet loss)"
                )

        except NameLookupError:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"DNS resolution failed for {host}"
            )
        except ICMPLibError as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"ICMP error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Ping monitor '{self.name}' failed: {e}")
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Ping failed: {str(e)}"
            )
