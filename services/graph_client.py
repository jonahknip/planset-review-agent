"""
Microsoft Graph API client for OneDrive/SharePoint file access
"""

import base64
import logging
from typing import Optional
from urllib.parse import urlparse, quote

import aiohttp
from azure.identity.aio import ClientSecretCredential

from bot.config import config

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    """
    Microsoft Graph API client for accessing OneDrive and SharePoint files
    """
    
    def __init__(self):
        """Initialize the Graph client"""
        self._credential = None
        self._access_token = None
    
    async def _get_app_token(self) -> str:
        """
        Get an access token using application credentials (client credentials flow)
        """
        if not self._credential:
            self._credential = ClientSecretCredential(
                tenant_id=config.tenant_id,
                client_id=config.client_id,
                client_secret=config.client_secret
            )
        
        token = await self._credential.get_token("https://graph.microsoft.com/.default")
        return token.token
    
    async def get_shared_file_info(
        self,
        share_url: str,
        user_token: str = None
    ) -> dict:
        """
        Get file information from a sharing URL
        
        Uses the shares API to resolve sharing links to driveItem info.
        
        Args:
            share_url: OneDrive/SharePoint sharing URL
            user_token: Optional user token for delegated access
            
        Returns:
            Dict with 'name', 'size', 'download_url', and 'id'
        """
        # Encode the sharing URL for the shares API
        # See: https://docs.microsoft.com/en-us/graph/api/shares-get
        encoded_url = self._encode_sharing_url(share_url)
        
        # Get token
        token = user_token or await self._get_app_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # First, resolve the sharing link to get driveItem info
        shares_url = f"{GRAPH_API_BASE}/shares/{encoded_url}/driveItem"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(shares_url, headers=headers) as response:
                if response.status == 401:
                    raise Exception("Not authorized to access this file. Please check sharing permissions.")
                elif response.status == 404:
                    raise Exception("File not found. The link may have expired or the file was moved.")
                elif response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Graph API error: {response.status} - {error_text}")
                    raise Exception(f"Failed to access file: HTTP {response.status}")
                
                data = await response.json()
        
        # Extract file info
        file_info = {
            'id': data.get('id'),
            'name': data.get('name', 'unknown.pdf'),
            'size': data.get('size', 0),
            'download_url': data.get('@microsoft.graph.downloadUrl'),
            'web_url': data.get('webUrl'),
            'mime_type': data.get('file', {}).get('mimeType'),
        }
        
        # If no direct download URL, we need to request one
        if not file_info['download_url']:
            file_info['download_url'] = await self._get_download_url(
                encoded_url, token
            )
        
        logger.info(f"Resolved sharing link to file: {file_info['name']} ({file_info['size']} bytes)")
        
        return file_info
    
    async def _get_download_url(self, encoded_url: str, token: str) -> str:
        """
        Get a download URL for a shared file
        """
        headers = {
            "Authorization": f"Bearer {token}",
        }
        
        # Request content endpoint
        content_url = f"{GRAPH_API_BASE}/shares/{encoded_url}/driveItem/content"
        
        async with aiohttp.ClientSession() as session:
            # Use HEAD request to get redirect URL without downloading
            async with session.head(
                content_url,
                headers=headers,
                allow_redirects=False
            ) as response:
                if response.status in (301, 302):
                    return response.headers.get('Location')
                elif response.status == 200:
                    # No redirect, return the content URL directly
                    return content_url
                else:
                    raise Exception(f"Failed to get download URL: HTTP {response.status}")
    
    def _encode_sharing_url(self, url: str) -> str:
        """
        Encode a sharing URL for use with the Graph shares API
        
        The encoding format is: u!{base64url encoded URL}
        See: https://docs.microsoft.com/en-us/graph/api/shares-get
        """
        # Base64 URL-safe encode
        encoded = base64.urlsafe_b64encode(url.encode()).decode()
        # Remove padding
        encoded = encoded.rstrip('=')
        # Add prefix
        return f"u!{encoded}"
    
    async def download_file_content(
        self,
        download_url: str,
        token: str = None
    ) -> bytes:
        """
        Download file content from a download URL
        
        Args:
            download_url: Direct download URL
            token: Access token (may not be needed for pre-authenticated URLs)
            
        Returns:
            File content as bytes
        """
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download file: HTTP {response.status}")
                return await response.read()
    
    async def close(self):
        """Clean up resources"""
        if self._credential:
            await self._credential.close()


# Singleton instance
_graph_client: Optional[GraphClient] = None


def get_graph_client() -> GraphClient:
    """Get or create the Graph client singleton"""
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphClient()
    return _graph_client
