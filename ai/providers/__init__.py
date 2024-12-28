from typing import List, Optional

from state_store.get_user_state import get_user_state

from ..ai_constants import DEFAULT_SYSTEM_CONTENT
from .anthropic import AnthropicAPI
from .openai import OpenAI_API
from .vertexai import VertexAPI
from .groq import GroqAPI

def get_available_providers():
    return {
        # **AnthropicAPI().get_models(),
        # **OpenAI_API().get_models(),
        # **VertexAPI().get_models(),
        **GroqAPI().get_models(),
    }

def _get_provider(provider_name: str):
    if provider_name.lower() == "anthropic":
        return AnthropicAPI()
    elif provider_name.lower() == "openai":
        return OpenAI_API()
    elif provider_name.lower() == "vertexai":
        return VertexAPI()
    elif provider_name.lower() == "groq":
        return GroqAPI()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")

def get_provider_response(
    user_id: str, 
    prompt: str, 
    context: Optional[List] = [], 
    system_content=DEFAULT_SYSTEM_CONTENT,
    metadata: Optional[dict] = None
):
    """
    Get response from the selected AI provider.
    
    Args:
        user_id (str): The user's ID
        prompt (str): The user's message
        context (Optional[List]): Previous conversation context
        system_content: System prompt content
        metadata (Optional[dict]): Additional metadata including user_id and other context
        
    Returns:
        str: The AI provider's response
    """
    # Format the context if provided
    formatted_context = "\n".join([f"{msg['user']}: {msg['text']}" for msg in context])
    full_prompt = f"Prompt: {prompt}\nContext: {formatted_context}"

    try:
        # Get provider and model from user state
        provider_name, model_name = get_user_state(user_id, False)
        provider = _get_provider(provider_name)
        provider.set_model(model_name)

        # Ensure metadata contains user_id
        if metadata is None:
            metadata = {}
        metadata['user_id'] = user_id

        # Generate response with metadata
        response = provider.generate_response(
            prompt=full_prompt,
            system_content=system_content,
            metadata=metadata
        )
        return response
    except Exception as e:
        raise e