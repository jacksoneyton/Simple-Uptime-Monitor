"""
Discord webhook notification handler.
"""

from discord_webhook import DiscordWebhook, DiscordEmbed
from uptime_monitor.notifications.base import Notifier, NotificationContext, NotificationEvent
import logging

logger = logging.getLogger(__name__)


class DiscordNotifier(Notifier):
    """Discord webhook notification"""

    def send(self, context: NotificationContext) -> bool:
        """
        Send Discord notification.

        Args:
            context: Notification context

        Returns:
            True if notification sent successfully
        """
        webhook_url = self.config.get('webhook_url')
        username = self.config.get('username', 'Uptime Monitor')
        mention_role_id = self.config.get('mention_role_id')

        if not webhook_url:
            logger.error("Discord notifier missing webhook_url configuration")
            return False

        try:
            webhook = DiscordWebhook(url=webhook_url, username=username)

            # Create embed
            embed = self._create_embed(context)
            webhook.add_embed(embed)

            # Add role mention if configured and event is DOWN
            if mention_role_id and context.event_type == NotificationEvent.DOWN:
                webhook.set_content(f"<@&{mention_role_id}>")

            # Send webhook
            response = webhook.execute()

            if response.status_code in [200, 204]:
                logger.info("Discord notification sent successfully")
                return True
            else:
                logger.error(f"Discord webhook returned status code {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def _create_embed(self, context: NotificationContext) -> DiscordEmbed:
        """Create Discord embed"""
        # Color based on event type
        colors = {
            NotificationEvent.DOWN: 0xDC3545,      # Red
            NotificationEvent.UP: 0x28A745,        # Green
            NotificationEvent.SSL_EXPIRE: 0xFFC107,  # Yellow
            NotificationEvent.DEGRADED: 0xFD7E14    # Orange
        }
        color = colors.get(context.event_type, 0x6C757D)

        # Create embed
        embed = DiscordEmbed(
            title=f"{context.event_type.value.upper()}: {context.monitor_name}",
            description=context.message,
            color=color
        )

        # Add fields
        embed.add_embed_field(name="Status", value=context.status, inline=True)
        embed.add_embed_field(
            name="Time",
            value=context.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
            inline=True
        )

        # Add metadata fields
        if context.metadata:
            for key, value in list(context.metadata.items())[:5]:  # Limit to 5 additional fields
                embed.add_embed_field(name=key.replace('_', ' ').title(), value=str(value), inline=True)

        # Add footer
        embed.set_footer(text="Simple Uptime Monitor")
        embed.set_timestamp(context.timestamp)

        return embed
