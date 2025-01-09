import os
import logging
import json
from typing import Dict, Optional, Tuple
from datetime import datetime
from groq import Groq
from google.cloud import bigquery
from pandas_gbq import read_gbq
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_IDS = [
    "prj-p-cloud-analytics-c7f5.warehouse_lago.invoices_denormalized",
    "prj-p-cloud-analytics-c7f5.warehouse_lago.dim_plans",
    "prj-p-cloud-analytics-c7f5.warehouse_lago.dim_customers",
    "prj-p-cloud-analytics-c7f5.warehouse_orion.usage_denormalized",
    "prj-p-cloud-analytics-c7f5.warehouse_models.user_model_current_pricing"
]

class SQLQueryGenerationTool:
    def __init__(self):
        """
        Initialize the Groq client and load schemas for all tables.
        """
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.llm_client = Groq(api_key=self.api_key)
        self.project_id = 'prj-p-cloud-analytics-c7f5'
        self.schemas = self.load_schemas()

    def load_schemas(self) -> Dict:
        """
        Load the database schemas for all tables in table_ids.

        Returns:
            dict: A dictionary where keys are table names and values are their schemas.
        """
        schemas = {}
        for table_id in TABLE_IDS:
            table_name = table_id.split(".")[-1]
            schema_path = f'/Users/calwilmott/Desktop/Projects/groq-slack-python-ai-chatbot/testbed/schemas/schema_{table_name}.json'
            try:
                with open(schema_path, 'r') as f:
                    schemas[table_name] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading schema for {table_name}: {e}")
        return schemas

    def generate_query(self, user_question: str) -> Dict:
        """
        Generate a SQL query based on the user's question using Groq's LLM.

        Args:
            user_question (str): The user's question in natural language

        Returns:
            dict: Contains 'success' (bool), 'query' (string or None),
                  and 'error' (error message if any)
        """
        if not self.schemas:
            return {
                'success': False,
                'query': None,
                'error': 'Schemas not loaded'
            }

        current_date = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""You are a text-to-SQL system. Given the following schemas and user question, generate a BigQuery SQL query that answers the question.

Schemas:
{json.dumps(self.schemas, indent=2)}

Tables:
{TABLE_IDS}

Current date: {current_date}

Generate only the SQL query without any explanation or additional text. The query should conform to BigQuery SQL syntax. Be sure to include the CORRECT and COMPLETE table name in the query.

User question: {user_question}"""

        try:
            completion = self.llm_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a text-to-SQL system that generates BigQuery SQL queries. Respond only with the SQL query, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1024
            )
            
            query = completion.choices[0].message.content
            # Clean up query if it contains markdown
            if query.startswith("```sql"):
                query = query[7:-3]

            return {
                'success': True,
                'query': query,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'query': None,
                'error': str(e)
            }

    def execute_query(self, query: str) -> Dict:
        """
        Execute the generated SQL query and return the results.

        Args:
            query (str): The SQL query to execute

        Returns:
            dict: Contains 'success' (bool), 'data' (list of dictionaries or None),
                  and 'error' (error message if any)
        """
        try:
            df = read_gbq(query, project_id=self.project_id)
            
            if df.empty:
                return {
                    'success': True,
                    'data': [],
                    'error': None
                }

            # Convert DataFrame to list of dictionaries
            results = df.to_dict(orient='records')

            return {
                'success': True,
                'data': results,
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }

    def process_question(self, user_question: str) -> Dict:
        """
        Process a user question end-to-end: generate and execute query.

        Args:
            user_question (str): The user's question in natural language

        Returns:
            dict: Contains 'success' (bool), 'query' (string or None),
                  'data' (list of dictionaries or None),
                  and 'error' (error message if any)
        """
        # Generate query
        query_result = self.generate_query(user_question)
        if not query_result['success']:
            return {
                'success': False,
                'query': None,
                'data': None,
                'error': query_result['error']
            }

        # Execute query
        execution_result = self.execute_query(query_result['query'])
        
        return {
            'success': execution_result['success'],
            'query': query_result['query'],
            'data': execution_result['data'],
            'error': execution_result['error']
        }

def generate_and_execute_query(question: str) -> str:
    """Generate and execute a query using all loaded schemas."""
    sql_generator = SQLQueryGenerationTool()
    result = sql_generator.process_question(question)
    result['data'] = str(result['data'])
    return json.dumps({
        'success': result['success'],
        'query': result['query'],
        'data': result['data'],
        'error': result['error']
    }, indent=2)


SQL_GENERATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_and_execute_query",
            "description": "Generate and execute a SQL query based on a natural language question. This tool should be used for any question that can be answered by a SQL query. Some of the major content of these tables includes: invoices_denormalized (details about invoices), dim_plans (details about subscription plans), dim_customers (data about customers, including associated email suffix), usage_denormalized (data about API usage/token consumption), user_model_current_pricing (data about the model pricing)",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The natural language question to convert to SQL",
                    }
                },
                "required": ["question"],
            },
        },
    }
]