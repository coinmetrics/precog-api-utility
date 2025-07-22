"""
Authentication utilities for Precog API
"""

import requests
import bittensor as bt
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

from .config import get_config


# Create a shared session for all auth operations
_session = requests.Session()


def setup_authentication() -> bool:
    """
    Set up authentication for Precog API using current configuration
    
    This function will:
    1. Check if valid tokens already exist
    2. If not, authenticate with your Bittensor wallet
    3. Save tokens for future use
    
    Returns:
        bool: True if setup was successful
    """
    config = get_config()
    
    wallet_name = config.get_wallet_name()
    if not wallet_name:
        print("ERROR: No wallet name configured.")
        print("Please configure wallet name first.")
        return False
    
    api_url = os.getenv("API_URL", "https://precog-api.example.com")
    token_file = config.get_token_file()
    
    # Create token directory if it doesn't exist
    os.makedirs(os.path.dirname(token_file), exist_ok=True)
    
    print("=== Precog API Authentication ===")
    print(f"Wallet: {wallet_name}")
    print(f"Token file: {token_file}")
    print()
    
    # Check if we already have valid tokens
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                tokens = json.load(f)
            
            if not _is_token_expired(tokens.get('expires_at')):
                print(f"✓ Valid tokens found in {token_file}")
                print(f"  Access token expires: {tokens.get('expires_at')}")
                return True
            else:
                print(f"! Found expired tokens in {token_file}")
        except Exception as e:
            print(f"! Error reading token file: {e}")
    
    # Need to authenticate
    print(f"Authenticating with wallet: {wallet_name}")
    
    try:
        # Step 1: Get challenge
        print("1. Requesting authentication challenge...")
        response = _session.get(f"{api_url}/auth/challenge")
        response.raise_for_status()
        challenge = response.json()
        
        # Step 2: Sign challenge with wallet
        print("2. Signing challenge with wallet...")
        wallet = bt.wallet(name=wallet_name)
        coldkey = wallet.coldkey
        signature = coldkey.sign(challenge['challenge_text'])
        
        print(f"   Coldkey: {coldkey.ss58_address}")
        
        # Step 3: Authenticate and get tokens
        print("3. Authenticating and requesting tokens...")
        auth_data = {
            "challenge_id": challenge["challenge_id"],
            "signature": signature.hex(),
            "coldkey": coldkey.ss58_address
        }
        
        response = _session.post(f"{api_url}/auth/authenticate", json=auth_data)
        response.raise_for_status()
        
        tokens = response.json()
        
        # Step 4: Save tokens
        now = datetime.now(timezone.utc)
        expires_in = tokens['expires_in']
        refresh_expires_in = tokens.get('refresh_expires_in', expires_in)  # Fallback to expires_in if not provided
        
        access_expires_at = now + timedelta(seconds=expires_in)
        refresh_expires_at = now + timedelta(seconds=refresh_expires_in)
        
        token_data = {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "access_expires_at": access_expires_at.isoformat(),  # Access token expiry
            "expires_at": refresh_expires_at.isoformat(),  # Refresh token expiry
            "wallet_name": wallet_name,
            "api_url": api_url
        }
        
        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✓ Authentication successful!")
        print(f"  Tokens saved to: {token_file}")
        print(f"  Access token expires: {access_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Refresh token expires: {refresh_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Access token expires in: {expires_in} seconds")
        print(f"  Refresh token expires in: {refresh_expires_in} seconds")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API request failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False


def _is_token_expired(expires_at_str: Optional[str]) -> bool:
    """Check if token is expired (with smart buffer)"""
    if not expires_at_str:
        return True
    
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        # Calculate time until expiry
        time_until_expiry = (expires_at - now).total_seconds()
        
        # Use smart buffer: 30 seconds or 10% of token lifetime, whichever is smaller
        buffer_seconds = min(30, max(5, time_until_expiry * 0.1))
        buffer = timedelta(seconds=buffer_seconds)
        
        return now >= (expires_at - buffer)
    except:
        return True


def load_tokens(token_file: str = None) -> Dict[str, Any]:
    """Load tokens from file"""
    if token_file is None:
        config = get_config()
        token_file = config.get_token_file()
    
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_tokens(tokens: Dict[str, Any], token_file: str = None):
    """Save tokens to file"""
    if token_file is None:
        config = get_config()
        token_file = config.get_token_file()
    
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)


def refresh_access_token(refresh_token: str, api_url: str) -> Optional[Dict[str, Any]]:
    """Refresh access token using refresh token"""
    try:
        response = _session.post(f"{api_url}/auth/refresh", json={"refresh_token": refresh_token})
        response.raise_for_status()
        
        tokens = response.json()
        now = datetime.now(timezone.utc)
        expires_in = tokens['expires_in']
        refresh_expires_in = tokens.get('refresh_expires_in', expires_in)  # Fallback to expires_in if not provided
        
        access_expires_at = now + timedelta(seconds=expires_in)
        refresh_expires_at = now + timedelta(seconds=refresh_expires_in)
        
        return {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "access_expires_at": access_expires_at.isoformat(),  # Access token expiry
            "expires_at": refresh_expires_at.isoformat()  # Refresh token expiry
        }
        
    except Exception as e:
        return None


def get_valid_access_token() -> Optional[str]:
    """Get access token (caller handles refresh on failure)"""
    config = get_config()
    
    if not config.get_wallet_name():
        return None
    
    tokens = load_tokens()
    return tokens.get('access_token')

def refresh_tokens_if_needed() -> bool:
    """Try to refresh tokens if access token is expired/expiring and refresh token is still valid"""
    config = get_config()
    tokens = load_tokens()
    
    if not tokens.get('refresh_token'):
        return False
    
    # Check if refresh token is still valid
    if tokens.get('expires_at'):
        expires_at = datetime.fromisoformat(tokens['expires_at'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        if now >= expires_at:  # Refresh token expired
            return False
    
    # Check if we need to refresh (access token expired or close to expiry)
    if not tokens.get('access_expires_at'):
        return False  # No access token info
    
    access_expires = datetime.fromisoformat(tokens['access_expires_at'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    # Refresh if access token expires in less than 30 seconds
    if now < (access_expires - timedelta(seconds=30)):
        return False  # Token still has more than 30 seconds
    
    refreshed = refresh_access_token(tokens['refresh_token'], os.getenv("API_URL", "https://precog-api.example.com"))
    if refreshed:
        tokens.update(refreshed)
        save_tokens(tokens)
        return True
    else:
        return False