"""
User-facing messages for the PlanSet Review Bot
"""

# Support contact info
SUPPORT_CONTACT = "Jonah Knip on Teams"

# Welcome / Help message
WELCOME_MESSAGE = """**PlanSet Review Agent**

I can review your civil engineering planset PDFs and generate a comprehensive PM review report.

**How to use:**

1. **Direct upload** (files under 25MB):
   - Click the attachment icon (paperclip)
   - Select your PDF planset
   - Send the message

2. **OneDrive/SharePoint link** (files up to 500MB):
   - Upload your planset to OneDrive or SharePoint
   - Copy the sharing link
   - Paste the link in a message and send

**Supported formats:** PDF files only

**What you'll get:**
- Project information extraction
- Sheet index and discipline coverage
- Key features identification
- PM review flags and action items
- Recommendations for coordination, permits, and scheduling

Just send me a planset to get started!
"""

# Processing messages
PROCESSING_START = "Received your planset. Processing now... This may take a minute for large files."

PROCESSING_DOWNLOAD = "Downloading planset from {source}..."

PROCESSING_ANALYSIS = "Analyzing planset ({pages} pages)..."

PROCESSING_COMPLETE = "Analysis complete! Here's your review report:"

# Error messages
ERROR_NO_ATTACHMENT = """I didn't receive a PDF file or OneDrive/SharePoint link.

**To submit a planset:**
- Attach a PDF file directly (under 25MB), or
- Paste a OneDrive/SharePoint sharing link (for files up to 500MB)

Need help? Contact {support}
""".format(support=SUPPORT_CONTACT)

ERROR_INVALID_FILE_TYPE = """Sorry, I can only process PDF files.

You sent: **{filename}**

Please send a PDF planset file. If you need to convert your plans to PDF, most CAD software can export to PDF format.

Need help? Contact {support}
""".format(support=SUPPORT_CONTACT, filename="{filename}")

ERROR_FILE_TOO_LARGE = """The file is too large to process directly.

**File size:** {size_mb:.1f} MB
**Maximum direct upload:** 25 MB

**For large files:**
1. Upload your planset to OneDrive or SharePoint
2. Create a sharing link
3. Send me the link instead

Need help? Contact {support}
""".format(support=SUPPORT_CONTACT, size_mb="{size_mb}")

ERROR_DOWNLOAD_FAILED = """I couldn't download the file from the link you provided.

**Possible causes:**
- The link may have expired
- The file may have been moved or deleted
- I may not have permission to access it

**To fix:**
1. Make sure the file still exists
2. Create a new sharing link with "Anyone with the link can view" permission
3. Send me the new link

Need help? Contact {support}
""".format(support=SUPPORT_CONTACT)

ERROR_INVALID_LINK = """I couldn't recognize that as a OneDrive or SharePoint link.

**Supported link formats:**
- `https://[company].sharepoint.com/...`
- `https://[company]-my.sharepoint.com/...`
- `https://onedrive.live.com/...`
- `https://1drv.ms/...`

Please share a valid OneDrive or SharePoint link to your planset.

Need help? Contact {support}
""".format(support=SUPPORT_CONTACT)

ERROR_PROCESSING_FAILED = """Sorry, I encountered an error while analyzing your planset.

**Error:** {error}

**What to try:**
- Make sure the PDF is not corrupted or password-protected
- Try re-uploading the file
- If the problem persists, the PDF may use an unsupported format

Need help? Contact {support}
""".format(support=SUPPORT_CONTACT, error="{error}")

ERROR_GENERIC = """Sorry, something went wrong.

**Error:** {error}

Please try again. If the problem persists, contact {support}
""".format(support=SUPPORT_CONTACT, error="{error}")


def format_error_invalid_file_type(filename: str) -> str:
    """Format the invalid file type error with the actual filename"""
    return ERROR_INVALID_FILE_TYPE.replace("{filename}", filename)


def format_error_file_too_large(size_mb: float) -> str:
    """Format the file too large error with the actual size"""
    return ERROR_FILE_TOO_LARGE.replace("{size_mb}", f"{size_mb:.1f}")


def format_error_processing_failed(error: str) -> str:
    """Format the processing failed error with the actual error message"""
    return ERROR_PROCESSING_FAILED.replace("{error}", str(error))


def format_error_generic(error: str) -> str:
    """Format the generic error with the actual error message"""
    return ERROR_GENERIC.replace("{error}", str(error))


def format_processing_download(source: str) -> str:
    """Format the download progress message"""
    return PROCESSING_DOWNLOAD.format(source=source)


def format_processing_analysis(pages: int) -> str:
    """Format the analysis progress message"""
    return PROCESSING_ANALYSIS.format(pages=pages)
