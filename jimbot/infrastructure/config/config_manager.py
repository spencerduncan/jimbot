"""Configuration Manager Implementation

Hierarchical configuration with hot reload support.
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ConfigChangeHandler(FileSystemEventHandler):
    """Handle configuration file changes"""

    def __init__(self, config_manager):
        self.config_manager = config_manager

    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith((".yaml", ".yml", ".json")):
            logger.info(f"Configuration file changed: {event.src_path}")
            asyncio.create_task(self.config_manager.reload())


class ConfigManager:
    """
    Hierarchical configuration management with hot reload.

    Features:
    - Three-level hierarchy: Environment → Component → Feature
    - Hot reload with file watching
    - Configuration validation
    - Change notifications
    - Environment variable interpolation
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config: Dict[str, Any] = {}
        self.watchers: Dict[str, List[Callable]] = defaultdict(list)
        self.observer = Observer()
        self.environment = os.getenv("JIMBOT_ENV", "development")

    async def initialize(self):
        """Initialize configuration manager"""
        # Load initial configuration
        await self.reload()

        # Start file watcher
        event_handler = ConfigChangeHandler(self)
        self.observer.schedule(event_handler, str(self.config_dir), recursive=True)
        self.observer.start()

        logger.info(
            f"Configuration manager initialized for environment: {self.environment}"
        )

    async def reload(self):
        """Reload all configuration files"""
        new_config = {}

        # Load base configuration
        base_config = self._load_file(self.config_dir / "base.yaml")
        if base_config:
            new_config.update(base_config)

        # Load environment-specific configuration
        env_config = self._load_file(
            self.config_dir / "environments" / f"{self.environment}.yaml"
        )
        if env_config:
            new_config = self._deep_merge(new_config, env_config)

        # Load component configurations
        component_dir = self.config_dir / "components"
        if component_dir.exists():
            for component_file in component_dir.glob("*.yaml"):
                component_name = component_file.stem
                component_config = self._load_file(component_file)
                if component_config:
                    new_config[component_name] = self._deep_merge(
                        new_config.get(component_name, {}), component_config
                    )

        # Apply environment variable interpolation
        new_config = self._interpolate_env_vars(new_config)

        # Detect changes and notify watchers
        changes = self._detect_changes(self.config, new_config)
        self.config = new_config

        # Notify watchers of changes
        for key, old_value, new_value in changes:
            await self._notify_watchers(key, old_value, new_value)

        logger.info(f"Configuration reloaded, {len(changes)} changes detected")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., "infrastructure.event_bus.port")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split(".")
        value = self.config

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def watch(self, key: str):
        """
        Decorator to watch for configuration changes.

        Example:
            @config_manager.watch("infrastructure.event_bus.batch_window_ms")
            async def on_batch_window_change(old_value, new_value):
                event_bus.update_batch_window(new_value)
        """

        def decorator(handler: Callable):
            self.watchers[key].append(handler)
            return handler

        return decorator

    async def set(self, key: str, value: Any):
        """
        Set configuration value programmatically.

        Args:
            key: Configuration key
            value: New value
        """
        parts = key.split(".")
        config = self.config

        # Navigate to parent
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]

        old_value = config.get(parts[-1])
        config[parts[-1]] = value

        # Notify watchers
        await self._notify_watchers(key, old_value, value)

    def _load_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from file"""
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                if path.suffix in [".yaml", ".yml"]:
                    return yaml.safe_load(f)
                elif path.suffix == ".json":
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config file {path}: {e}")
            return None

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _interpolate_env_vars(self, config: Any) -> Any:
        """Replace ${ENV_VAR} with environment variable values"""
        if isinstance(config, str):
            # Look for ${VAR_NAME} pattern
            import re

            pattern = r"\$\{([^}]+)\}"

            def replacer(match):
                var_name = match.group(1)
                return os.getenv(var_name, match.group(0))

            return re.sub(pattern, replacer, config)

        elif isinstance(config, dict):
            return {k: self._interpolate_env_vars(v) for k, v in config.items()}

        elif isinstance(config, list):
            return [self._interpolate_env_vars(item) for item in config]

        return config

    def _detect_changes(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any], prefix: str = ""
    ) -> List[tuple]:
        """Detect configuration changes"""
        changes = []

        # Check for modified and removed keys
        for key, old_value in old_config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if key not in new_config:
                changes.append((full_key, old_value, None))
            elif old_value != new_config[key]:
                if isinstance(old_value, dict) and isinstance(new_config[key], dict):
                    # Recursive check for nested configs
                    changes.extend(
                        self._detect_changes(old_value, new_config[key], full_key)
                    )
                else:
                    changes.append((full_key, old_value, new_config[key]))

        # Check for new keys
        for key, new_value in new_config.items():
            if key not in old_config:
                full_key = f"{prefix}.{key}" if prefix else key
                changes.append((full_key, None, new_value))

        return changes

    async def _notify_watchers(self, key: str, old_value: Any, new_value: Any):
        """Notify watchers of configuration changes"""
        # Exact key watchers
        for handler in self.watchers.get(key, []):
            try:
                await handler(old_value, new_value)
            except Exception as e:
                logger.error(f"Error in config watcher for {key}: {e}", exc_info=True)

        # Pattern watchers (e.g., watching "infrastructure.*")
        for pattern, handlers in self.watchers.items():
            if "*" in pattern and self._matches_pattern(key, pattern):
                for handler in handlers:
                    try:
                        await handler(old_value, new_value)
                    except Exception as e:
                        logger.error(
                            f"Error in pattern watcher {pattern}: {e}", exc_info=True
                        )

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern with wildcards"""
        import fnmatch

        return fnmatch.fnmatch(key, pattern)

    def validate(self, schema: Dict[str, Any]) -> List[str]:
        """
        Validate configuration against schema.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        # TODO: Implement schema validation
        return errors

    def export(self) -> Dict[str, Any]:
        """Export current configuration"""
        return self.config.copy()

    def stop(self):
        """Stop configuration manager"""
        self.observer.stop()
        self.observer.join()
