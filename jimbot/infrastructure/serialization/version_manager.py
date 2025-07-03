"""Version management for Protocol Buffer schemas

Handles schema versioning, compatibility checking, and migrations.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VersionChange(str, Enum):
    """Types of version changes"""

    PATCH = "patch"  # Bug fixes, no schema changes
    MINOR = "minor"  # New fields, backward compatible
    MAJOR = "major"  # Breaking changes


@dataclass
class SchemaVersion:
    """Schema version information"""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "SchemaVersion") -> bool:
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __eq__(self, other: "SchemaVersion") -> bool:
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )

    @classmethod
    def from_string(cls, version_str: str) -> "SchemaVersion":
        """Parse version string (e.g., "1.2.3")"""
        parts = version_str.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version string: {version_str}")

        return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))

    def is_compatible_with(self, other: "SchemaVersion") -> bool:
        """Check if this version is compatible with another"""
        # Same major version = compatible
        # Higher minor/patch in same major = backward compatible
        if self.major != other.major:
            return False

        # Newer minor versions are backward compatible
        if self.minor > other.minor:
            return True
        elif self.minor < other.minor:
            return False

        # Same minor, any patch is compatible
        return True


class VersionManager:
    """Manages Protocol Buffer schema versions and migrations"""

    # Current schema version
    CURRENT_VERSION = SchemaVersion(1, 0, 0)

    # Minimum supported version for compatibility
    MIN_SUPPORTED_VERSION = SchemaVersion(1, 0, 0)

    def __init__(self):
        """Initialize version manager"""
        self.migrations: Dict[Tuple[str, str], List[callable]] = {}
        self.feature_flags: Dict[str, SchemaVersion] = {}
        self._register_migrations()
        self._register_features()

    def _register_migrations(self):
        """Register available migrations between versions"""
        # Example migrations - would be implemented as needed
        # self.register_migration(
        #     SchemaVersion(1, 0, 0),
        #     SchemaVersion(1, 1, 0),
        #     [self._migrate_1_0_to_1_1]
        # )

    def _register_features(self):
        """Register feature flags and their required versions"""
        self.feature_flags = {
            "learning_events": SchemaVersion(1, 0, 0),
            "strategy_events": SchemaVersion(1, 0, 0),
            "knowledge_updates": SchemaVersion(1, 0, 0),
            "custom_events": SchemaVersion(1, 0, 0),
            "metric_events": SchemaVersion(1, 0, 0),
        }

    def register_migration(
        self,
        from_version: SchemaVersion,
        to_version: SchemaVersion,
        migration_funcs: List[callable],
    ):
        """Register a migration path between versions"""
        key = (str(from_version), str(to_version))
        self.migrations[key] = migration_funcs
        logger.info(f"Registered migration: {from_version} -> {to_version}")

    def check_compatibility(
        self, client_version: SchemaVersion
    ) -> Tuple[bool, Optional[str]]:
        """Check if a client version is compatible

        Returns:
            Tuple of (is_compatible, error_message)
        """
        # Check minimum version
        if client_version < self.MIN_SUPPORTED_VERSION:
            return (
                False,
                f"Version {client_version} is below minimum supported version {self.MIN_SUPPORTED_VERSION}",
            )

        # Check major version compatibility
        if client_version.major != self.CURRENT_VERSION.major:
            return (
                False,
                f"Major version mismatch: client {client_version.major}, server {self.CURRENT_VERSION.major}",
            )

        # Minor version differences are OK (backward compatible)
        if client_version.minor > self.CURRENT_VERSION.minor:
            return (
                False,
                f"Client version {client_version} is newer than server version {self.CURRENT_VERSION}",
            )

        return True, None

    def negotiate_version(
        self, client_versions: List[SchemaVersion]
    ) -> Optional[SchemaVersion]:
        """Negotiate the best compatible version

        Args:
            client_versions: List of versions supported by client

        Returns:
            Best compatible version or None if no compatible version
        """
        # Sort client versions in descending order
        sorted_versions = sorted(client_versions, reverse=True)

        for version in sorted_versions:
            compatible, _ = self.check_compatibility(version)
            if compatible:
                return version

        return None

    def get_required_migrations(
        self, from_version: SchemaVersion, to_version: SchemaVersion
    ) -> List[callable]:
        """Get list of migrations required to go from one version to another

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            List of migration functions to apply in order
        """
        if from_version == to_version:
            return []

        # Direct migration path
        direct_key = (str(from_version), str(to_version))
        if direct_key in self.migrations:
            return self.migrations[direct_key]

        # TODO: Implement path finding for multi-step migrations
        # For now, we don't support multi-step migrations
        logger.warning(f"No migration path from {from_version} to {to_version}")
        return []

    def apply_migrations(
        self, data: Dict, from_version: SchemaVersion, to_version: SchemaVersion
    ) -> Dict:
        """Apply migrations to transform data between versions

        Args:
            data: Data to migrate
            from_version: Current version of the data
            to_version: Target version

        Returns:
            Migrated data
        """
        migrations = self.get_required_migrations(from_version, to_version)

        migrated_data = data.copy()
        for migration_func in migrations:
            try:
                migrated_data = migration_func(migrated_data)
                logger.debug(f"Applied migration: {migration_func.__name__}")
            except Exception as e:
                logger.error(f"Migration failed: {e}", exc_info=True)
                raise

        return migrated_data

    def check_feature_availability(
        self, feature: str, client_version: SchemaVersion
    ) -> bool:
        """Check if a feature is available for a given client version

        Args:
            feature: Feature name to check
            client_version: Client's schema version

        Returns:
            True if feature is available for the client version
        """
        if feature not in self.feature_flags:
            logger.warning(f"Unknown feature: {feature}")
            return False

        required_version = self.feature_flags[feature]
        return client_version >= required_version

    def get_version_info(self) -> Dict:
        """Get comprehensive version information

        Returns:
            Dictionary with version details
        """
        return {
            "current_version": str(self.CURRENT_VERSION),
            "min_supported_version": str(self.MIN_SUPPORTED_VERSION),
            "features": {
                feature: str(version) for feature, version in self.feature_flags.items()
            },
            "migration_paths": [
                {"from": from_v, "to": to_v}
                for (from_v, to_v) in self.migrations.keys()
            ],
        }

    def validate_event_version(self, event: Dict) -> Tuple[bool, Optional[str]]:
        """Validate event version compatibility

        Args:
            event: Event dictionary with version field

        Returns:
            Tuple of (is_valid, error_message)
        """
        version_num = event.get("version", 1)

        # Map version number to SchemaVersion
        # Version 1 = 1.0.0
        if version_num == 1:
            event_version = SchemaVersion(1, 0, 0)
        else:
            return False, f"Unknown event version: {version_num}"

        return self.check_compatibility(event_version)

    # Example migration functions (would be implemented as needed)
    def _migrate_1_0_to_1_1(self, data: Dict) -> Dict:
        """Example migration from 1.0.0 to 1.1.0"""
        # Add new required fields with defaults
        # Transform existing fields
        # etc.
        return data


# Global instance
version_manager = VersionManager()
