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
from .constants import API_URL


def setup_authentication(wallet_name: str = None) -> bool:
    """
    Set up authentication for Precog API
    
    This function will:
    1. Check if valid tokens already exist
    2. If not, authenticate with your Bittensor wallet
    3. Save tokens for future use
    
    Args:
        wallet_name: Name of your Bittensor wallet (uses config if not provided)
        
    Returns:
        bool: True if setup was successful
    """
    config = get_config()
    
    # Use provided wallet name or get from config
    if wallet_name:
        config.set("wallet_name", wallet_name)
        config.save_config()
    else:
        wallet_name = config.get_wallet_name()
    
    if not wallet_name:
        print("ERROR: No wallet name configured.")
        print("Please either:")
        print("  1. Pass wallet_name parameter: setup_authentication('your_wallet')")
        print("  2. Configure it first: from precog_api.config import get_config; get_config().set('wallet_name', 'your_wallet')")
        return False
    
    api_url = API_URL
    token_file = config.get_token_file()
    
    # Create token directory if it doesn't exist
    os.makedirs(os.path.dirname(token_file), exist_ok=True)
    
    print("=== Precog API Authentication Setup ===")
    print(f"Wallet: {wallet_name}")
    print(f"API URL: {api_url}")
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
        response = requests.get(f"{api_url}/auth/challenge")
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
        
        response = requests.post(f"{api_url}/auth/authenticate", json=auth_data)
        response.raise_for_status()
        
        tokens = response.json()
        
        # Step 4: Save tokens
        expires_in = tokens['expires_in']
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        token_data = {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "expires_at": expires_at.isoformat(),
            "refresh_expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "wallet_name": wallet_name,
            "api_url": api_url
        }
        
        with open(token_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print(f"✓ Authentication successful!")
        print(f"  Tokens saved to: {token_file}")
        print(f"  Access token expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  Token expires in: {expires_in} seconds ({expires_in//3600} hours)")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ API request failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False


def _is_token_expired(expires_at_str: Optional[str]) -> bool:
    """Check if token is expired (with 5 minute buffer)"""
    if not expires_at_str:
        return True
    
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        buffer = timedelta(minutes=5)
        return datetime.now(timezone.utc) >= (expires_at - buffer)
    except:
        return True


def load_tokens(token_file: str = "precog_tokens.json") -> Dict[str, Any]:
    """Load tokens from file"""
    if os.path.exists(token_file):
        try:
            with open(token_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_tokens(tokens: Dict[str, Any], token_file: str = "precog_tokens.json"):
    """Save tokens to file"""
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)


def refresh_access_token(refresh_token: str, api_url: str) -> Optional[Dict[str, Any]]:
    """Refresh access token using refresh token"""
    try:
        response = requests.post(f"{api_url}/auth/refresh", json={"refresh_token": refresh_token})
        response.raise_for_status()
        
        tokens = response.json()
        expires_in = tokens['expires_in']
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "expires_at": expires_at.isoformat()
        }
        
    except Exception:
        return None


def get_valid_access_token() -> Optional[str]:
    """Get a valid access token, refreshing or re-authenticating as needed"""
    config = get_config()
    
    wallet_name = config.get_wallet_name()
    api_url = API_URL
    token_file = config.get_token_file()
    
    if not wallet_name:
        return None
    
    tokens = load_tokens(token_file)
    
    # Check if we have a valid access token
    if tokens.get('access_token') and not _is_token_expired(tokens.get('expires_at')):
        return tokens['access_token']
    
    # Try to refresh if we have a valid refresh token
    if tokens.get('refresh_token') and not _is_token_expired(tokens.get('refresh_expires_at')):
        refreshed = refresh_access_token(tokens['refresh_token'], api_url)
        if refreshed:
            # Update stored tokens
            tokens.update(refreshed)
            save_tokens(tokens, token_file)
            return refreshed['access_token']
    
    # If refresh failed, try to re-authenticate
    if setup_authentication(wallet_name):
        tokens = load_tokens(token_file)
        return tokens.get('access_token')
    
    return None