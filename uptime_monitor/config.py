"""
Configuration loader and validator.
Loads YAML configuration with environment variable substitution.
"""

import os
import re
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class ConfigError(Exception):
    """Configuration error exception"""
    pass


class Config:
    """Configuration manager"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self.raw_config: Dict[str, Any] = {}
        self.global_config: Dict[str, Any] = {}
        self.notifications: List[Dict[str, Any]] = []
        self.groups: List[Dict[str, Any]] = []
        self.monitors: List[Dict[str, Any]] = []

    def load(self) -> None:
        """Load and parse configuration file"""
        if not Path(self.config_path).exists():
            raise ConfigError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, 'r') as f:
                raw_content = f.read()

            # Substitute environment variables
            substituted_content = self._substitute_env_vars(raw_content)

            # Parse YAML
            self.raw_config = yaml.safe_load(substituted_content)

            if not self.raw_config:
                raise ConfigError("Configuration file is empty")

            # Parse sections
            self.global_config = self.raw_config.get('global', {})
            self.notifications = self.raw_config.get('notifications', [])
            self.groups = self.raw_config.get('groups', [])
            self.monitors = self.raw_config.get('monitors', [])

            # Validate configuration
            self._validate()

            logger.info(f"Configuration loaded successfully from {self.config_path}")
            logger.info(f"Loaded {len(self.monitors)} monitors, {len(self.groups)} groups, {len(self.notifications)} notification channels")

        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration: {e}")

    def _substitute_env_vars(self, content: str) -> str:
        """
        Substitute environment variables in format ${VAR_NAME}.

        Args:
            content: YAML content with potential env vars

        Returns:
            Content with env vars substituted

        Raises:
            ConfigError: If required env var is not found
        """
        pattern = re.compile(r'\$\{([A-Za-z0-9_]+)\}')

        def replacer(match):
            var_name = match.group(1)
            var_value = os.environ.get(var_name)

            if var_value is None:
                raise ConfigError(f"Environment variable '{var_name}' not found. Set it in .env file or environment.")

            return var_value

        return pattern.sub(replacer, content)

    def _validate(self) -> None:
        """Validate configuration structure"""
        # Validate global section
        if not self.global_config:
            logger.warning("No global configuration section found, using defaults")

        # Validate monitors
        if not self.monitors:
            raise ConfigError("No monitors defined in configuration")

        monitor_names = set()
        for idx, monitor in enumerate(self.monitors):
            # Check required fields
            if 'name' not in monitor:
                raise ConfigError(f"Monitor at index {idx} is missing 'name' field")

            if 'type' not in monitor:
                raise ConfigError(f"Monitor '{monitor.get('name')}' is missing 'type' field")

            # Check for duplicate names
            name = monitor['name']
            if name in monitor_names:
                raise ConfigError(f"Duplicate monitor name: '{name}'")
            monitor_names.add(name)

            # Validate monitor type
            valid_types = ['http', 'tcp', 'ping', 'dns', 'websocket', 'docker', 'push']
            if monitor['type'] not in valid_types:
                raise ConfigError(
                    f"Monitor '{name}' has invalid type '{monitor['type']}'. "
                    f"Valid types: {', '.join(valid_types)}"
                )

        # Validate notification names referenced by monitors
        notification_names = {n['name'] for n in self.notifications}
        for monitor in self.monitors:
            monitor_notifs = monitor.get('notifications', [])
            for notif_name in monitor_notifs:
                if notif_name not in notification_names:
                    logger.warning(
                        f"Monitor '{monitor['name']}' references unknown notification '{notif_name}'"
                    )

    def get_global(self, key: str, default: Any = None) -> Any:
        """Get global configuration value"""
        return self.global_config.get(key, default)

    def get_database_path(self) -> str:
        """Get database path from config or default"""
        db_path = self.get_global('database', 'data/uptime.db')

        # Create data directory if it doesn't exist
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        return db_path

    def get_web_config(self) -> Dict[str, Any]:
        """Get web server configuration"""
        web_config = self.get_global('web', {})
        return {
            'host': web_config.get('host', '0.0.0.0'),
            'port': web_config.get('port', 5000),
            'secret_key': web_config.get('secret_key', self._generate_secret_key())
        }

    def get_default_interval(self) -> int:
        """Get default check interval in seconds"""
        return self.get_global('default_interval', 60)

    def get_timezone(self) -> str:
        """Get timezone for reporting"""
        return self.get_global('timezone', 'UTC')

    def get_retention_config(self) -> Dict[str, int]:
        """Get data retention configuration"""
        retention = self.get_global('retention', {})
        return {
            'ping_history_days': retention.get('ping_history_days', 30),
            'aggregate_after_days': retention.get('aggregate_after_days', 90)
        }

    def get_monitors_by_group(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get monitors organized by group"""
        groups = {}

        for monitor in self.monitors:
            group_name = monitor.get('group', 'Ungrouped')
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(monitor)

        return groups

    def get_notification_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get notification configuration by name"""
        for notif in self.notifications:
            if notif.get('name') == name:
                return notif
        return None

    def get_group_display_order(self) -> List[str]:
        """Get group names in display order"""
        # Sort groups by display_order field
        sorted_groups = sorted(
            self.groups,
            key=lambda g: g.get('display_order', 999)
        )
        return [g['name'] for g in sorted_groups]

    @staticmethod
    def _generate_secret_key() -> str:
        """Generate a random secret key for Flask"""
        import secrets
        return secrets.token_hex(32)

    def reload(self) -> None:
        """Reload configuration from file"""
        logger.info("Reloading configuration...")
        self.load()

    def __repr__(self) -> str:
        return f"<Config(monitors={len(self.monitors)}, groups={len(self.groups)}, notifications={len(self.notifications)})>"


# Global config instance
_config: Optional[Config] = None


def load_config(config_path: str = "config.yaml") -> Config:
    """
    Load configuration from file.

    Args:
        config_path: Path to configuration file

    Returns:
        Config instance
    """
    global _config
    _config = Config(config_path)
    _config.load()
    return _config


def get_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Config instance

    Raises:
        ConfigError: If config has not been loaded yet
    """
    if _config is None:
        raise ConfigError("Configuration not loaded. Call load_config() first.")
    return _config
