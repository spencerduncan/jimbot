"""Schema Registry Module

Manages Protocol Buffer schema versions and evolution.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """Registry for Protocol Buffer schemas"""
    
    def __init__(self):
        self.schemas: Dict[str, Any] = {}
        self.versions: Dict[str, int] = {}
        
    def register_schema(self, name: str, schema: Any, version: int = 1):
        """Register a schema with version"""
        self.schemas[name] = schema
        self.versions[name] = version
        logger.info(f"Registered schema {name} v{version}")
        
    def get_schema(self, name: str) -> Any:
        """Get schema by name"""
        return self.schemas.get(name)
        
    def get_version(self, name: str) -> int:
        """Get schema version"""
        return self.versions.get(name, 0)