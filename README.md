---
page_type: sample
description: This app demonstrates using bot conversation events in Microsoft Teams, supporting adaptive cards, read receipts, and message update events. It includes immersive reader support for enhanced accessibility.
products:
- office-teams
- office
- office-365
languages:
- python
extensions:
 contentType: samples
 createdDate: "12-12-2019 13:38:25"
urlFragment: officedev-microsoft-teams-samples-bot-conversation-python

---

# Teams Conversation Bot

This sample app demonstrates how to handle various bot conversation events in Microsoft Teams, including read receipts and adaptive card interactions. It showcases capabilities such as immersive reader support and message update tracking, making it ideal for personal, group, and team chat scopes.

Bot Framework v4 Conversation Bot sample for Teams ([Messages in bot conversations](https://learn.microsoft.com/microsoftteams/platform/bots/how-to/conversations/conversation-messages?tabs=dotnet)).

This bot has been created using [Bot Framework](https://dev.botframework.com). This sample shows
how to incorporate basic conversational flow into a Teams application. It also illustrates a few of the Teams specific calls you can make from your bot.

## Included Features
* Bots
* Adaptive Cards
* Teams Conversation Events
* Immersive Reading Support for Cards

## Interaction with bot
![BotConversation](Images/BotConversation.gif)

## Try it yourself - experience the App in your Microsoft Teams client
Please find below demo manifest which is deployed on Microsoft Azure and you can try it yourself by uploading the app package (.zip file link below) to your teams and/or as a personal app. (Uploading must be enabled for your tenant, [see steps here](https://docs.microsoft.com/microsoftteams/platform/concepts/build-and-test/prepare-your-o365-tenant#enable-custom-teams-apps-and-turn-on-custom-app-uploading)).

**Teams Conversation Bot:** [Manifest](https://github.com/OfficeDev/Microsoft-Teams-Samples/blob/main/samples/bot-conversation/csharp/demo-manifest/bot-conversation.zip)

## Prerequisites

- Microsoft Teams is installed and you have an account
- [Python SDK](https://www.python.org/downloads/) min version 3.6
- [dev tunnel](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/get-started?tabs=windows) or [ngrok](https://ngrok.com/) latest version or equivalent tunnelling solution


## Run the app (Using Microsoft 365 Agents Toolkit for Visual Studio Code)

The simplest way to run this sample in Teams is to use Microsoft 365 Agents Toolkit for Visual Studio Code.

1. Ensure you have downloaded and installed [Visual Studio Code](https://code.visualstudio.com/docs/setup/setup-overview)
1. Install the [Microsoft 365 Agents Toolkit extension](https://marketplace.visualstudio.com/items?itemName=TeamsDevApp.ms-teams-vscode-extension) and [Python Extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
1. Select **File > Open Folder** in VS Code and choose this samples directory from the repo
1. Press **CTRL+Shift+P** to open the command box and enter **Python: Create Environment** to create and activate your desired virtual environment. Remember to select `requirements.txt` as dependencies to install when creating the virtual environment.
1. Using the extension, sign in with your Microsoft 365 account where you have permissions to upload custom apps
1. Select **Debug > Start Debugging** or **F5** to run the app in a Teams web client.
1. In the browser that launches, select the **Add** button to install the app to Teams.

> If you do not have permission to upload custom apps (uploading), Microsoft 365 Agents Toolkit will recommend creating and using a Microsoft 365 Developer Program account - a free program to get your own dev environment sandbox that includes Teams.

## Run the app (Manually Uploading to Teams)

> Note these instructions are for running the sample on your local machine, the tunnelling solution is required because
the Teams service needs to call into the bot.

1) Clone the repository

    ```bash
    git clone https://github.com/OfficeDev/Microsoft-Teams-Samples.git
    ```

2) Run ngrok - point to port 3978

   ```bash
   ngrok http 3978 --host-header="localhost:3978"
   ```  

   Alternatively, you can also use the `dev tunnels`. Please follow [Create and host a dev tunnel](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/get-started?tabs=windows) and host the tunnel with anonymous user access command as shown below:

   ```bash
   devtunnel host -p 3978 --allow-anonymous
   ```

3) Create [Azure Bot resource resource](https://docs.microsoft.com/azure/bot-service/bot-service-quickstart-registration) in Azure
    - Use the current `https` URL you were given by running the tunneling application. Append with the path `/api/messages` used by this sample
    - Ensure that you've [enabled the Teams Channel](https://docs.microsoft.com/azure/bot-service/channel-connect-teams?view=azure-bot-service-4.0)
    - __*If you don't have an Azure account*__ you can use this [Azure free account here](https://azure.microsoft.com/free/)

4) In a terminal, go to `samples\bot-conversation`

5) Activate your desired virtual environment

6) Install dependencies by running ```pip install -r requirements.txt``` in the project folder.

7) Update the `config.py` configuration for the bot to use the Microsoft App Id and App Password from the Bot Framework registration. (Note the App Password is referred to as the "client secret" in the azure portal and you can always create a new client secret anytime.)

8) __*This step is specific to Teams.*__
    - **Edit** the `manifest.json` contained in the `appManifest` folder to replace your Microsoft App Id (that was created when you registered your bot earlier) *everywhere* you see the place holder string `${{AAD_APP_CLIENT_ID}}` and `${{TEAMS_APP_ID}}` (depending on the scenario the Microsoft App Id may occur multiple times in the `manifest.json`)
    - **Zip** up the contents of the `appManifest` folder to create a `manifest.zip`
    - **Upload** the `manifest.zip` to Teams (in the Apps view click "Upload a custom app")

9) Run your bot with `python app.py`

## Interacting with the bot

You can interact with this bot by sending it a message, or selecting a command from the command list. The bot will respond to the following strings. 

1. **Show Welcome**
  - **Result:** The bot will send the welcome card for you to interact with
  - **Valid Scopes:** personal, group chat, team chat
2. **MentionMe**
  - **Result:** The bot will respond to the message and mention the user
  - **Valid Scopes:** personal, group chat, team chat
3. **MessageAllMembers**
  - **Result:** The bot will send a 1-on-1 message to each member in the current conversation (aka on the conversation's roster).
  - **Valid Scopes:** personal, group chat, team chat

You can select an option from the command list by typing ```@TeamsConversationBot``` into the compose message area and ```What can I do?``` text above the compose area.

## Running the sample

The bot initialization message
![Message](Images/1.prompts.png)

The bot will send the welcome card for you to interact with
![WelcomeCard](Images/2.welcome.png)

The bot will respond to the message and mention the user
![MentionMe](Images/3.mention.png)

The bot initialization message
![MessageAllMembers](Images/4.message-to-all.png)

## Broadcast Adaptive Card API

This project now includes an external API endpoint to broadcast Adaptive Cards to every user in your organization via Microsoft Graph.

### Setup: Azure App Registration
1. Register an Azure AD App in the Azure Portal.
2. Grant the following Microsoft Graph application permissions:
   - TeamsAppInstallation.ReadWriteSelfForUser.All
   - Chat.Create
   - ChatMessage.Send
   - User.Read.All
3. Click "Grant admin consent" for your tenant.
4. Note the Client ID, Client Secret, and Tenant ID.
5. In your Teams app manifest, note the Teams App (bot) ID.

### Environment Variables
Set the following environment variables (e.g., in your shell or .env file):

```
TENANT_ID=<your-tenant-id>
CLIENT_ID=<your-azure-app-client-id>
CLIENT_SECRET=<your-azure-app-client-secret>
TEAMS_APP_ID=<your-teams-app-id>
```

### Running the API
Install dependencies:
```
pip install -r requirements.txt
```

Run the FastAPI app (for both bot and broadcast API):
```
uvicorn app:app --host 0.0.0.0 --port 3978 --reload
```

Or, to run only the broadcast API:
```
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Sending a Card
Prepare your Adaptive Card JSON (see `card.json` for a stub):

```
curl -X POST http://localhost:8000/send-card \
  -H "Content-Type: application/json" \
  -d @card.json
```

### Example card.json
Create a file named `card.json`:
```
{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    { "type": "TextBlock", "text": "Hello, this is a broadcast!" }
  ]
}
```

### Notes
- The API will ensure the bot is installed for each user, create a 1:1 chat if needed, and send the card.
- Errors (e.g., user blocks bot) are logged and reported in the API response.
- For large orgs, the API processes users in batches to respect Graph rate limits.

## Deploy the bot to Azure

To learn more about deploying a bot to Azure, see [Deploy your bot to Azure](https://aka.ms/azuredeployment) for a complete list of deployment instructions.

# Further reading

- [Bot Framework Documentation](https://docs.botframework.com)
- [Bot Basics](https://docs.microsoft.com/azure/bot-service/bot-builder-basics?view=azure-bot-service-4.0)
- [Azure Bot Service Introduction](https://docs.microsoft.com/azure/bot-service/bot-service-overview-introduction?view=azure-bot-service-4.0)
- [Azure Bot Service Documentation](https://docs.microsoft.com/azure/bot-service/?view=azure-bot-service-4.0)
- [Messages in bot conversations](https://learn.microsoft.com/microsoftteams/platform/bots/how-to/conversations/conversation-messages?tabs=dotnet)

<img src="https://pnptelemetry.azurewebsites.net/microsoft-teams-samples/samples/bot-conversation-python" />