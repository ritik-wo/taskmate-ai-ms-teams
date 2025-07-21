# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import traceback
import uuid
from datetime import datetime
from http import HTTPStatus
from dotenv import load_dotenv
# from routes.custom_api import router as custom_api_router

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botbuilder.schema import Activity, ActivityTypes

from bots import TeamsConversationBot
from config import DefaultConfig

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load configuration
CONFIG = DefaultConfig()

# Create adapter
# See https://aka.ms/about-bot-adapter to learn more about how bots work
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)


# Catch-all for errors
async def on_error(context: TurnContext, error: Exception):
    # Log errors to console (consider Azure Application Insights for production)
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send error messages to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    # Send a trace activity for Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.utcnow(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        await context.send_activity(trace_activity)


ADAPTER.on_turn_error = on_error

# If the channel is the Emulator and authentication is not in use, generate a random AppId
APP_ID = SETTINGS.app_id if SETTINGS.app_id else uuid.uuid4()

# Create the Bot
BOT = TeamsConversationBot(CONFIG.APP_ID, CONFIG.APP_PASSWORD)


# Pydantic model for /api/custom input validation
class CustomInput(BaseModel):
    input: str


# Route for bot messages: POST /api/messages
@app.post("/api/messages")
async def messages(request: Request):
    # if request.headers.get("content-type") != "application/json":
    #     return Response(status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    body = await request.json()
    # print("body+++++++++++++++++++", body)
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return JSONResponse(content=response.body, status_code=response.status)
    return Response(status_code=HTTPStatus.OK)


# Custom API: POST /api/custom
# app.include_router(custom_api_router)


# Custom API: GET /api/status
@app.get("/")
async def status_api():
    return {"status": "Bot is running", "timestamp": datetime.utcnow().isoformat()}


# Run the app with uvicorn (configured in production or via command line)
if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(app, host="localhost", port=CONFIG.PORT)
    except Exception as error:
        raise error
