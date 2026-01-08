"""
PlanSet Review Web App
Simple web interface for civil engineering planset PDF review
"""

import os
import tempfile
import logging
import re
import traceback
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from agent.plan_reviewer import CivilEngineeringPMAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload

# Allowed extensions
ALLOWED_EXTENSIONS = {'.pdf'}

# OneDrive/SharePoint URL patterns
SHARE_URL_PATTERNS = [
    r'https?://[a-zA-Z0-9-]+\.sharepoint\.com/.*',
    r'https?://[a-zA-Z0-9-]+-my\.sharepoint\.com/.*',
    r'https?://onedrive\.live\.com/.*',
    r'https?://1drv\.ms/.*',
]


def allowed_file(filename: str) -> bool:
    """Check if file has allowed extension"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def is_share_url(text: str) -> bool:
    """Check if text is a OneDrive/SharePoint URL"""
    for pattern in SHARE_URL_PATTERNS:
        if re.match(pattern, text.strip(), re.IGNORECASE):
            return True
    return False


def download_from_share_url(url: str) -> tuple[str, str]:
    """
    Download a file from OneDrive/SharePoint sharing URL
    
    Returns tuple of (local_path, filename)
    """
    import requests
    
    url = url.strip()
    logger.info(f"Attempting to download from: {url}")
    
    # Try to get a direct download URL
    # For OneDrive/SharePoint, we can often modify the URL to get direct download
    download_url = url
    
    # Handle different URL formats
    if '1drv.ms' in url:
        # Short URL - need to follow redirect
        response = requests.head(url, allow_redirects=True)
        download_url = response.url
    
    # Try to convert to direct download URL
    if 'sharepoint.com' in download_url or 'onedrive.live.com' in download_url:
        # Replace sharing indicator with download
        if '?e=' in download_url:
            download_url = download_url.split('?e=')[0]
        if ':b:' in download_url:
            # This is a file link, try to get download URL
            download_url = download_url.replace(':b:', ':b:/') + '?download=1'
        elif 'download=1' not in download_url:
            separator = '&' if '?' in download_url else '?'
            download_url = download_url + separator + 'download=1'
    
    logger.info(f"Download URL: {download_url}")
    
    # Download the file
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(download_url, headers=headers, stream=True, timeout=300)
    
    if response.status_code != 200:
        raise Exception(f"Failed to download file: HTTP {response.status_code}")
    
    # Try to get filename from headers
    content_disposition = response.headers.get('Content-Disposition', '')
    filename = 'planset.pdf'
    
    if 'filename=' in content_disposition:
        # Extract filename from header
        match = re.search(r'filename[*]?=["\']?([^"\';\n]+)', content_disposition)
        if match:
            filename = match.group(1).strip()
    
    # Verify it's a PDF
    content_type = response.headers.get('Content-Type', '')
    if 'pdf' not in content_type.lower() and not filename.lower().endswith('.pdf'):
        # Check first bytes for PDF signature
        first_bytes = response.content[:5]
        if first_bytes != b'%PDF-':
            raise Exception("The shared file does not appear to be a PDF")
    
    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    safe_filename = secure_filename(filename)
    if not safe_filename.lower().endswith('.pdf'):
        safe_filename += '.pdf'
    
    local_path = os.path.join(temp_dir, safe_filename)
    
    with open(local_path, 'wb') as f:
        f.write(response.content)
    
    file_size = os.path.getsize(local_path)
    logger.info(f"Downloaded {safe_filename} ({file_size} bytes)")
    
    return local_path, safe_filename


def analyze_planset(pdf_path: str) -> dict:
    """
    Analyze a planset PDF and return results
    """
    try:
        agent = CivilEngineeringPMAgent(pdf_path)
        
        # Get page count
        page_count = len(agent.doc)
        
        # Generate report
        report = agent.generate_summary_report()
        
        # Get JSON data for structured display
        json_data = agent.export_json()
        
        return {
            'success': True,
            'page_count': page_count,
            'report': report,
            'data': json_data
        }
    except Exception as e:
        logger.error(f"Analysis error: {e}\n{traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/review', methods=['POST'])
def review_planset():
    """
    Review a planset from either file upload or URL
    """
    temp_path = None
    
    try:
        # Check if URL was provided
        share_url = request.form.get('url', '').strip()
        
        if share_url:
            # Download from OneDrive/SharePoint
            if not is_share_url(share_url):
                return jsonify({
                    'success': False,
                    'error': 'Invalid URL. Please provide a OneDrive or SharePoint sharing link.'
                }), 400
            
            try:
                temp_path, filename = download_from_share_url(share_url)
            except Exception as e:
                logger.error(f"Download error: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to download file: {str(e)}'
                }), 400
        
        elif 'file' in request.files:
            # Handle file upload
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400
            
            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'error': 'Invalid file type. Please upload a PDF file.'
                }), 400
            
            # Save uploaded file
            temp_dir = tempfile.mkdtemp()
            filename = secure_filename(file.filename)
            temp_path = os.path.join(temp_dir, filename)
            file.save(temp_path)
            
            logger.info(f"Saved uploaded file: {filename}")
        
        else:
            return jsonify({
                'success': False,
                'error': 'Please upload a PDF file or provide a OneDrive/SharePoint link.'
            }), 400
        
        # Analyze the planset
        result = analyze_planset(temp_path)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
    
    except Exception as e:
        logger.error(f"Review error: {e}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                os.rmdir(os.path.dirname(temp_path))
            except Exception:
                pass


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
