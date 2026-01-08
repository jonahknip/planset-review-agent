"""
Configuration settings for the PlanSet Review Bot
"""

import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    """Bot configuration loaded from environment variables"""
    
    # Azure Bot Service
    app_id: str
    app_password: str
    
    # Azure AD (for Graph API)
    tenant_id: str
    client_id: str
    client_secret: str
    
    # Azure Blob Storage (for temp file storage)
    storage_connection_string: str
    storage_container_name: str = "planset-uploads"
    
    # Bot settings
    max_file_size_mb: int = 500
    supported_extensions: tuple = (".pdf",)
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables"""
        return cls(
            app_id=os.environ.get("BOT_APP_ID", ""),
            app_password=os.environ.get("BOT_APP_PASSWORD", ""),
            tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
            client_id=os.environ.get("AZURE_CLIENT_ID", ""),
            client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
            storage_connection_string=os.environ.get("AZURE_STORAGE_CONNECTION_STRING", ""),
            storage_container_name=os.environ.get("STORAGE_CONTAINER_NAME", "planset-uploads"),
            max_file_size_mb=int(os.environ.get("MAX_FILE_SIZE_MB", "500")),
        )
    
    def validate(self) -> list[str]:
        """Validate required configuration values, return list of missing items"""
        missing = []
        if not self.app_id:
            missing.append("BOT_APP_ID")
        if not self.app_password:
            missing.append("BOT_APP_PASSWORD")
        if not self.tenant_id:
            missing.append("AZURE_TENANT_ID")
        if not self.client_id:
            missing.append("AZURE_CLIENT_ID")
        if not self.client_secret:
            missing.append("AZURE_CLIENT_SECRET")
        if not self.storage_connection_string:
            missing.append("AZURE_STORAGE_CONNECTION_STRING")
        return missing


# Global config instance
config = BotConfig.from_env()
