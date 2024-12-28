import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from fastembed import TextEmbedding
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeSearchTool:
    def __init__(self, 
                 qdrant_url: str = "http://35.192.46.32:6333",
                 collection_name: str = "github_code",
                 encoder_model: str = "BAAI/bge-small-en-v1.5"):
        """Initialize the code search tool with Qdrant and embedding model

        Args:
            qdrant_url (str): URL of the Qdrant server
            collection_name (str): Name of the Qdrant collection containing code embeddings
            encoder_model (str): Name of the embedding model to use
        """
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.client = QdrantClient(qdrant_url, api_key="a9pEPn1qlB4hS9oTzzT7Nmzbsqct3PPN")
        self.encoder = TextEmbedding(encoder_model)

    def search_code(self,
                   query: str,
                   limit: int = 5,
                   filters: Optional[Dict] = None) -> Dict:
        """
        Search for code snippets semantically similar to the query
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            filters (Dict, optional): Additional filters for the search
            
        Returns:
            Dict: Response containing search results or error information
        """
        logger.info(f"Searching code with query: {query}")
        
        try:
            # Generate embedding for the query
            query_embedding = next(self.encoder.embed([query]))
            
            # Prepare search parameters
            search_params = {
                "collection_name": self.collection_name,
                "query_vector": query_embedding,
                "limit": limit
            }
            if filters:
                search_params["filter"] = filters
                
            # Execute search
            results = self.client.search(**search_params)
            
            # Format results
            formatted_results = []
            for hit in results:
                result = hit.payload
                result["score"] = float(hit.score)  # Convert score to float for JSON serialization
                formatted_results.append(result)
                
            logger.info(f"Found {len(formatted_results)} results")
            return {
                "status": "success",
                "results": formatted_results
            }
            
        except Exception as e:
            error_msg = f"Error during code search: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }

# Initialize tool instance
code_searcher = CodeSearchTool()

# Define available tools configuration
CODE_SEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for code snippets semantically similar to the query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query describing the code you're looking for",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# Function mappings for tool calls
def search_code(query: str, 
                limit: int = 5,
                language: Optional[str] = None) -> str:
    filters = {"language": language} if language else None
    result = code_searcher.search_code(
        query=query,
        limit=limit    
        )
    return json.dumps(result, indent=2)
