"""
Precog API Client

A Python client for the Precog API (Bittensor Subnet 55) with automatic token management.
"""

from .client import PrecogClient
from .auth import setup_authentication

__version__ = "0.1.0"
__all__ = ["PrecogClient", "setup_authentication"]