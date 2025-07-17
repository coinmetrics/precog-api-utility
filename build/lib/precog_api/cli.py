#!/usr/bin/env python3
"""
Interactive CLI for Precog API setup
"""

import sys
import os
from .config import get_config
from .auth import setup_authentication

def setup_command():
    """Interactive setup command"""
    print("=== Precog API Setup ===")
    print()
    
    config = get_config()
    
    # Check if already configured
    if config.is_configured():
        print("✓ Precog API is already configured")
        config.show_config()
        print()
        
        response = input("Do you want to reconfigure? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Setup cancelled.")
            return
        print()
    
    # Get wallet name
    print("Enter your Bittensor wallet name.")
    print("This should be the name of your wallet directory in ~/.bittensor/wallets/")
    print()
    
    current_wallet = config.get_wallet_name()
    if current_wallet:
        wallet_prompt = f"Wallet name [{current_wallet}]: "
    else:
        wallet_prompt = "Wallet name: "
    
    while True:
        wallet_name = input(wallet_prompt).strip()
        
        # Use current wallet if just pressed enter
        if not wallet_name and current_wallet:
            wallet_name = current_wallet
        
        if not wallet_name:
            print("❌ Wallet name is required.")
            continue
        
        # Check if wallet exists
        wallet_path = os.path.expanduser(f"~/.bittensor/wallets/{wallet_name}")
        coldkey_path = os.path.join(wallet_path, "coldkey")
        
        if not os.path.exists(wallet_path):
            print(f"❌ Wallet directory not found: {wallet_path}")
            print("Available wallets:")
            wallets_dir = os.path.expanduser("~/.bittensor/wallets")
            if os.path.exists(wallets_dir):
                for item in os.listdir(wallets_dir):
                    if os.path.isdir(os.path.join(wallets_dir, item)):
                        print(f"  - {item}")
            continue
        
        if not os.path.exists(coldkey_path):
            print(f"❌ Coldkey not found in wallet: {coldkey_path}")
            continue
        
        break
    
    # Get token file path (optional)
    print()
    print("Token file location (optional).")
    print("This is where your API tokens will be stored.")
    print()
    
    current_token_file = config.get_token_file()
    token_file_prompt = f"Token file [{current_token_file}]: "
    
    token_file = input(token_file_prompt).strip()
    if not token_file:
        token_file = current_token_file
    
    # Expand ~ in path
    token_file = os.path.expanduser(token_file)
    
    # Update config
    config.set("wallet_name", wallet_name)
    config.set("token_file", token_file)
    config.save_config()
    
    print()
    print("Configuration saved!")
    config.show_config()
    
    # Run authentication
    print()
    print("Now authenticating with your wallet...")
    print("You will be prompted for your wallet password.")
    print()
    
    if setup_authentication(wallet_name):
        print()
        print("🎉 Setup completed successfully!")
        print()
        print("You can now use the Precog API:")
        print("  from precog_api import PrecogClient")
        print("  client = PrecogClient()")
        print("  predictions = client.get_recent_predictions()")
        print()
        print("For help, see the documentation or run: precog --help")
    else:
        print()
        print("❌ Authentication failed.")
        print("Your configuration has been saved, but authentication was not successful.")
        print("You can try again by running: precog setup")

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: precog <command>")
        print("Commands:")
        print("  setup    Interactive setup")
        print("  status   Show current configuration")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "setup":
        setup_command()
    elif command == "status":
        config = get_config()
        if config.is_configured():
            print("✓ Precog API is configured")
            config.show_config()
        else:
            print("❌ Precog API is not configured")
            print("Run 'precog setup' to get started")
    else:
        print(f"Unknown command: {command}")
        print("Available commands: setup, status")
        sys.exit(1)

if __name__ == "__main__":
    main()