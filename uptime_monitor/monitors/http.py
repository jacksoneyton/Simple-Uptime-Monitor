"""
HTTP/HTTPS monitor with keyword and JSON query validation support.
"""

import time
import re
import ssl
import socket
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, SSLError
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from uptime_monitor.monitors.base import Monitor, MonitorResult, MonitorStatus
import logging

logger = logging.getLogger(__name__)


class HTTPMonitor(Monitor):
    """HTTP/HTTPS monitor with support for keyword and JSON validation"""

    def check(self) -> MonitorResult:
        """
        Perform HTTP(S) check.

        Returns:
            MonitorResult with status and response time
        """
        url = self.config.get('url')
        if not url:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message="No URL configured"
            )

        method = self.config.get('method', 'GET').upper()
        expected_codes = self.config.get('expected_status_codes', [200])
        headers = self.config.get('headers', {})
        follow_redirects = self.config.get('follow_redirects', True)
        verify_ssl = self.config.get('verify_ssl', True)
        body = self.config.get('body')

        start_time = time.time()

        try:
            # Make HTTP request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                timeout=self.timeout,
                allow_redirects=follow_redirects,
                verify=verify_ssl
            )

            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Check status code
            if response.status_code not in expected_codes:
                return MonitorResult(
                    status=MonitorStatus.DOWN,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Unexpected status code: {response.status_code} (expected {expected_codes})"
                )

            # Perform keyword validation if configured
            keyword_config = self.config.get('keyword')
            if keyword_config:
                keyword_valid = self._validate_keyword(response.text, keyword_config)
                if not keyword_valid:
                    return MonitorResult(
                        status=MonitorStatus.DOWN,
                        response_time=response_time,
                        status_code=response.status_code,
                        error_message="Keyword validation failed"
                    )

            # Perform JSON query validation if configured
            json_query_config = self.config.get('json_query')
            if json_query_config:
                json_valid, json_error = self._validate_json(response, json_query_config)
                if not json_valid:
                    return MonitorResult(
                        status=MonitorStatus.DOWN,
                        response_time=response_time,
                        status_code=response.status_code,
                        error_message=f"JSON validation failed: {json_error}"
                    )

            # Check SSL certificate if HTTPS
            ssl_info = {}
            if url.startswith('https://'):
                ssl_info = self._check_ssl_certificate(url)

            # All checks passed
            return MonitorResult(
                status=MonitorStatus.UP,
                response_time=response_time,
                status_code=response.status_code,
                metadata={
                    'content_length': len(response.content),
                    'url': url,
                    **ssl_info
                }
            )

        except Timeout:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                response_time=(time.time() - start_time) * 1000,
                error_message=f"Request timed out after {self.timeout}s"
            )
        except SSLError as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"SSL error: {str(e)}"
            )
        except ConnectionError as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Connection error: {str(e)}"
            )
        except RequestException as e:
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"HTTP monitor '{self.name}' failed with unexpected error: {e}")
            return MonitorResult(
                status=MonitorStatus.DOWN,
                error_message=f"Unexpected error: {str(e)}"
            )

    def _validate_keyword(self, content: str, keyword_config: Dict[str, Any]) -> bool:
        """
        Validate keyword in response content.

        Args:
            content: Response content
            keyword_config: Keyword validation config

        Returns:
            True if validation passes, False otherwise
        """
        search_for = keyword_config.get('search_for', '')
        use_regex = keyword_config.get('regex', False)
        invert = keyword_config.get('invert', False)

        if use_regex:
            # Regex search
            try:
                pattern = re.compile(search_for)
                found = pattern.search(content) is not None
            except re.error as e:
                logger.error(f"Invalid regex pattern '{search_for}': {e}")
                return False
        else:
            # Plain string search
            found = search_for in content

        # Apply invert logic
        return not found if invert else found

    def _validate_json(self, response: requests.Response, json_config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate JSON response using JSONPath.

        Args:
            response: HTTP response
            json_config: JSON validation config

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            json_data = response.json()
        except ValueError as e:
            return False, f"Response is not valid JSON: {str(e)}"

        path_expr = json_config.get('path')
        expected_value = json_config.get('expected_value')
        check_exists = json_config.get('exists', False)

        if not path_expr:
            return False, "No JSONPath expression configured"

        try:
            # Parse JSONPath expression
            jsonpath_expr = jsonpath_parse(path_expr)
            matches = jsonpath_expr.find(json_data)

            # Check if field exists
            if check_exists:
                return len(matches) > 0, "JSONPath field not found" if len(matches) == 0 else None

            # Check if value matches
            if expected_value is not None:
                if len(matches) == 0:
                    return False, f"JSONPath '{path_expr}' not found in response"

                actual_value = matches[0].value

                if actual_value != expected_value:
                    return False, f"Expected '{expected_value}', got '{actual_value}'"

            return True, None

        except JsonPathParserError as e:
            return False, f"Invalid JSONPath expression: {str(e)}"
        except Exception as e:
            return False, f"JSON validation error: {str(e)}"

    def _check_ssl_certificate(self, url: str) -> Dict[str, Any]:
        """
        Check SSL certificate information.

        Args:
            url: HTTPS URL

        Returns:
            Dictionary with SSL certificate info
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or 443

            # Get certificate
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)

            # Parse certificate
            cert = x509.load_der_x509_certificate(cert_der, default_backend())

            # Calculate days until expiration
            days_remaining = (cert.not_valid_after - datetime.utcnow()).days

            return {
                'ssl_valid_until': cert.not_valid_after.isoformat(),
                'ssl_days_remaining': days_remaining,
                'ssl_issuer': cert.issuer.rfc4514_string(),
                'ssl_subject': cert.subject.rfc4514_string()
            }

        except Exception as e:
            logger.warning(f"Failed to check SSL certificate for {url}: {e}")
            return {}
