"""
Docker container health monitor.
"""

import time
from typing import Optional
import docker
from docker.errors import DockerException, NotFound, APIError
from uptime_monitor.monitors.base import Monitor, MonitorResult, MonitorStatus
import logging

logger = logging.getLogger(__name__)


class DockerMonitor(Monitor):
    """Docker container health monitor"""

    def check(self) -> MonitorResult:
        """
        Perform Docker container health check.

        Returns:
            MonitorResult with status and container info
        """
        socket_path = self.config.get('socket', '/var/run/docker.sock')
        container_name = self.config.get('container_name')
        container_id = self.config.get('container_id')
        expect_status = self.config.get('expect_status', 'running')
        check_health = self.config.get('check_health', False)

        if not container_name and not container_id:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message="No container_name or container_id configured"
            )

        start_time = time.time()

        try:
            # Connect to Docker
            if socket_path.startswith('tcp://'):
                client = docker.DockerClient(base_url=socket_path)
            else:
                client = docker.DockerClient(base_url=f'unix://{socket_path}')

            # Get container
            identifier = container_id if container_id else container_name
            container = client.containers.get(identifier)

            response_time = (time.time() - start_time) * 1000

            # Get container status
            container.reload()  # Refresh container info
            actual_status = container.status

            # Check if status matches expected
            if actual_status != expect_status:
                return MonitorResult(
                    status=MonitorStatus.DOWN,
                    response_time=response_time,
                    error_message=f"Container status is '{actual_status}', expected '{expect_status}'"
                )

            # Check Docker health status if configured
            if check_health:
                health_status = container.attrs.get('State', {}).get('Health', {}).get('Status')

                if health_status and health_status != 'healthy':
                    return MonitorResult(
                        status=MonitorStatus.DOWN,
                        response_time=response_time,
                        error_message=f"Container health check status is '{health_status}' (expected 'healthy')"
                    )

            # All checks passed
            return MonitorResult(
                status=MonitorStatus.UP,
                response_time=response_time,
                metadata={
                    'container_name': container.name,
                    'container_id': container.short_id,
                    'status': actual_status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown'
                }
            )

        except NotFound:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Container '{identifier}' not found"
            )
        except APIError as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Docker API error: {str(e)}"
            )
        except DockerException as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Docker error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Docker monitor '{self.name}' failed: {e}")
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Docker check failed: {str(e)}"
            )
