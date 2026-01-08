# PlanSet Review Agent

A simple web application for civil engineering planset PDF review. Upload a PDF or paste a OneDrive/SharePoint link to get a comprehensive PM review report.

## Features

- **Direct PDF Upload**: Upload plansets of any size directly
- **OneDrive/SharePoint Links**: Paste sharing links to review files stored in the cloud
- **Comprehensive Analysis**: Extracts project info, sheet index, disciplines, key features
- **PM Review Reports**: Generates actionable recommendations for coordination, permits, and scheduling
- **Copy to Clipboard**: Easy copy button to paste report into emails

## How to Use

1. Go to the web app URL
2. Either:
   - **Upload a PDF**: Click the upload area or drag & drop your planset
   - **Paste a link**: Paste a OneDrive or SharePoint sharing link
3. Click "Review Planset"
4. Wait for analysis (may take a minute for large files)
5. Copy the report and email it to the drawer

## Project Structure

```
planset-review-agent/
├── agent/
│   ├── __init__.py
│   └── plan_reviewer.py      # Core PDF analysis engine
├── templates/
│   └── index.html            # Web interface
├── app.py                    # Flask web application
├── requirements.txt          # Python dependencies
├── Procfile                  # For Heroku/Railway deployment
├── railway.json              # Railway deployment config
├── render.yaml               # Render deployment config
└── README.md
```

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open http://localhost:5000 in your browser
```

## Deployment Options

### Railway (Recommended - Free Tier)

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select `planset-review-agent`
5. Railway auto-detects Python and deploys
6. Get your public URL from the deployment settings

### Render (Free Tier)

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Click "New" → "Web Service"
4. Connect your GitHub repo
5. Render uses `render.yaml` for configuration
6. Deploy and get your URL

### Heroku

```bash
# Install Heroku CLI, then:
heroku create planset-review
git push heroku main
heroku open
```

## Supported Link Formats

- `https://company.sharepoint.com/...`
- `https://company-my.sharepoint.com/...`
- `https://onedrive.live.com/...`
- `https://1drv.ms/...`

**Note**: The sharing link must have "Anyone with the link can view" permission for the download to work without authentication.

## Support

Questions? Contact Jonah Knip

## License

Private - Internal use only
