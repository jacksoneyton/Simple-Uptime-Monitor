"""
DNS resolution monitor.
"""

import time
import dns.resolver
from dns.exception import DNSException, Timeout
from uptime_monitor.monitors.base import Monitor, MonitorResult, MonitorStatus
import logging

logger = logging.getLogger(__name__)


class DNSMonitor(Monitor):
    """DNS resolution monitor"""

    def check(self) -> MonitorResult:
        """
        Perform DNS resolution check.

        Returns:
            MonitorResult with status and response time
        """
        hostname = self.config.get('hostname')
        resolver_ip = self.config.get('resolver', '8.8.8.8')
        record_type = self.config.get('record_type', 'A')
        expected_values = self.config.get('expected_values', [])
        expected_contains = self.config.get('expected_contains')
        match_mode = self.config.get('match_mode', 'any')  # any, all, exact

        if not hostname:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message="No hostname configured"
            )

        start_time = time.time()

        try:
            # Create resolver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [resolver_ip]
            resolver.timeout = self.timeout
            resolver.lifetime = self.timeout

            # Perform DNS query
            answers = resolver.resolve(hostname, record_type)
            response_time = (time.time() - start_time) * 1000

            # Extract resolved values
            resolved_values = []
            for rdata in answers:
                if record_type == 'MX':
                    resolved_values.append(str(rdata.exchange))
                elif record_type == 'TXT':
                    resolved_values.append(str(rdata))
                else:
                    resolved_values.append(str(rdata))

            # Validate results if expected values are configured
            if expected_values:
                is_valid = self._validate_values(resolved_values, expected_values, match_mode)
                if not is_valid:
                    return MonitorResult(
                        status=MonitorStatus.DOWN,
                        response_time=response_time,
                        error_message=f"DNS resolution mismatch. Expected {expected_values}, got {resolved_values}"
                    )

            # Check if any resolved value contains expected string
            if expected_contains:
                contains_found = any(expected_contains in val for val in resolved_values)
                if not contains_found:
                    return MonitorResult(
                        status=MonitorStatus.DOWN,
                        response_time=response_time,
                        error_message=f"None of the resolved values contain '{expected_contains}'"
                    )

            return MonitorResult(
                status=MonitorStatus.UP,
                response_time=response_time,
                metadata={
                    'hostname': hostname,
                    'record_type': record_type,
                    'resolver': resolver_ip,
                    'resolved_values': resolved_values
                }
            )

        except Timeout:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                response_time=(time.time() - start_time) * 1000,
                error_message=f"DNS query timed out after {self.timeout}s"
            )
        except DNSException as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"DNS error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"DNS monitor '{self.name}' failed: {e}")
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"DNS check failed: {str(e)}"
            )

    def _validate_values(self, resolved: list, expected: list, mode: str) -> bool:
        """
        Validate resolved values against expected values.

        Args:
            resolved: List of resolved values
            expected: List of expected values
            mode: Validation mode ('any', 'all', 'exact')

        Returns:
            True if validation passes
        """
        if mode == 'exact':
            # Exact match (same values, same order)
            return resolved == expected
        elif mode == 'all':
            # All expected values must be present
            return all(exp in resolved for exp in expected)
        else:  # 'any'
            # At least one expected value must be present
            return any(exp in resolved for exp in expected)
