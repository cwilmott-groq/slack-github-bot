from ai.ai_constants import DM_SYSTEM_CONTENT
from ai.providers import get_provider_response
from logging import Logger
from slack_sdk.errors import SlackApiError
from slack_bolt import Say
from slack_sdk import WebClient
from ..listener_utils.listener_constants import DEFAULT_LOADING_TEXT
from ..listener_utils.parse_conversation import parse_conversation
import json
"""
Handles the event when a direct message is sent to the bot, retrieves the conversation context,
and generates an AI response.
"""


def app_messaged_callback(client: WebClient, event: dict, logger: Logger, say: Say):
    print("Event - app_messaged.py: ", event)
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")
    user_id = event.get("user")
    text = event.get("text")
    # Store conversation history
    conversation_history = []


    try:
        # Call the conversations.history method using the WebClient
        # conversations.history returns the first 100 messages by default
        # These results are paginated, see: https://api.slack.com/methods/conversations.history$pagination
        result = client.conversations_history(channel=channel_id, limit=10)

        conversation_history = result["messages"]
        # Print results
        # print("{} messages found in {}".format(len(conversation_history), channel_id))

    except SlackApiError as e:
        logger.error("Error creating conversation: {}".format(e))
    try:
        if event.get("channel_type") == "im":
            conversation_context = ""

            if thread_ts:  # Retrieves context to continue the conversation in a thread.
                conversation = client.conversations_replies(channel=channel_id, limit=10, ts=thread_ts)["messages"]
                conversation_context = parse_conversation(conversation[:-1])
            else:
                conversation_context = parse_conversation(conversation_history)
            print("conversation_context: ", conversation_context)
            waiting_message = say(text=DEFAULT_LOADING_TEXT, thread_ts=thread_ts)
            response = get_provider_response(user_id, text, conversation_context, DM_SYSTEM_CONTENT)
            print("response: ", response)

            client.chat_update(channel=channel_id, ts=waiting_message["ts"], text=response)
    except Exception as e:
        logger.error(e)
        client.chat_update(channel=channel_id, ts=waiting_message["ts"], text=f"Received an error from Groq Chat:\n{e}")
