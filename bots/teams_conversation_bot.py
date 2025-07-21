import os
import json
import shutil
import logging

# from services.langchain_setup import agent_executor

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot_errors.log"), logging.StreamHandler()],
)

# Clean old ChromaDB on startup
if os.path.exists("chromadb"):
    shutil.rmtree("chromadb")

# Vanna instance (already trained and connected)

# Bot Framework specific imports
from botbuilder.core import (
    CardFactory,
    TurnContext,
    MessageFactory,
)
from botbuilder.core.teams import TeamsActivityHandler, TeamsInfo
from botbuilder.schema import Activity
from botbuilder.schema.teams import TeamInfo, TeamsChannelAccount

# Optional OpenAI service (for fallback or future use)

ADAPTIVECARDTEMPLATE = "resources/UserMentionCardTemplate.json"
WELCOME_CARD_PATH = "resources/welcome.json"


class TeamsConversationBot(TeamsActivityHandler):
    def __init__(self, app_id: str, app_password: str):
        self._app_id = app_id
        self._app_password = app_password

    async def on_teams_members_added(
        self,
        teams_members_added: list[TeamsChannelAccount],
        team_info: TeamInfo,
        turn_context: TurnContext,
    ):
        for member in teams_members_added:
            try:
                if (
                    member
                    and member.id
                    and turn_context.activity
                    and turn_context.activity.recipient
                    and turn_context.activity.recipient.id
                    and member.id != turn_context.activity.recipient.id
                ):
                    await turn_context.send_activity(
                        f"Welcome to the team { member.given_name } { member.surname }. I can answer questions about your data. Try asking 'list all tasks'."
                    )
            except Exception as e:
                logging.error(f"Error welcoming new team member {member.id}: {e}")
                # Optionally, send a message to the user or admin about the failure
                await turn_context.send_activity(
                    f"Failed to welcome {member.given_name}. An error occurred and has been logged."
                )

    async def send_welcome_adaptive_card(self, turn_context: TurnContext):
        if not turn_context.activity.from_property:
            await turn_context.send_activity(
                "Could not fetch user details - missing sender info."
            )
            return

        try:
            member = await TeamsInfo.get_member(
                turn_context, turn_context.activity.from_property.id
            )
        except Exception as e:
            logging.error(f"Failed to get member info: {e}")
            await turn_context.send_activity("Could not fetch user details.")
            return

        try:
            with open(WELCOME_CARD_PATH, "r", encoding="utf-8") as f:
                card_json = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load welcome card from {WELCOME_CARD_PATH}: {e}")
            await turn_context.send_activity("Failed to load welcome card.")
            return

        for item in card_json.get("body", []):
            if "text" in item:
                item["text"] = item["text"].replace("{user}", member.name)

        card_attachment = CardFactory.adaptive_card(card_json)
        await turn_context.send_activity(MessageFactory.attachment(card_attachment))

    async def on_message_activity(self, turn_context: TurnContext):
        TurnContext.remove_recipient_mention(turn_context.activity)

        # ✅ Handle Adaptive Card button clicks
        if turn_context.activity.value and "option" in turn_context.activity.value:
            text = turn_context.activity.value["option"]
        else:
            text = (turn_context.activity.text or "").strip().lower()

        print("Text received in server:::::::", text)
        await turn_context.send_activity(Activity(type="typing"))

        # ✅ Inject user name only if self-referential words are used
        self_referential_keywords = [" me ", " my ", " mine ", " i "]
        # Add padding spaces to ensure exact word match (e.g., avoids matching "some" or "dummy")
        padded_text = f" {text} "

        if any(kw in padded_text for kw in self_referential_keywords):
            print("Self-referential input detected, injecting user name.")
            user_name = (
                turn_context.activity.from_property.name
                if turn_context.activity.from_property
                and turn_context.activity.from_property.name
                else "the user"
            )
            text = f"{text}, my name is {user_name}"

        # ✅ Greet user with Welcome Card
        greetings = {
            "hi",
            "hello",
            "hey",
            "welcome",
            "yo",
            "greetings",
            "sup",
            "good morning",
            "good evening",
        }

        if any(greet in text for greet in greetings):
            await self.send_welcome_adaptive_card(turn_context)
            return
