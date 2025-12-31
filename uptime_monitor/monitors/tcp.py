"""
TCP port connectivity monitor.
"""

import socket
import time
from uptime_monitor.monitors.base import Monitor, MonitorResult, MonitorStatus
import logging

logger = logging.getLogger(__name__)


class TCPMonitor(Monitor):
    """TCP port connectivity monitor"""

    def check(self) -> MonitorResult:
        """
        Perform TCP port check.

        Returns:
            MonitorResult with status and response time
        """
        host = self.config.get('host')
        port = self.config.get('port')

        if not host or not port:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message="Missing host or port configuration"
            )

        start_time = time.time()

        try:
            # Create socket and attempt connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            result = sock.connect_ex((host, port))
            response_time = (time.time() - start_time) * 1000

            sock.close()

            if result == 0:
                # Connection successful
                return MonitorResult(
                    status=MonitorStatus.UP,
                    response_time=response_time,
                    metadata={
                        'host': host,
                        'port': port
                    }
                )
            else:
                # Connection failed
                return MonitorResult(
                    status=MonitorStatus.DOWN,
                    response_time=response_time,
                    error_message=f"Connection to {host}:{port} failed (error code: {result})"
                )

        except socket.timeout:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                response_time=(time.time() - start_time) * 1000,
                error_message=f"Connection to {host}:{port} timed out after {self.timeout}s"
            )
        except socket.gaierror as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"DNS resolution failed for {host}: {str(e)}"
            )
        except Exception as e:
            logger.error(f"TCP monitor '{self.name}' failed: {e}")
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"TCP check failed: {str(e)}"
            )
