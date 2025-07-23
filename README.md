# Precog API Client

A Python client for the Precog API with automatic token management and Bittensor wallet authentication.

## Features

- **Automatic Authentication**: Uses Bittensor wallet for secure authentication
- **Token Management**: Automatic access token refresh with no user intervention
- **Simple API**: Clean interface for accessing prediction data
- **Error Handling**: Graceful handling of token expiry and network errors

## Installation

```bash
pip install -e .
```

## Quick Start

### 1. Initial Setup


#### API URL Configuration

Set the API endpoint using the `API_URL` environment variable:

```bash
export API_URL="https://precog-api-stg.cnmtrcs.io"
```

If not set, the client will use a default example URL.

#### Get authentication token
Then, authenticate with your Bittensor wallet:

```bash
precog authenticate
```

This will:
- Prompt for your wallet name and password
- Authenticate with the Precog API
- Save tokens for future use

### 2. Use the Client

```python
from precog_api import PrecogClient

# Create client (uses saved authentication)
client = PrecogClient()

# Get recent predictions
predictions = client.get_recent_predictions(limit=10)
print(f"Found {predictions['count']} predictions")

# Get predictions for specific miner
miner_predictions = client.get_recent_predictions_by_uid(42, limit=5)

# Get historical data
from datetime import datetime, timedelta
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
historical = client.get_historical_predictions(start_date, end_date)
```

## Configuration

The client uses a configuration file at `~/.precog/config.json`:

```json
{
  "wallet_name": "your_wallet_name",
  "token_file": "~/.precog/tokens.json"
}
```

## Authentication Requirements

To check the current authentication requirements for the Precog API:

```bash
precog requirements
```

This command will fetch and display:
- Subnet UID
- Minimum stake amount

### Basic Requirements

- **Stake**: Minimum stake required on subnet 55
- **Network**: Connected to Bittensor mainnet (not testnet)
- **Documentation**: For more details on how to create a Bittensor wallet and staking basics, see the [official Bittensor docs](https://docs.bittensor.com/)

## Staking Guide for API Access

To gain access to the Precog API, you must stake Alpha to a hotkey on subnet 55.

### Step-by-Step Staking Process

1. **Check current requirements**:
```bash
precog requirements
```

2. **Check your current stake** (if any):
```bash
btcli stake list --wallet.name YOUR_WALLET_NAME
```

3. **Stake to subnet 55**:
```bash
btcli stake add \
  --wallet.name YOUR_WALLET_NAME \
  --subtensor.network finney \
  --netuid 55 \
  --amount AMOUNT_TO_STAKE
```

Example:
```bash
btcli stake add \
  --wallet.name my_wallet \
  --wallet.hotkey my_hotkey \
  --subtensor.network finney \
  --netuid 55 \
  --amount 1
```

4r. **Verify your stake**:
```bash
btcli stake show --wallet.name YOUR_WALLET_NAME --wallet.hotkey YOUR_HOTKEY_NAME --netuid 55
```

### Important Notes

- Staking is done on **subnet 55** specifically
- Check current requirements with `precog requirements` as they may change

## Authentication

The client uses Bittensor wallet authentication with automatic token refresh:

1. **Initial Authentication**: Run `precog authenticate` to set up
2. **Automatic Refresh**: Access tokens refresh automatically when needed
3. **Re-authentication**: If refresh tokens expire, run `precog authenticate` again

## API Methods

### Recent Predictions

```python
# All miners
predictions = client.get_recent_predictions(limit=100)

# Specific miner by UID
predictions = client.get_recent_predictions_by_uid(miner_uid=42, limit=100)

# Specific miner by hotkey
predictions = client.get_recent_predictions_by_hotkey(
    miner_hotkey="5EgvTaftth7S7Gz9UpnLm2AbCdS9wcw8HeZfVrxNrLippUfC",
    limit=100
)
```

### Historical Predictions

```python
from datetime import datetime

# All miners
historical = client.get_historical_predictions(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 7),
    page=1,
    page_size=1000
)

# Specific miner by UID
historical = client.get_historical_predictions_by_uid(
    miner_uid=42,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 7)
)

# Specific miner by hotkey
historical = client.get_historical_predictions_by_hotkey(
    miner_hotkey="5EgvTaftth7S7Gz9UpnLm2AbCdS9wcw8HeZfVrxNrLippUfC",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 7)
)
```

## Error Handling

The client handles common errors automatically:

- **Token Expiry**: Automatically refreshes access tokens
- **Network Errors**: Raises appropriate exceptions with clear messages
- **Authentication Errors**: Prompts to re-authenticate when needed

```python
try:
    predictions = client.get_recent_predictions()
except Exception as e:
    if "Authentication tokens have expired" in str(e):
        print("Please run: precog authenticate")
    else:
        print(f"API Error: {e}")
```

## API Documentation

For complete API documentation including request/response schemas:

**Swagger UI**: Access the interactive API documentation at `{API_URL}/docs` where `API_URL` is your configured API endpoint.

## Support

For issues and questions, please reach out on Discord:
https://discordapp.com/channels/799672011265015819/1320766712508977192
