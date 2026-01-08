"""
Azure Functions entry point for PlanSet Review Bot

This module sets up the Azure Function that receives webhook calls from
Microsoft Teams via Azure Bot Service.
"""

import logging
import json
import traceback

import azure.functions as func
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
)
from botbuilder.schema import Activity

from bot.bot import PlanSetReviewBot
from bot.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Azure Functions app
app = func.FunctionApp()

# Create bot adapter and bot instance
adapter_settings = BotFrameworkAdapterSettings(
    app_id=config.app_id,
    app_password=config.app_password
)
adapter = BotFrameworkAdapter(adapter_settings)

# Error handler
async def on_error(context: TurnContext, error: Exception):
    """Handle errors that occur during bot processing"""
    logger.error(f"Bot error: {error}\n{traceback.format_exc()}")
    
    # Send error message to user
    await context.send_activity(
        "Sorry, something went wrong processing your request. "
        "Please try again or contact Jonah Knip on Teams for help."
    )

adapter.on_turn_error = on_error

# Create bot instance
bot = PlanSetReviewBot()


@app.function_name(name="messages")
@app.route(route="api/messages", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def messages(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main endpoint for receiving messages from Azure Bot Service
    
    This function receives all incoming activities (messages, events, etc.)
    from Microsoft Teams via the Azure Bot Service.
    """
    logger.info("Received message request")
    
    # Validate configuration
    missing_config = config.validate()
    if missing_config:
        logger.error(f"Missing configuration: {missing_config}")
        return func.HttpResponse(
            json.dumps({"error": "Bot not configured properly"}),
            status_code=500,
            mimetype="application/json"
        )
    
    try:
        # Parse the incoming activity
        body = req.get_body().decode("utf-8")
        activity = Activity().deserialize(json.loads(body))
        
        # Get authorization header
        auth_header = req.headers.get("Authorization", "")
        
        # Process the activity
        response = await adapter.process_activity(
            activity,
            auth_header,
            bot.on_turn
        )
        
        if response:
            return func.HttpResponse(
                json.dumps(response.body),
                status_code=response.status,
                mimetype="application/json"
            )
        
        return func.HttpResponse(status_code=200)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}\n{traceback.format_exc()}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.function_name(name="health")
@app.route(route="api/health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def health(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint
    
    Used by Azure to verify the function is running.
    """
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "bot_configured": len(config.validate()) == 0
        }),
        status_code=200,
        mimetype="application/json"
    )
