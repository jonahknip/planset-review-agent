# PlanSet Review Agent

A Microsoft Teams bot that analyzes civil engineering planset PDFs and generates comprehensive PM review reports.

## Features

- **Direct PDF Upload**: Attach PDFs up to 25MB directly in Teams
- **OneDrive/SharePoint Integration**: Share links to plansets up to 500MB
- **Comprehensive Analysis**: Extracts project info, sheet index, disciplines, key features
- **PM Review Reports**: Generates actionable recommendations for coordination, permits, and scheduling

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Microsoft      │────>│  Azure Bot       │────>│  Azure Function │
│  Teams          │<────│  Service         │<────│  (Python)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                        ┌──────────────────┐             │
                        │  Microsoft Graph │<────────────┤
                        │  API             │             │
                        └──────────────────┘             │
                                                         │
                        ┌──────────────────┐             │
                        │  Azure Blob      │<────────────┘
                        │  Storage         │
                        └──────────────────┘
```

## Project Structure

```
planset-review-agent/
├── agent/
│   ├── __init__.py
│   └── plan_reviewer.py      # Core PDF analysis engine
├── bot/
│   ├── __init__.py
│   ├── bot.py                # Teams bot handler
│   ├── config.py             # Configuration management
│   ├── file_handler.py       # File download handling
│   └── messages.py           # User-facing messages
├── services/
│   ├── __init__.py
│   └── graph_client.py       # Microsoft Graph API client
├── teams_app/
│   ├── manifest.json         # Teams app manifest
│   ├── color.png            # Bot icon (192x192)
│   └── outline.png          # Bot outline icon (32x32)
├── function_app.py           # Azure Functions entry point
├── host.json                 # Azure Functions config
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── README.md
```

## Prerequisites

- Azure subscription
- Microsoft 365 tenant with Teams
- Python 3.9+
- Azure CLI
- Azure Functions Core Tools

## Azure Resources Required

| Resource | Purpose | Tier |
|----------|---------|------|
| Resource Group | Container for all resources | - |
| Azure Bot Service | Bot registration | F0 (Free) |
| Azure AD App Registration | Authentication | - |
| Azure Functions | Serverless compute | Consumption |
| Azure Blob Storage | Temp file storage | Standard |

## Setup Instructions

### 1. Create Azure Resources

```bash
# Login to Azure
az login

# Create resource group
az group create --name planset-review-agent-rg --location eastus

# Create storage account
az storage account create \
  --name plansetreviewstorage \
  --resource-group planset-review-agent-rg \
  --location eastus \
  --sku Standard_LRS

# Create function app
az functionapp create \
  --name planset-review-bot \
  --resource-group planset-review-agent-rg \
  --storage-account plansetreviewstorage \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4
```

### 2. Register Azure AD App

1. Go to [Azure Portal](https://portal.azure.com) > Azure Active Directory > App registrations
2. Click "New registration"
   - Name: `PlanSet Review Bot`
   - Supported account types: "Accounts in this organizational directory only"
3. After creation, note the **Application (client) ID** and **Directory (tenant) ID**
4. Go to "Certificates & secrets" > "New client secret"
   - Note the secret value (you won't see it again!)
5. Go to "API permissions" > "Add a permission"
   - Microsoft Graph > Delegated permissions
   - Add: `Files.Read.All`, `Sites.Read.All`
6. Click "Grant admin consent" (requires admin)

### 3. Create Azure Bot

1. Go to [Azure Portal](https://portal.azure.com) > Create a resource > "Azure Bot"
2. Configure:
   - Bot handle: `planset-review-bot`
   - Pricing tier: F0 (Free)
   - Microsoft App ID: Use the App Registration from step 2
3. After creation, go to Channels > Microsoft Teams > Enable

### 4. Configure Environment Variables

Set these in your Azure Function App settings:

```bash
az functionapp config appsettings set \
  --name planset-review-bot \
  --resource-group planset-review-agent-rg \
  --settings \
    BOT_APP_ID="your-bot-app-id" \
    BOT_APP_PASSWORD="your-bot-app-password" \
    AZURE_TENANT_ID="your-tenant-id" \
    AZURE_CLIENT_ID="your-client-id" \
    AZURE_CLIENT_SECRET="your-client-secret" \
    AZURE_STORAGE_CONNECTION_STRING="your-storage-connection-string"
```

### 5. Deploy the Function

```bash
# From the project directory
func azure functionapp publish planset-review-bot
```

### 6. Configure Bot Messaging Endpoint

1. Go to Azure Portal > your Bot Service > Configuration
2. Set Messaging endpoint: `https://planset-review-bot.azurewebsites.net/api/messages`

### 7. Create Teams App Package

1. Update `teams_app/manifest.json`:
   - Replace `{{BOT_APP_ID}}` with your actual Bot App ID
2. Create the app package:
   ```bash
   cd teams_app
   zip -r ../planset-review-bot.zip manifest.json color.png outline.png
   ```
3. Upload to Teams Admin Center or sideload for testing

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your values

# Run locally
func start
```

For local testing with Teams, use ngrok:
```bash
ngrok http 7071
# Update Bot messaging endpoint to ngrok URL
```

## Usage

### Direct Upload
1. Open a chat with the bot in Teams
2. Click the attachment icon
3. Select your PDF planset
4. Send the message

### OneDrive/SharePoint Link
1. Upload your planset to OneDrive or SharePoint
2. Create a sharing link
3. Paste the link in a message to the bot
4. Send the message

## Support

Contact Jonah Knip on Teams for help.

## License

Private - Internal use only
