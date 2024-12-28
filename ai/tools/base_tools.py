# tools.py
import json
import os
import wolframalpha
import requests
from qdrant_client import QdrantClient
from typing import Dict, List, Optional

class WolframTool:
    def __init__(self):
        self.client = wolframalpha.Client("UG8596-J8V6LP3YW9")

    def query(self, expression: str) -> str:
        """
        Queries Wolfram Alpha with a mathematical expression or question.
        
        Args:
            expression (str): Mathematical expression or question
            
        Returns:
            str: Result from Wolfram Alpha
        """
        try:
            res = self.client.query(expression)
            
            # First check for the "Definite integral" pod
            for pod in res.pods:
                if pod.title == 'Definite integral':
                    return pod.text
            
            # If no definite integral pod, check for other relevant pods
            for pod in res.pods:
                if pod.title in ['Result', 'Solution', 'Value']:
                    return pod.text
                
            # If still no result, look for any pod with a text result
            for pod in res.pods:
                if hasattr(pod, 'text') and pod.text:
                    return pod.text
            
            return "No solution found"
            
        except Exception as e:
            return f"Error querying Wolfram Alpha: {str(e)}"

class ExaSearchTool:
    def __init__(self):
        self.api_key = os.environ.get("EXASEARCH_API_KEY")
        self.base_url = "https://api.exa.ai/search"

    def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Performs a web search using exa.ai API.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of search results with title, snippet, and URL
        """
        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "query": query,
                "numResults": max_results,
                "useAutoprompt": True,
                "contents": {
                    "text": {
                        "maxCharacters": 1000
                    },
                    "highlights": {
                        "numSentences": 3,
                        "highlightsPerUrl": 3
                    }
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                results = response.json()
                return [
                    {
                        "title": result.get("title", ""),
                        "snippet": result.get("text", ""),  # Changed from "snippet" to "text" based on API response
                        "url": result.get("url", "")
                    }
                    for result in results.get("results", [])
                ]
            else:
                error_message = f"Search failed with status code: {response.status_code}"
                if response.text:
                    error_message += f". Response: {response.text}"
                return [{"error": error_message}]
                
        except Exception as e:
            return [{"error": f"Search error: {str(e)}"}]

class GroqRepoTool:
    def __init__(self):
        self.client = QdrantClient(
            url=os.environ.get("QDRANT_URL"),
            api_key=os.environ.get("QDRANT_API_KEY")
        )
        self.collection_name = "groq_repo"

    def query_repo(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Queries the Qdrant vector database containing Groq repository information.
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of relevant code snippets and documentation
        """
        try:
            # Search the vector database
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=self._embed_query(query),
                limit=limit
            )
            
            return [
                {
                    "content": hit.payload.get("content"),
                    "file_path": hit.payload.get("file_path"),
                    "relevance_score": hit.score
                }
                for hit in search_result
            ]
        except Exception as e:
            return [{"error": f"Repository search error: {str(e)}"}]

    def _embed_query(self, query: str) -> List[float]:
        """
        Converts the query string into an embedding vector.
        This is a placeholder - you'd need to implement actual embedding logic.
        """
        # TODO: Implement actual embedding logic using your preferred embedding model
        pass

# Initialize tool instances
wolfram_tool = WolframTool()
search_tool = ExaSearchTool()
repo_tool = GroqRepoTool()

# Define available tools configuration
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "wolfram_calculate",
            "description": "Evaluate mathematical expressions and answer scientific questions using Wolfram Alpha",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression or scientific question to evaluate",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information using exa.ai",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 3
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_groq_repo",
            "description": "Search the Groq repository for relevant code and documentation",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for the repository",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5
                    }
                },
                "required": ["query"],
            },
        },
    }
]

# Function mappings for tool calls
def wolfram_calculate(expression: str) -> str:
    return wolfram_tool.query(expression)

def web_search(query: str, max_results: int = 3) -> str:
    results = search_tool.search(query, max_results)
    return json.dumps(results, indent=2)

def query_groq_repo(query: str, limit: int = 5) -> str:
    results = repo_tool.query_repo(query, limit)
    return json.dumps(results, indent=2)