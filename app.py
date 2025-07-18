# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import sys
import traceback
import uuid
from datetime import datetime
from http import HTTPStatus
import os
import asyncio
import logging
from typing import Any, Dict, List

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    BotFrameworkAdapter,
)
from botbuilder.schema import Activity, ActivityTypes
import msal
import httpx

from bots import TeamsConversationBot
from config import DefaultConfig

CONFIG = DefaultConfig()

# Create adapter.
SETTINGS = BotFrameworkAdapterSettings(CONFIG.APP_ID, CONFIG.APP_PASSWORD)
ADAPTER = BotFrameworkAdapter(SETTINGS)

# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
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

APP_ID = SETTINGS.app_id if SETTINGS.app_id else uuid.uuid4()
BOT = TeamsConversationBot(CONFIG.APP_ID, CONFIG.APP_PASSWORD)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "The chatbot and broadcast API are running"}

@app.post("/api/messages")
async def messages(request: Request):
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
    else:
        return Response(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = request.headers.get("authorization", "")
    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return JSONResponse(content=response.body, status_code=response.status)
    return Response(status_code=status.HTTP_200_OK)

# --- Broadcast API logic (from api.py) ---
TENANT_ID = os.environ.get("TENANT_ID", "<YOUR_TENANT_ID>")
CLIENT_ID = os.environ.get("CLIENT_ID", "<YOUR_CLIENT_ID>")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "<YOUR_CLIENT_SECRET>")
GRAPH_APP_ID = os.environ.get("TEAMS_APP_ID", "<YOUR_TEAMS_APP_ID>")  # Teams app (bot) ID
SCOPES = ["https://graph.microsoft.com/.default"]
GRAPH_API = "https://graph.microsoft.com/v1.0"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("broadcast")

def get_graph_token() -> str:
    app_msal = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential=CLIENT_SECRET,
    )
    result = app_msal.acquire_token_for_client(scopes=SCOPES)
    if "access_token" not in result:
        logger.error(f"MSAL error: {result}")
        raise Exception("Could not obtain Graph token")
    return result["access_token"]

async def get_all_users(token: str) -> List[Dict[str, Any]]:
    users = []
    url = f"{GRAPH_API}/users?$select=id,displayName,mail,userPrincipalName"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        while url:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            users.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
    return users

async def ensure_bot_installed(token: str, user_id: str) -> None:
    url = f"{GRAPH_API}/users/{user_id}/teamwork/installedApps"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        installed = resp.json().get("value", [])
        for app in installed:
            if app.get("teamsApp", {}).get("id") == GRAPH_APP_ID:
                return  # Already installed
        payload = {
            "teamsApp@odata.bind": f"https://graph.microsoft.com/v1.0/appCatalogs/teamsApps/{GRAPH_APP_ID}"
        }
        install_resp = await client.post(url, headers=headers, json=payload)
        if install_resp.status_code not in (200, 201, 202):
            logger.warning(f"Install failed for user {user_id}: {install_resp.text}")

async def get_or_create_chat(token: str, user_id: str, bot_id: str) -> str:
    url = f"{GRAPH_API}/chats"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "chatType": "oneOnOne",
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"
            },
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{bot_id}')"
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201):
            return resp.json()["id"]
        elif resp.status_code == 409:
            chats_url = f"{GRAPH_API}/users/{user_id}/chats?$filter=chatType eq 'oneOnOne'"
            chats_resp = await client.get(chats_url, headers=headers)
            chats_resp.raise_for_status()
            chats = chats_resp.json().get("value", [])
            for chat in chats:
                if chat["chatType"] == "oneOnOne":
                    return chat["id"]
            raise Exception(f"Could not find or create chat for user {user_id}")
        else:
            logger.error(f"Chat creation failed for user {user_id}: {resp.text}")
            raise Exception(f"Chat creation failed: {resp.text}")

async def send_adaptive_card(token: str, chat_id: str, card: Dict[str, Any]) -> None:
    url = f"{GRAPH_API}/chats/{chat_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "attachments": [
            {
                "id": str(uuid.uuid4()),
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": card
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code not in (200, 201, 202):
            logger.warning(f"Failed to send card to chat {chat_id}: {resp.text}")

@app.post("/send-card")
async def send_card(request: Request):
    try:
        card = await request.json()
        token = get_graph_token()
        users = await get_all_users(token)
        logger.info(f"Broadcasting card to {len(users)} users...")
        results = []
        async def process_user(user):
            user_id = user["id"]
            try:
                await ensure_bot_installed(token, user_id)
                chat_id = await get_or_create_chat(token, user_id, CLIENT_ID)
                await send_adaptive_card(token, chat_id, card)
                return {"user": user_id, "status": "sent"}
            except Exception as e:
                logger.error(f"Failed for user {user_id}: {e}")
                return {"user": user_id, "status": "error", "error": str(e)}
        batch_size = 10
        for i in range(0, len(users), batch_size):
            batch = users[i:i+batch_size]
            batch_results = await asyncio.gather(*(process_user(u) for u in batch))
            results.extend(batch_results)
            await asyncio.sleep(1)
        return JSONResponse(content={"results": results})
    except Exception as e:
        logger.exception("Broadcast failed")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Entrypoint for uvicorn or gunicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
