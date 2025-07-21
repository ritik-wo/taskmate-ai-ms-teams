# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import json
import aiohttp
import ssl
from datetime import datetime, timezone
import time
from datetime import datetime
import traceback
import inspect

from typing import List
from botbuilder.core import CardFactory, TurnContext, MessageFactory
from botbuilder.core.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.schema import CardAction, HeroCard, Mention, ConversationParameters, Attachment, Activity
from botbuilder.schema.teams import TeamInfo, TeamsChannelAccount
from botbuilder.schema._connector_client_enums import ActionTypes

ADAPTIVECARDTEMPLATE = "resources/UserMentionCardTemplate.json"

class TeamsConversationBot(TeamsActivityHandler):
    def __init__(self, app_id: str, app_password: str):
        self._app_id = app_id
        self._app_password = app_password

    async def on_teams_members_added(  # pylint: disable=unused-argument
        self,
        teams_members_added: list[TeamsChannelAccount],
        team_info: TeamInfo,
        turn_context: TurnContext,
    ):
        for member in teams_members_added:
            if getattr(member, 'id', None) != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    f"Welcome to the team { member.given_name } { member.surname }. "
                )

    async def on_message_activity(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)
        text = turn_context.activity.text.strip().lower()
        print("Text received in bot::::::=>",text)
        if text.lower().strip() == "hey":
            print("=== ATTEMPTING TO SEND SIMPLE TEXT RESPONSE ===")
            try:
                await turn_context.send_activity("Hey back!")
                print("=== TEXT RESPONSE SENT SUCCESSFULLY ===")
            except Exception as e:
                print(f"=== ERROR SENDING TEXT RESPONSE ===")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                # Get detailed HTTP response info
                response = getattr(e, 'response', None)
                if response is not None:
                    print(f"HTTP Status: {getattr(response, 'status', 'Unknown')}")
                    print(f"HTTP Reason: {getattr(response, 'reason', 'Unknown')}")
                    print(f"Response Headers: {dict(response.headers) if hasattr(response, 'headers') else 'No headers'}")
                    try:
                        if hasattr(response, 'text'):
                            text_attr = response.text
                            if inspect.iscoroutinefunction(text_attr):
                                body = await text_attr()
                            elif callable(text_attr):
                                body = text_attr()
                            else:
                                body = str(text_attr)
                            print(f"Response Body: {body}")
                    except Exception as body_err:
                        print(f"Could not read response body: {body_err}")
                print(f"Service URL: {turn_context.activity.service_url}")
                print(f"Conversation ID: {turn_context.activity.conversation.id}")
                raise e
            return
        if text.lower().strip() == "debug":
            print(f"Service URL from activity: {turn_context.activity.service_url}")
            print(f"Channel ID: {turn_context.activity.channel_id}")
            print(f"Tenant ID: {turn_context.activity.channel_data.get('tenant', {}).get('id', 'Not found')}")
            return
        if text.lower().strip() == "time":
            print(f"Server time: {datetime.now()}")
            print(f"UTC time: {datetime.now(timezone.utc)}")
            print(f"Timestamp: {int(time.time())}")
            await turn_context.send_activity(f"Server time: {datetime.now(timezone.utc)} UTC")
            return
        if text.lower().strip() == "connectivity test":
            await self.test_connectivity(turn_context.activity.service_url)
            return
        if text.lower().strip() == "test token":
            import aiohttp
            import json
            from config import DefaultConfig
            print("=== TESTING TOKEN ACQUISITION ===")
            auth_url = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
            data = {
                'grant_type': 'client_credentials',
                'client_id': DefaultConfig.APP_ID,
                'client_secret': DefaultConfig.APP_PASSWORD,
                'scope': 'https://api.botframework.com/.default'
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(auth_url, data=data) as response:
                        print(f"Token request status: {response.status}")
                        response_text = await response.text()
                        print(f"Token response: {response_text}")
                        if response.status == 200:
                            token_data = json.loads(response_text)
                            print("✅ TOKEN ACQUISITION SUCCESSFUL!")
                            print(f"Token type: {token_data.get('token_type', 'Unknown')}")
                            print(f"Expires in: {token_data.get('expires_in', 'Unknown')} seconds")
                            access_token = token_data.get('access_token', '')
                            print(f"Token acquired (first 50 chars): {access_token[:50]}...")
                        else:
                            print("❌ TOKEN ACQUISITION FAILED!")
                            print(f"Full response: {response_text}")
            except Exception as e:
                print(f"❌ TOKEN ACQUISITION ERROR: {e}")
            return
        if "mention me" in text:
            await self._mention_adaptive_card_activity(turn_context)
            return

        if "mention" in text:
            await self._mention_activity(turn_context)
            return

        if "update" in text:
            await self._send_card(turn_context, True)
            return

        if "message" in text:
            await self._message_all_members(turn_context)
            return

        if "who" in text:
            await self._get_member(turn_context)
            return

        if "delete" in text:
            await self._delete_card_activity(turn_context)
            return

        await self._send_card(turn_context, False)
        return

    async def _mention_adaptive_card_activity(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
                return
            else:
                raise

        card_path = os.path.join(os.getcwd(), ADAPTIVECARDTEMPLATE)
        with open(card_path, "rb") as in_file:
            template_json = json.load(in_file)
        
        for t in template_json["body"]:
            t["text"] = t["text"].replace("${userName}", member.name)        
        for e in template_json["msteams"]["entities"]:
            e["text"] = e["text"].replace("${userName}", member.name)
            e["mentioned"]["id"] = e["mentioned"]["id"].replace("${userUPN}", member.user_principal_name)
            e["mentioned"]["id"] = e["mentioned"]["id"].replace("${userAAD}", member.aad_object_id)
            e["mentioned"]["name"] = e["mentioned"]["name"].replace("${userName}", member.name)
        
        adaptive_card_attachment = Activity(
            attachments=[CardFactory.adaptive_card(template_json)]
        )
        await turn_context.send_activity(adaptive_card_attachment)

    async def _mention_activity(self, turn_context: TurnContext):
        mention = Mention(
            mentioned=turn_context.activity.from_property,
            text=f"<at>{turn_context.activity.from_property.name}</at>",
            type="mention",
        )

        reply_activity = MessageFactory.text(f"Hello {mention.text}")
        reply_activity.entities = [Mention().deserialize(mention.serialize())]
        await turn_context.send_activity(reply_activity)

    async def _send_card(self, turn_context: TurnContext, isUpdate):
        buttons = [
            CardAction(
                type=ActionTypes.message_back,
                title="Message all members",
                text="messageallmembers",
            ),
            CardAction(type=ActionTypes.message_back, title="Who am I?", text="whoami"),
            CardAction(type=ActionTypes.message_back, title="Find me in Adaptive Card", text="mention me"),
            CardAction(
                type=ActionTypes.message_back, title="Delete card", text="deletecard"
            ),
        ]
        if isUpdate:
            await self._send_update_card(turn_context, buttons)
        else:
            await self._send_welcome_card(turn_context, buttons)

    async def _send_welcome_card(self, turn_context: TurnContext, buttons):
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value={"count": 0},
            )
        )
        card = HeroCard(
            title="Welcome Card", text="Click the buttons.", buttons=buttons
        )
        await turn_context.send_activity(
            MessageFactory.attachment(CardFactory.hero_card(card))
        )

    async def _send_update_card(self, turn_context: TurnContext, buttons):
        data = turn_context.activity.value
        data["count"] += 1
        buttons.append(
            CardAction(
                type=ActionTypes.message_back,
                title="Update Card",
                text="updatecardaction",
                value=data,
            )
        )
        card = HeroCard(
            title="Updated card", text=f"Update count {data['count']}", buttons=buttons
        )

        updated_activity = MessageFactory.attachment(CardFactory.hero_card(card))
        updated_activity.id = turn_context.activity.reply_to_id
        await turn_context.update_activity(updated_activity)

    async def _get_member(self, turn_context: TurnContext):
        TeamsChannelAccount: member = None
        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            if "MemberNotFoundInConversation" in e.args[0]:
                await turn_context.send_activity("Member not found.")
            else:
                raise
        else:
            await turn_context.send_activity(f"You are: {member.name}")

    async def _message_all_members(self, turn_context: TurnContext):
        team_members = await self._get_paged_members(turn_context)

        for member in team_members:
            conversation_reference = TurnContext.get_conversation_reference(
                turn_context.activity
            )

            conversation_parameters = ConversationParameters(
                is_group=False,
                bot=turn_context.activity.recipient,
                members=[member],
                tenant_id=turn_context.activity.conversation.tenant_id,
            )

            async def get_ref(tc1):
                conversation_reference_inner = TurnContext.get_conversation_reference(
                    tc1.activity
                )
                return await tc1.adapter.continue_conversation(
                    conversation_reference_inner, send_message, self._app_id
                )

            async def send_message(tc2: TurnContext):
                return await tc2.send_activity(
                    f"Hello {member.name}. I'm a Teams conversation bot."
                )  # pylint: disable=cell-var-from-loop

            await turn_context.adapter.create_conversation(
                conversation_reference, get_ref, conversation_parameters
            )

        await turn_context.send_activity(
            MessageFactory.text("All messages have been sent")
        )

    async def _get_paged_members(
        self, turn_context: TurnContext
    ) -> List[TeamsChannelAccount]:
        paged_members = []
        continuation_token = None

        while True:
            current_page = await TeamsInfo.get_paged_members(
                turn_context, continuation_token, 100
            )
            continuation_token = current_page.continuation_token
            paged_members.extend(current_page.members)

            if continuation_token is None:
                break

        return paged_members

    async def _delete_card_activity(self, turn_context: TurnContext):
        await turn_context.delete_activity(turn_context.activity.reply_to_id)

    async def test_connectivity(self, service_url):
        print(f"=== TESTING CONNECTIVITY TO {service_url} ===")
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{service_url}v3/conversations", headers={'User-Agent': 'Test-Connectivity'}) as response:
                    print(f"Connectivity test - Status: {response.status}")
                    print(f"Connectivity test - Headers: {dict(response.headers)}")
        except Exception as conn_error:
            print(f"Connectivity test failed: {conn_error}")
