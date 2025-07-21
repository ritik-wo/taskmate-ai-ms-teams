# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import traceback
import uuid
from datetime import datetime
from http import HTTPStatus

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity, ActivityTypes

from bots import TeamsConversationBot
from config import DefaultConfig

CONFIG = DefaultConfig()

# ENVIRONMENT CHECK LOGGING
print("=== ENVIRONMENT CHECK ===")
print(f"APP_ID: {CONFIG.APP_ID[:10]}...{CONFIG.APP_ID[-4:]}")  # Show partial for security")
print(f"APP_PASSWORD length: {len(CONFIG.APP_PASSWORD) if CONFIG.APP_PASSWORD else 0}")
print(f"APP_PASSWORD starts with: {CONFIG.APP_PASSWORD[:5] if CONFIG.APP_PASSWORD else 'None'}...")
print(f"Python version: {sys.version}")
print(f"Current time: {datetime.now()}")

# Log App ID and App Password in plain text for debugging
print(f"CONFIG.APP_ID: {CONFIG.APP_ID}")
print(f"CONFIG.APP_PASSWORD: {CONFIG.APP_PASSWORD}")

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)


# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    print(f"=== DETAILED ERROR INFORMATION ===")
    print(f"Error type: {type(error).__name__}")
    print(f"Error message: {str(error)}")
    # Check if it's the specific ErrorResponseException
    response = getattr(error, 'response', None)
    if response is not None:
        print(f"HTTP Response available: True")
        print(f"Status code: {getattr(response, 'status', 'Unknown')}")
        print(f"Status text: {getattr(response, 'reason', 'Unknown')}")
        if hasattr(response, 'headers'):
            print(f"Response headers: {dict(response.headers)}")
        if hasattr(response, 'text'):
            try:
                body = response.text if isinstance(response.text, str) else str(response.text)
                print(f"Response body: {body}")
            except Exception as body_error:
                print(f"Could not read response body: {body_error}")
    print(f"Activity Service URL: {context.activity.service_url}")
    print(f"Activity Channel: {context.activity.channel_id}")
    print(f"Bot App ID from adapter: {getattr(context.adapter, 'app_id', 'Not available')}")
    print(f"\n!!! Error at {datetime.now()}: {error}")
    traceback.print_exc()
    try:
        await context.send_activity("The bot encountered an error or bug.")
    except Exception as send_error:
        print(f"=== EVEN ERROR MESSAGE FAILED ===")
        print(f"Send error: {send_error}")
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        # Create a trace activity that contains the error object
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        # Send a trace activity, which will be displayed in Bot Framework Emulator
        await context.send_activity(trace_activity)


ADAPTER.on_turn_error = on_error

# If the channel is the Emulator, and authentication is not in use, the AppId will be null.
# We generate a random AppId for this case only. This is not required for production, since
# the AppId will have a value.
APP_ID = SETTINGS.app_id if SETTINGS.app_id else uuid.uuid4()

# Create the Bot
BOT = TeamsConversationBot(CONFIG.APP_ID, CONFIG.APP_PASSWORD)


# Listen for incoming requests on /api/messages.
async def messages(req: Request) -> Response:
    # Main bot message handler.
    print("Incoming request headers:", dict(req.headers))
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
        print("Incoming request body:", body)
    else:
        print("Unsupported content type:", req.headers["Content-Type"])
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""
    if auth_header:
        print(f"Authorization header present. Length: {len(auth_header)}. Starts with: {auth_header[:10]}")
    else:
        print("No Authorization header present.")

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return json_response(data=response.body, status=response.status)
    return Response(status=HTTPStatus.OK)


APP = web.Application(middlewares=[aiohttp_error_middleware])
APP.router.add_post("/api/messages", messages)

# Add a root route
async def root(request: Request) -> Response:
    return Response(text="Welcome to the Taskmate AI Teams Bot!", content_type="text/plain")

APP.router.add_get("/", root)

if __name__ == "__main__":
    try:
        web.run_app(APP, host="0.0.0.0", port=CONFIG.PORT)
    except Exception as error:
        raise error
