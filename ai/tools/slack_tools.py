# slack_tools.py
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from slack_bolt import App
from slack_sdk.errors import SlackApiError
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SlackSchedulerTool:
    def __init__(self):
        """Initialize the Slack app with your bot token"""
        self.app = App(
            token=os.environ.get("SLACK_BOT_TOKEN"),
            signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
        )

    def parse_time_expression(self, time_expr: str) -> timedelta:
        """
        Parse a time expression like '5 minutes' or '2 hours' into a timedelta
        
        Args:
            time_expr (str): Time expression (e.g., '5 minutes', '2 hours')
            
        Returns:
            timedelta: Parsed time duration
        """
        parts = time_expr.lower().split()
        if len(parts) != 2:
            raise ValueError("Time expression must be in format: NUMBER UNIT (e.g., '5 minutes')")
            
        try:
            amount = int(parts[0])
            unit = parts[1].rstrip('s')  # Remove potential plural 's'
            
            if unit == 'minute':
                return timedelta(minutes=amount)
            elif unit == 'hour':
                return timedelta(hours=amount)
            elif unit == 'day':
                return timedelta(days=amount)
            else:
                raise ValueError(f"Unsupported time unit: {unit}")
                
        except ValueError as e:
            raise ValueError(f"Invalid time expression: {str(e)}")

    def schedule_reminder(self, 
                         user_id: str,
                         message: str, 
                         delay: str) -> Dict:
        """
        Schedule a reminder message to be sent to the user after the specified delay
        
        Args:
            user_id (str): ID of the user who will receive the reminder
            message (str): Message text to send
            delay (str): Delay expression (e.g., '5 minutes', '2 hours')
            
        Returns:
            Dict: Response from the Slack API
        """
        logger.info(f"Attempting to schedule reminder for user {user_id}")
        
        try:
            # Open DM channel with user
            dm_response = self.app.client.conversations_open(users=[user_id])
            if not dm_response["ok"]:
                return {
                    "status": "error",
                    "error": "Could not open DM channel with user"
                }
            
            dm_channel_id = dm_response["channel"]["id"]
            
            # Parse the delay expression
            time_delta = self.parse_time_expression(delay)
            
            # Calculate the scheduled time
            schedule_time = datetime.now() + time_delta
            
            # Convert to Unix timestamp
            schedule_timestamp = int(schedule_time.timestamp())
            
            # Schedule the message
            response = self.app.client.chat_scheduleMessage(
                channel=dm_channel_id,
                text=message,
                post_at=schedule_timestamp
            )
            
            logger.info(f"Successfully scheduled reminder: {response['scheduled_message_id']}")
            return {
                "status": "success",
                "scheduled_time": schedule_time.isoformat(),
                "message_id": response["scheduled_message_id"]
            }
            
        except SlackApiError as e:
            error_msg = f"Slack API error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
        except ValueError as e:
            error_msg = f"Invalid delay format: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }

    def cancel_reminder(self, 
                       user_id: str,
                       scheduled_message_id: str) -> Dict:
        """
        Cancel a scheduled reminder
        
        Args:
            user_id (str): User ID who the reminder was for
            scheduled_message_id (str): ID of the scheduled message
            
        Returns:
            Dict: Response indicating success or failure
        """
        try:
            # Get DM channel ID
            dm_response = self.app.client.conversations_open(users=[user_id])
            if not dm_response["ok"]:
                return {
                    "status": "error",
                    "error": "Could not open DM channel with user"
                }
            
            dm_channel_id = dm_response["channel"]["id"]
                
            self.app.client.chat_deleteScheduledMessage(
                channel=dm_channel_id,
                scheduled_message_id=scheduled_message_id
            )
            
            return {
                "status": "success",
                "message": "Scheduled reminder cancelled successfully"
            }
            
        except SlackApiError as e:
            error_msg = f"Slack API error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }

# Initialize tool instance
slack_scheduler = SlackSchedulerTool()

# Define available tools configuration
SLACK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "schedule_reminder",
            "description": "Schedule a reminder message to be sent to the user after a specified delay",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "ID of the user who will receive the reminder",
                    },
                    "message": {
                        "type": "string",
                        "description": "Message text to send",
                    },
                    "delay": {
                        "type": "string",
                        "description": "Delay before sending (e.g., '5 minutes', '2 hours')",
                    }
                },
                "required": ["user_id", "message", "delay"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reminder",
            "description": "Cancel a scheduled reminder",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID who the reminder was for",
                    },
                    "scheduled_message_id": {
                        "type": "string",
                        "description": "ID of the scheduled message to cancel",
                    }
                },
                "required": ["user_id", "scheduled_message_id"],
            },
        },
    }
]

# Function mappings for tool calls
def schedule_reminder(user_id: str, 
                     message: str, 
                     delay: str) -> str:
    result = slack_scheduler.schedule_reminder(
        user_id=user_id,
        message=message,
        delay=delay
    )
    return json.dumps(result, indent=2)

def cancel_reminder(user_id: str, 
                   scheduled_message_id: str) -> str:
    result = slack_scheduler.cancel_reminder(
        user_id=user_id,
        scheduled_message_id=scheduled_message_id
    )
    return json.dumps(result, indent=2)