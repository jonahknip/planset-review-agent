"""
File handling for the PlanSet Review Bot
Handles PDF downloads from Teams attachments and OneDrive/SharePoint links
"""

import re
import os
import tempfile
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import aiohttp
from azure.storage.blob.aio import BlobServiceClient

from bot.config import config

logger = logging.getLogger(__name__)

# OneDrive/SharePoint URL patterns
ONEDRIVE_PATTERNS = [
    r'https?://[a-zA-Z0-9-]+\.sharepoint\.com/.*',
    r'https?://[a-zA-Z0-9-]+-my\.sharepoint\.com/.*',
    r'https?://onedrive\.live\.com/.*',
    r'https?://1drv\.ms/.*',
]


@dataclass
class DownloadedFile:
    """Represents a downloaded file"""
    local_path: str
    filename: str
    size_bytes: int
    source: str  # 'attachment' or 'onedrive'
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)
    
    def cleanup(self):
        """Delete the local file"""
        try:
            if os.path.exists(self.local_path):
                os.remove(self.local_path)
                logger.info(f"Cleaned up temp file: {self.local_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {self.local_path}: {e}")


class FileHandler:
    """Handles file downloads from various sources"""
    
    def __init__(self, graph_client=None):
        """
        Initialize file handler
        
        Args:
            graph_client: Microsoft Graph client for OneDrive/SharePoint access
        """
        self.graph_client = graph_client
        self.temp_dir = tempfile.gettempdir()
    
    def is_onedrive_sharepoint_url(self, text: str) -> Optional[str]:
        """
        Check if text contains a OneDrive/SharePoint URL
        
        Returns the URL if found, None otherwise
        """
        for pattern in ONEDRIVE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def is_valid_pdf(self, filename: str) -> bool:
        """Check if filename has a PDF extension"""
        return filename.lower().endswith('.pdf')
    
    async def download_from_attachment(
        self,
        content_url: str,
        filename: str,
        bot_token: str
    ) -> DownloadedFile:
        """
        Download a file from a Teams attachment
        
        Args:
            content_url: The attachment content URL
            filename: Original filename
            bot_token: Bot authentication token for download
            
        Returns:
            DownloadedFile with local path and metadata
        """
        logger.info(f"Downloading attachment: {filename}")
        
        # Create temp file path
        safe_filename = self._sanitize_filename(filename)
        local_path = os.path.join(self.temp_dir, f"planset_{safe_filename}")
        
        # Download file
        headers = {"Authorization": f"Bearer {bot_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(content_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download attachment: HTTP {response.status}")
                
                content = await response.read()
                size_bytes = len(content)
                
                with open(local_path, 'wb') as f:
                    f.write(content)
        
        logger.info(f"Downloaded attachment to {local_path} ({size_bytes} bytes)")
        
        return DownloadedFile(
            local_path=local_path,
            filename=filename,
            size_bytes=size_bytes,
            source='attachment'
        )
    
    async def download_from_onedrive(
        self,
        share_url: str,
        user_token: str = None
    ) -> DownloadedFile:
        """
        Download a file from OneDrive/SharePoint using Graph API
        
        Args:
            share_url: The OneDrive/SharePoint sharing URL
            user_token: User's access token (for delegated permissions)
            
        Returns:
            DownloadedFile with local path and metadata
        """
        if not self.graph_client:
            raise Exception("Graph client not configured for OneDrive access")
        
        logger.info(f"Downloading from OneDrive/SharePoint: {share_url}")
        
        # Get file metadata and download URL from Graph API
        file_info = await self.graph_client.get_shared_file_info(share_url, user_token)
        
        filename = file_info['name']
        download_url = file_info['download_url']
        size_bytes = file_info.get('size', 0)
        
        # Validate file type
        if not self.is_valid_pdf(filename):
            raise Exception(f"File is not a PDF: {filename}")
        
        # Check size limit
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > config.max_file_size_mb:
            raise Exception(f"File too large: {size_mb:.1f}MB (max: {config.max_file_size_mb}MB)")
        
        # Create temp file path
        safe_filename = self._sanitize_filename(filename)
        local_path = os.path.join(self.temp_dir, f"planset_{safe_filename}")
        
        # Download file content
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download file: HTTP {response.status}")
                
                content = await response.read()
                actual_size = len(content)
                
                with open(local_path, 'wb') as f:
                    f.write(content)
        
        logger.info(f"Downloaded from OneDrive to {local_path} ({actual_size} bytes)")
        
        return DownloadedFile(
            local_path=local_path,
            filename=filename,
            size_bytes=actual_size,
            source='onedrive'
        )
    
    async def upload_to_blob_storage(
        self,
        local_path: str,
        blob_name: str
    ) -> str:
        """
        Upload a file to Azure Blob Storage for temporary storage
        
        Args:
            local_path: Path to local file
            blob_name: Name for the blob
            
        Returns:
            Blob URL
        """
        if not config.storage_connection_string:
            raise Exception("Azure Storage not configured")
        
        blob_service = BlobServiceClient.from_connection_string(
            config.storage_connection_string
        )
        
        container_client = blob_service.get_container_client(
            config.storage_container_name
        )
        
        # Ensure container exists
        try:
            await container_client.create_container()
        except Exception:
            pass  # Container may already exist
        
        blob_client = container_client.get_blob_client(blob_name)
        
        with open(local_path, 'rb') as f:
            await blob_client.upload_blob(f, overwrite=True)
        
        return blob_client.url
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe local storage"""
        # Remove path components
        filename = os.path.basename(filename)
        # Replace unsafe characters
        filename = re.sub(r'[^\w\-_\.]', '_', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        return filename


def extract_urls_from_text(text: str) -> list[str]:
    """Extract all URLs from text"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)
