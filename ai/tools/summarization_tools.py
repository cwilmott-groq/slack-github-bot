import os
import logging
from typing import Dict, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import groq  
import json
from listeners.listener_utils.parse_conversation_for_summarization import parse_slack_conversation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackSummarizationTool:
    def __init__(self):
        """Initialize the Slack client and OpenAI API"""
        self.client = WebClient(token=os.environ.get("SLACK_USER_TOKEN"))
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.llm_client = groq.Groq(api_key=self.api_key)

    def get_conversation_history(self, channel_name: str, limit: int = 10) -> Dict:
        """
        Retrieves and parses conversation history for a given channel name.

        Args:
            channel_name (str): Name of the channel to search for
            limit (int): Maximum number of messages to retrieve (default: 10)

        Returns:
            dict: Contains 'success' (bool), 'data' (conversation messages or None),
                  and 'error' (error message if any)
        """
        conversation_id = None
        try:
            # Find the conversation ID
            for result in self.client.conversations_list():
                for channel in result["channels"]:
                    if channel["name"] == channel_name:
                        conversation_id = channel["id"]
                        break
            print("\n\nconversation_id: ", conversation_id)
            if conversation_id is None:
                conversation_id = channel_name

            # Retrieve conversation history
            conversation = self.client.conversations_history(
                channel=conversation_id,
                limit=limit
            )["messages"]
            print("\n\nconversation: ", conversation)
            parsed_conversation = parse_slack_conversation(conversation)
            print("\n\nparsed_conversation SUCCESS: ", parsed_conversation)
            return {
                'success': True,
                'data': parsed_conversation,
                'error': None
            }

        except SlackApiError as e:
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
# Example function mappings for tool usage
def retrieve_conversation_history(channel_name: str) -> str:
    # Initialize the tool instance
    slack_summarizer = SlackSummarizationTool()
    result = slack_summarizer.get_conversation_history(channel_name)
    return json.dumps(result, indent=2)

SUMMARIZATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_conversation_history",
            "description": "Retrieve a conversation from a Slack channel",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel_name": {
                        "type": "string",
                        "description": "Name of the Slack channel to retrieve. Note that channel IDs are also accepted, but should be JUST the ID, with <# and > delimitation removed. For example, <#C2AQZMCKE|> should be C2AQZMCKE.",
                    }
                },
                "required": ["channel_name"],
            },
        },
    }
]