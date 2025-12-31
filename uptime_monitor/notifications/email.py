"""
Email (SMTP) notification handler.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from uptime_monitor.notifications.base import Notifier, NotificationContext
import logging

logger = logging.getLogger(__name__)


class EmailNotifier(Notifier):
    """Email notification via SMTP"""

    def send(self, context: NotificationContext) -> bool:
        """
        Send email notification.

        Args:
            context: Notification context

        Returns:
            True if email sent successfully
        """
        smtp_host = self.config.get('smtp_host')
        smtp_port = self.config.get('smtp_port', 587)
        smtp_user = self.config.get('smtp_user')
        smtp_password = self.config.get('smtp_password')
        smtp_use_tls = self.config.get('smtp_use_tls', True)
        from_address = self.config.get('from_address', smtp_user)
        to_addresses = self.config.get('to_addresses', [])

        if not smtp_host or not smtp_user or not smtp_password:
            logger.error("Email notifier missing required configuration (smtp_host, smtp_user, smtp_password)")
            return False

        if not to_addresses:
            logger.error("Email notifier has no recipient addresses configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = from_address
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = self._create_subject(context)

            # Create plain text and HTML versions
            text_body = self.format_message(context)
            html_body = self._create_html_body(context)

            # Attach parts
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Connect and send
            if smtp_use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)

            server.login(smtp_user, smtp_password)
            server.sendmail(from_address, to_addresses, msg.as_string())
            server.quit()

            logger.info(f"Email sent to {', '.join(to_addresses)}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed - check username/password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _create_subject(self, context: NotificationContext) -> str:
        """Create email subject line"""
        event_type = context.event_type.value.upper()
        status_emoji = {
            'down': '🔴',
            'up': '🟢',
            'ssl_expire': '⚠️',
            'degraded': '🟡'
        }
        emoji = status_emoji.get(context.event_type.value, 'ℹ️')

        return f"{emoji} [{event_type}] {context.monitor_name}"

    def _create_html_body(self, context: NotificationContext) -> str:
        """Create HTML email body"""
        status_color = {
            'down': '#dc3545',
            'up': '#28a745',
            'ssl_expire': '#ffc107',
            'degraded': '#fd7e14'
        }
        color = status_color.get(context.event_type.value, '#6c757d')

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 5px 5px; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }}
                .details {{ background-color: white; padding: 15px; border-radius: 5px; margin-top: 15px; }}
                .detail-item {{ margin: 8px 0; }}
                .label {{ font-weight: bold; color: #495057; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">{context.event_type.value.upper()}: {context.monitor_name}</h2>
                </div>
                <div class="content">
                    <p style="font-size: 16px; margin-top: 0;">{context.message}</p>

                    <div class="details">
                        <div class="detail-item">
                            <span class="label">Monitor:</span> {context.monitor_name}
                        </div>
                        <div class="detail-item">
                            <span class="label">Status:</span> {context.status}
                        </div>
                        <div class="detail-item">
                            <span class="label">Time:</span> {context.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
                        </div>
"""

        # Add metadata if present
        if context.metadata:
            html += """
                        <div class="detail-item" style="margin-top: 15px;">
                            <span class="label">Additional Details:</span>
                        </div>
"""
            for key, value in context.metadata.items():
                html += f"""
                        <div class="detail-item" style="margin-left: 20px;">
                            <span class="label">{key}:</span> {value}
                        </div>
"""

        html += """
                    </div>

                    <div class="footer">
                        <p style="margin: 0;">This is an automated notification from Simple Uptime Monitor.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return html
