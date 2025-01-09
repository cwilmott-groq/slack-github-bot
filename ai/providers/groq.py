# groq_api.py
import groq
from .base_provider import BaseAPIProvider
import os
import logging
import json
from ..tools.base_tools import (
    AVAILABLE_TOOLS,
    wolfram_calculate,
    web_search,
    WolframTool,
    ExaSearchTool,
)
from ..tools.scheduling_tools import (
    SLACK_TOOLS,
    schedule_reminder,
    cancel_reminder,
    SlackSchedulerTool
)

from ..tools.qdrant_tools import (
    CODE_SEARCH_TOOLS,
    CodeSearchTool,
    search_code
)
from ..tools.summarization_tools import (
    SUMMARIZATION_TOOLS,
    SlackSummarizationTool,
    retrieve_conversation_history
)

from ..tools.text_to_sql_tools import (
    SQL_GENERATION_TOOLS,
    generate_and_execute_query,
    SQLQueryGenerationTool
)
from ..tools.chart_tools import (
    FINAL_RESPONSE_TOOLS,
    create_chart_from_data,
    ChartTool,
    summarize_data
)
logging.basicConfig(level=logging.INFO)  # Changed to INFO for better debugging
logger = logging.getLogger(__name__)

class GroqAPI(BaseAPIProvider):
    MODELS = {
        "llama-3.3-70B-versatile": {"name": "Llama 3.3 70B Versatile", "provider": "Groq", "max_tokens": 4096},
        "llama-3.1-8B-instant": {"name": "Llama 3.1 8B Instant", "provider": "Groq", "max_tokens": 4096},
        "llama-3.3-70B-specdec": {"name": "Llama 3.3 70B SpecDec", "provider": "Groq", "max_tokens": 4096},
    }

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.client = None
        self.current_model = None
        # Initialize tool instances
        self._init_tools()

    def _init_tools(self):
        """Initialize tool instances if the required environment variables are present."""
        try:
            self.wolfram_tool = WolframTool()
            self.search_tool = ExaSearchTool()
            self.slack_tool = SlackSchedulerTool()
            self.code_search_tool = CodeSearchTool()
            self.summarization_tool = SlackSummarizationTool()
            self.sql_tool = SQLQueryGenerationTool()
            self.chart_tool = ChartTool()
        except Exception as e:
            logger.error(f"Error initializing tools: {e}")
            raise

    def set_model(self, model_name: str):
        if model_name not in self.MODELS.keys():
            raise ValueError("Invalid model")
        self.current_model = model_name

    def get_models(self) -> dict:
        if self.api_key is not None:
            return self.MODELS
        else:
            return {}

    def generate_response(self, prompt: str, system_content: str, metadata: dict = None) -> tuple[str, dict]:
        """
        Generate a response using the Groq API.
        
        Args:
            prompt (str): User's input prompt
            system_content (str): System message content
            metadata (dict): Additional metadata including user_id
        """
        print("GENERATING RESPONSE...")
        try:
            if not self.client:
                self.client = groq.Groq(api_key=self.api_key)

            # Extract user_id from metadata
            user_id = metadata.get('user_id') if metadata else None
            if not user_id:
                logger.error("No user_id provided in metadata")
                raise ValueError("user_id is required in metadata")

            logger.info(f"Processing request for user_id: {user_id}")

            # Initial messages setup
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]

            # Combine all available tools
            all_tools = AVAILABLE_TOOLS + SLACK_TOOLS + CODE_SEARCH_TOOLS + SUMMARIZATION_TOOLS + SQL_GENERATION_TOOLS
            # In case we don't need to create a chart, we don't need to pass blocks
            # First API call with tools
            response = self.client.chat.completions.create(
                model=self.current_model,
                messages=messages,
                tools=all_tools,
                tool_choice="auto",
                max_tokens=self.MODELS[self.current_model]["max_tokens"],
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            print(response)
            # If the model wants to use tools
            if tool_calls:
                logger.info("TOOL CALLS FOUND: %s", tool_calls)
                # Map of available functions
                available_functions = {
                    "wolfram_calculate": wolfram_calculate,
                    "web_search": web_search,
                    "schedule_reminder": schedule_reminder,
                    "cancel_reminder": cancel_reminder,
                    "search_code": search_code,
                    "retrieve_conversation_history": retrieve_conversation_history,
                    "generate_and_execute_query": generate_and_execute_query
                }

                messages.append(response_message)

                # Process each tool call
                for tool_call in tool_calls:
                    print("tool_call: ", tool_call)
                    function_name = tool_call.function.name
                    if function_name not in available_functions:
                        logger.error(f"Unknown function called: {function_name}")
                        continue

                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)

                    # Call the function with appropriate arguments based on function name
                    if function_name == "wolfram_calculate":
                        function_response = function_to_call(
                            expression=function_args.get("expression")
                        )
                        new_prompt = f"Here is the Wolfram Alpha result: {function_response}. Please provide a summary of the result and any relevant information."
                    elif function_name == "web_search":
                        function_response = function_to_call(
                            query=function_args.get("query"),
                            max_results=function_args.get("max_results", 3)
                        )
                        new_prompt = f"Here is the web search result: {function_response}. Please provide a summary of the result and any relevant information."
                    elif function_name == "query_groq_repo":
                        function_response = function_to_call(
                            query=function_args.get("query"),
                            limit=function_args.get("limit", 5)
                        )
                        new_prompt = f"Here is the Groq repo search result: {function_response}. Please provide a summary of the result and any relevant information."
                    elif function_name == "schedule_reminder":
                        logger.info(f"Scheduling reminder for user {user_id}")
                        function_response = function_to_call(
                            user_id=user_id,
                            message=function_args.get("message"),
                            delay=function_args.get("delay")
                        )
                        logger.info(f"Reminder scheduling response: {function_response}")

                        # Add response to messages
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(function_response),
                        })

                        # Add guidance for model's response after successful scheduling
                        if '"status": "success"' in str(function_response):
                            messages.append({
                                "role": "system",
                                "content": "The reminder has been successfully scheduled. Please provide a brief confirmation message indicating when the reminder will be sent. Do not repeat the reminder message itself."
                            })
                        continue  # Skip the standard message append for reminders

                    elif function_name == "cancel_reminder":
                        function_response = function_to_call(
                            user_id=user_id,
                            scheduled_message_id=function_args.get("scheduled_message_id")
                        )
                        new_prompt = f"Here is the scheduled message ID: {function_response}. Please provide a brief confirmation message indicating when the reminder will be sent. Do not repeat the reminder message itself."
                    elif function_name == "search_code":
                        print("attempting search_code")
                        function_response = function_to_call(
                            query=function_args.get("query"),
                            limit=function_args.get("limit", 5),
                            language=function_args.get("language")
                        )
                        print("search_code response: ", function_response)
                        new_prompt = f"Here is the code search result: {function_response}. Please provide a summary of the code and any relevant information. Cite your sources using the following format: <https://github.com/org/repo/blob/branch/path#Lstart-Lend|$DocumentName>."
                        print(new_prompt)
                    elif function_name == "retrieve_conversation_history":
                        function_response = function_to_call(
                            channel_name=function_args.get("channel_name")
                        )
                        new_prompt = f"Here is the Slack channel conversation: {function_response}. Please provide a summary of the conversation and any relevant information. Ensure you follow slack-specific formatting rules, such as single asterisks for bold text, and <http://example.com|Custom Text> for links. User IDs, which look like U012AB3CD|@username, should be formatted as <@UserID>. Do not include any additional formatting or markdown, or any additional instructions or content beyond the conversation summary."
                    elif function_name == "generate_and_execute_query":
                        function_response = function_to_call(
                            question=function_args.get("question")
                        )
                        print("function_response: ", function_response)
                        new_prompt = f"Here is the SQL query result: {function_response}. Please provide a summary of the results and any relevant information."
    
                    # Add the tool response to messages for non-reminder functions
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(new_prompt),
                    })


                
                # Make a second API call with the tool responses
                response_message = self.client.chat.completions.create(
                    model=self.current_model,
                    messages=messages,
                    max_tokens=self.MODELS[self.current_model]["max_tokens"],

                )

            return response_message.choices[0].message.content

        except groq.APIConnectionError as e:
            logger.error(f"Server could not be reached: {e.__cause__}")
            raise e
        except groq.RateLimitError as e:
            logger.error(f"A 429 status code was received. {e}")
            raise e
        except groq.AuthenticationError as e:
            logger.error(f"There's an issue with your API key. {e}")
            raise e
        except groq.APIStatusError as e:
            logger.error(f"Another non-200-range status code was received: {e.status_code}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise