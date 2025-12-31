"""
WebSocket monitor.
"""

import time
import json
from websocket import create_connection, WebSocketException, WebSocketTimeoutException
from uptime_monitor.monitors.base import Monitor, MonitorResult, MonitorStatus
import logging

logger = logging.getLogger(__name__)


class WebSocketMonitor(Monitor):
    """WebSocket connection monitor"""

    def check(self) -> MonitorResult:
        """
        Perform WebSocket connection check.

        Returns:
            MonitorResult with status and response time
        """
        url = self.config.get('url')
        send_message = self.config.get('send_message')
        expect_response = self.config.get('expect_response')
        response_timeout = self.config.get('response_timeout', 5)

        if not url:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message="No WebSocket URL configured"
            )

        start_time = time.time()

        try:
            # Create WebSocket connection
            ws = create_connection(url, timeout=self.timeout)
            connection_time = (time.time() - start_time) * 1000

            # If message exchange is configured
            if send_message:
                # Send message
                ws.send(send_message)

                if expect_response:
                    # Wait for response
                    ws.settimeout(response_timeout)
                    response = ws.recv()

                    # Validate response
                    if expect_response not in response:
                        ws.close()
                        return MonitorResult(
                            status=MonitorStatus.DOWN,
                            response_time=connection_time,
                            error_message=f"Unexpected WebSocket response. Expected '{expect_response}', got '{response}'"
                        )

            ws.close()
            total_time = (time.time() - start_time) * 1000

            return MonitorResult(
                status=MonitorStatus.UP,
                response_time=total_time,
                metadata={
                    'url': url,
                    'connection_time': connection_time
                }
            )

        except WebSocketTimeoutException:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                response_time=(time.time() - start_time) * 1000,
                error_message=f"WebSocket connection timed out after {self.timeout}s"
            )
        except WebSocketException as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"WebSocket error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"WebSocket monitor '{self.name}' failed: {e}")
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"WebSocket check failed: {str(e)}"
            )
