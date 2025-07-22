"""
Precog API Client with automatic token management
"""

import requests
import os
from datetime import datetime
from typing import Dict, Any, Optional

from .auth import get_valid_access_token, refresh_tokens_if_needed
from .config import get_config


class PrecogClient:
    """
    Simple client for Precog API with automatic token management
    
    Usage:
        # One-time setup
        from precog_api import setup_authentication
        setup_authentication("your_wallet_name")
        
        # Then use the client
        client = PrecogClient()
        predictions = client.get_recent_predictions()
    """
    
    def __init__(self):
        """
        Initialize Precog API client
        
        Configuration is loaded from ~/.precog/config.json
        """
        config = get_config()
        self.wallet_name = config.get_wallet_name()
        self.api_url = os.getenv("API_URL", "https://precog-api.example.com")
        self.token_file = config.get_token_file()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with valid authorization token"""
        token = get_valid_access_token()
        if not token:
            raise Exception(
                "Authentication tokens have expired. Please run 'precog authenticate' to re-authenticate."
            )
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated API request with automatic token refresh"""
        url = f"{self.api_url}{endpoint}"
        
        # Proactively check and refresh if needed
        refresh_tokens_if_needed()
        
        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Try once more with refresh (in case token just expired)
                if refresh_tokens_if_needed():
                    headers = self._get_headers()
                    response = requests.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    return response.json()
                else:
                    raise Exception(
                        "Authentication tokens have expired. Please run 'precog authenticate' to re-authenticate."
                    )
            else:
                raise
    
    def get_recent_predictions(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get recent predictions for all miners
        
        Args:
            limit: Maximum number of predictions to return (1-10000)
            
        Returns:
            dict: API response containing predictions data
        """
        if not isinstance(limit, int) or limit <= 0 or limit > 10000:
            raise ValueError("Limit must be a positive integer between 1 and 10000")
        
        return self._make_request("/predictions/recent", {"limit": limit})
    
    def get_recent_predictions_by_uid(self, miner_uid: int, limit: int = 100) -> Dict[str, Any]:
        """
        Get recent predictions for a specific miner by UID
        
        Args:
            miner_uid: Miner's unique identifier (0-255)
            limit: Maximum number of predictions to return (1-10000)
            
        Returns:
            dict: API response containing predictions for the miner
        """
        if not isinstance(miner_uid, int) or miner_uid < 0 or miner_uid > 255:
            raise ValueError("Miner UID must be an integer between 0 and 255")
        
        if not isinstance(limit, int) or limit <= 0 or limit > 10000:
            raise ValueError("Limit must be a positive integer between 1 and 10000")
        
        return self._make_request(f"/predictions/recent/uid/{miner_uid}", {"limit": limit})
    
    def get_recent_predictions_by_hotkey(self, miner_hotkey: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get recent predictions for a specific miner by hotkey
        
        Args:
            miner_hotkey: Miner's hotkey (SS58 address)
            limit: Maximum number of predictions to return (1-10000)
            
        Returns:
            dict: API response containing predictions for the miner
        """
        if not isinstance(miner_hotkey, str) or len(miner_hotkey) != 48:
            raise ValueError("Miner hotkey must be a 48-character SS58 address")
        
        if not isinstance(limit, int) or limit <= 0 or limit > 10000:
            raise ValueError("Limit must be a positive integer between 1 and 10000")
        
        return self._make_request(f"/predictions/recent/hotkey/{miner_hotkey}", {"limit": limit})
    
    def get_historical_predictions(
        self, 
        start_date: datetime, 
        end_date: datetime,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get historical predictions for all miners
        
        Args:
            start_date: Start date for query
            end_date: End date for query
            page: Page number (1-based)
            page_size: Number of items per page (100-10000)
            
        Returns:
            dict: API response with predictions and pagination info
        """
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise ValueError("start_date and end_date must be datetime objects")
        
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        
        if not isinstance(page, int) or page < 1:
            raise ValueError("Page must be a positive integer")
        
        if not isinstance(page_size, int) or page_size < 100 or page_size > 10000:
            raise ValueError("Page size must be between 100 and 10000")
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "page": page,
            "page_size": page_size
        }
        
        return self._make_request("/predictions/historical", params)
    
    def get_historical_predictions_by_uid(
        self, 
        miner_uid: int,
        start_date: datetime, 
        end_date: datetime,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get historical predictions for a specific miner by UID
        
        Args:
            miner_uid: Miner's unique identifier (0-255)
            start_date: Start date for query
            end_date: End date for query
            page: Page number (1-based)
            page_size: Number of items per page (100-10000)
            
        Returns:
            dict: API response with predictions and pagination info
        """
        if not isinstance(miner_uid, int) or miner_uid < 0 or miner_uid > 255:
            raise ValueError("Miner UID must be an integer between 0 and 255")
        
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise ValueError("start_date and end_date must be datetime objects")
        
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        
        if not isinstance(page, int) or page < 1:
            raise ValueError("Page must be a positive integer")
        
        if not isinstance(page_size, int) or page_size < 100 or page_size > 10000:
            raise ValueError("Page size must be between 100 and 10000")
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "page": page,
            "page_size": page_size
        }
        
        return self._make_request(f"/predictions/historical/uid/{miner_uid}", params)
    
    def get_historical_predictions_by_hotkey(
        self, 
        miner_hotkey: str,
        start_date: datetime, 
        end_date: datetime,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        Get historical predictions for a specific miner by hotkey
        
        Args:
            miner_hotkey: Miner's hotkey (SS58 address)
            start_date: Start date for query
            end_date: End date for query
            page: Page number (1-based)
            page_size: Number of items per page (100-10000)
            
        Returns:
            dict: API response with predictions and pagination info
        """
        if not isinstance(miner_hotkey, str) or len(miner_hotkey) != 48:
            raise ValueError("Miner hotkey must be a 48-character SS58 address")
        
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise ValueError("start_date and end_date must be datetime objects")
        
        if start_date >= end_date:
            raise ValueError("start_date must be before end_date")
        
        if not isinstance(page, int) or page < 1:
            raise ValueError("Page must be a positive integer")
        
        if not isinstance(page_size, int) or page_size < 100 or page_size > 10000:
            raise ValueError("Page size must be between 100 and 10000")
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "page": page,
            "page_size": page_size
        }
        
        return self._make_request(f"/predictions/historical/hotkey/{miner_hotkey}", params)