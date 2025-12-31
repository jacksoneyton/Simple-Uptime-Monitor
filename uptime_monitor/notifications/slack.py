"""
Slack webhook notification handler.
"""

from slack_sdk.webhook import WebhookClient
from slack_sdk.errors import SlackApiError
from uptime_monitor.notifications.base import Notifier, NotificationContext, NotificationEvent
import logging

logger = logging.getLogger(__name__)


class SlackNotifier(Notifier):
    """Slack webhook notification"""

    def send(self, context: NotificationContext) -> bool:
        """
        Send Slack notification.

        Args:
            context: Notification context

        Returns:
            True if notification sent successfully
        """
        webhook_url = self.config.get('webhook_url')
        channel = self.config.get('channel')
        username = self.config.get('username', 'Uptime Bot')

        if not webhook_url:
            logger.error("Slack notifier missing webhook_url configuration")
            return False

        try:
            webhook = WebhookClient(webhook_url)

            # Create message blocks
            blocks = self._create_blocks(context)

            # Send message
            response = webhook.send(
                text=f"{context.event_type.value.upper()}: {context.monitor_name}",  # Fallback text
                blocks=blocks,
                channel=channel,
                username=username
            )

            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return True
            else:
                logger.error(f"Slack webhook returned status code {response.status_code}")
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _create_blocks(self, context: NotificationContext) -> list:
        """Create Slack message blocks"""
        # Emoji and color based on event type
        emoji_map = {
            NotificationEvent.DOWN: ':red_circle:',
            NotificationEvent.UP: ':large_green_circle:',
            NotificationEvent.SSL_EXPIRE: ':warning:',
            NotificationEvent.DEGRADED: ':large_orange_circle:'
        }
        emoji = emoji_map.get(context.event_type, ':information_source:')

        color_map = {
            NotificationEvent.DOWN: '#dc3545',
            NotificationEvent.UP: '#28a745',
            NotificationEvent.SSL_EXPIRE: '#ffc107',
            NotificationEvent.DEGRADED: '#fd7e14'
        }
        color = color_map.get(context.event_type, '#6c757d')

        # Build blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {context.event_type.value.upper()}: {context.monitor_name}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": context.message
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{context.status}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{context.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    }
                ]
            }
        ]

        # Add metadata fields if present
        if context.metadata:
            metadata_fields = []
            for key, value in list(context.metadata.items())[:6]:  # Limit to 6 fields
                metadata_fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key.replace('_', ' ').title()}:*\n{value}"
                })

            # Add metadata section
            blocks.append({
                "type": "section",
                "fields": metadata_fields
            })

        # Add divider and footer
        blocks.extend([
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_Simple Uptime Monitor_"
                    }
                ]
            }
        ])

        return blocks
