"""
Teams Bot Activity Handler for PlanSet Review Bot
"""

import logging
import traceback
from typing import List

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity, ActivityTypes, Attachment

from bot.config import config
from bot.file_handler import FileHandler, DownloadedFile
from bot.messages import (
    WELCOME_MESSAGE,
    PROCESSING_START,
    PROCESSING_COMPLETE,
    ERROR_NO_ATTACHMENT,
    format_error_invalid_file_type,
    format_error_file_too_large,
    format_error_processing_failed,
    format_error_generic,
    format_processing_download,
    format_processing_analysis,
    ERROR_DOWNLOAD_FAILED,
    ERROR_INVALID_LINK,
)
from services.graph_client import get_graph_client
from agent.plan_reviewer import CivilEngineeringPMAgent

logger = logging.getLogger(__name__)


class PlanSetReviewBot(ActivityHandler):
    """
    Bot that handles planset review requests from Microsoft Teams
    """
    
    def __init__(self):
        """Initialize the bot"""
        super().__init__()
        self.file_handler = FileHandler(graph_client=get_graph_client())
    
    async def on_message_activity(self, turn_context: TurnContext):
        """
        Handle incoming messages
        
        Processes:
        1. PDF attachments directly uploaded
        2. OneDrive/SharePoint links in message text
        3. Help requests (shows welcome message)
        """
        try:
            # Check for attachments first
            attachments = turn_context.activity.attachments or []
            pdf_attachments = [a for a in attachments if self._is_pdf_attachment(a)]
            
            if pdf_attachments:
                await self._process_attachment(turn_context, pdf_attachments[0])
                return
            
            # Check for OneDrive/SharePoint links in message text
            message_text = turn_context.activity.text or ""
            onedrive_url = self.file_handler.is_onedrive_sharepoint_url(message_text)
            
            if onedrive_url:
                await self._process_onedrive_link(turn_context, onedrive_url)
                return
            
            # Check for help/greeting keywords
            text_lower = message_text.lower().strip()
            if text_lower in ("help", "hi", "hello", "start", "?", ""):
                await turn_context.send_activity(WELCOME_MESSAGE)
                return
            
            # No valid input found
            await turn_context.send_activity(ERROR_NO_ATTACHMENT)
            
        except Exception as e:
            logger.error(f"Error in on_message_activity: {e}\n{traceback.format_exc()}")
            await turn_context.send_activity(format_error_generic(str(e)))
    
    async def on_members_added_activity(
        self,
        members_added: List,
        turn_context: TurnContext
    ):
        """Send welcome message when bot is added to a conversation"""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(WELCOME_MESSAGE)
    
    def _is_pdf_attachment(self, attachment: Attachment) -> bool:
        """Check if an attachment is a PDF file"""
        if not attachment:
            return False
        
        # Check content type
        content_type = (attachment.content_type or "").lower()
        if "pdf" in content_type:
            return True
        
        # Check filename extension
        name = (attachment.name or "").lower()
        if name.endswith(".pdf"):
            return True
        
        return False
    
    async def _process_attachment(
        self,
        turn_context: TurnContext,
        attachment: Attachment
    ):
        """
        Process a PDF attachment
        """
        filename = attachment.name or "planset.pdf"
        
        # Validate file type
        if not self.file_handler.is_valid_pdf(filename):
            await turn_context.send_activity(format_error_invalid_file_type(filename))
            return
        
        # Send processing message
        await turn_context.send_activity(PROCESSING_START)
        
        downloaded_file = None
        try:
            # Download the attachment
            await turn_context.send_activity(
                format_processing_download("Teams attachment")
            )
            
            # Get the content URL
            content_url = attachment.content_url
            if not content_url:
                raise Exception("Attachment has no content URL")
            
            # Get bot token for download
            # Note: In production, you'd get this from the turn context's credentials
            bot_token = await self._get_bot_token(turn_context)
            
            downloaded_file = await self.file_handler.download_from_attachment(
                content_url=content_url,
                filename=filename,
                bot_token=bot_token
            )
            
            # Check file size
            if downloaded_file.size_mb > 25:
                await turn_context.send_activity(
                    format_error_file_too_large(downloaded_file.size_mb)
                )
                return
            
            # Process the planset
            await self._analyze_and_respond(turn_context, downloaded_file)
            
        except Exception as e:
            logger.error(f"Error processing attachment: {e}\n{traceback.format_exc()}")
            await turn_context.send_activity(format_error_processing_failed(str(e)))
        
        finally:
            # Clean up temp file
            if downloaded_file:
                downloaded_file.cleanup()
    
    async def _process_onedrive_link(
        self,
        turn_context: TurnContext,
        share_url: str
    ):
        """
        Process a OneDrive/SharePoint sharing link
        """
        await turn_context.send_activity(PROCESSING_START)
        
        downloaded_file = None
        try:
            # Download from OneDrive/SharePoint
            await turn_context.send_activity(
                format_processing_download("OneDrive/SharePoint")
            )
            
            # Note: For delegated permissions, you'd need to get the user's token
            # through an OAuth flow. For now, using app permissions.
            downloaded_file = await self.file_handler.download_from_onedrive(
                share_url=share_url,
                user_token=None  # Using app permissions
            )
            
            # Process the planset
            await self._analyze_and_respond(turn_context, downloaded_file)
            
        except Exception as e:
            error_msg = str(e).lower()
            if "not authorized" in error_msg or "401" in error_msg:
                await turn_context.send_activity(ERROR_DOWNLOAD_FAILED)
            elif "not found" in error_msg or "404" in error_msg:
                await turn_context.send_activity(ERROR_DOWNLOAD_FAILED)
            elif "not a pdf" in error_msg:
                await turn_context.send_activity(
                    format_error_invalid_file_type(share_url.split("/")[-1])
                )
            else:
                logger.error(f"Error processing OneDrive link: {e}\n{traceback.format_exc()}")
                await turn_context.send_activity(format_error_processing_failed(str(e)))
        
        finally:
            # Clean up temp file
            if downloaded_file:
                downloaded_file.cleanup()
    
    async def _analyze_and_respond(
        self,
        turn_context: TurnContext,
        downloaded_file: DownloadedFile
    ):
        """
        Run the planset analysis and send the report
        """
        try:
            # Create the PM agent and analyze
            agent = CivilEngineeringPMAgent(downloaded_file.local_path)
            
            # Send progress update
            await turn_context.send_activity(
                format_processing_analysis(agent.doc.page_count)
            )
            
            # Generate the report
            report = agent.generate_summary_report()
            
            # Send completion message
            await turn_context.send_activity(PROCESSING_COMPLETE)
            
            # Send the report (may need to split if too long for Teams)
            await self._send_report(turn_context, report)
            
        except Exception as e:
            logger.error(f"Error analyzing planset: {e}\n{traceback.format_exc()}")
            raise Exception(f"Analysis failed: {e}")
    
    async def _send_report(self, turn_context: TurnContext, report: str):
        """
        Send the report to the user
        
        Teams has a message size limit, so we may need to split large reports
        """
        # Teams message limit is approximately 28KB
        MAX_MESSAGE_LENGTH = 25000
        
        if len(report) <= MAX_MESSAGE_LENGTH:
            # Send as a code block for better formatting
            formatted_report = f"```\n{report}\n```"
            await turn_context.send_activity(formatted_report)
        else:
            # Split into chunks
            chunks = self._split_report(report, MAX_MESSAGE_LENGTH)
            for i, chunk in enumerate(chunks):
                header = f"**Report Part {i+1}/{len(chunks)}**\n"
                formatted_chunk = f"{header}```\n{chunk}\n```"
                await turn_context.send_activity(formatted_chunk)
    
    def _split_report(self, report: str, max_length: int) -> List[str]:
        """Split a report into chunks at section boundaries"""
        chunks = []
        current_chunk = ""
        
        # Try to split at section dividers
        sections = report.split("--------------------------------------------------------------------------------")
        
        for section in sections:
            if len(current_chunk) + len(section) + 80 < max_length:
                if current_chunk:
                    current_chunk += "--------------------------------------------------------------------------------"
                current_chunk += section
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = section
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _get_bot_token(self, turn_context: TurnContext) -> str:
        """
        Get the bot's token for downloading attachments
        
        In a real implementation, this would extract the token from the
        connector client or use the bot's credentials.
        """
        # The token can be extracted from the turn context's connector client
        # For Azure Bot Service, attachments from Teams use a special content URL
        # that may require authentication
        
        # This is a simplified implementation - in production you'd use:
        # credentials = turn_context.adapter.credentials
        # token = await credentials.get_token()
        
        # For Teams, attachments often have a pre-authenticated URL
        # that doesn't require additional token
        return ""
