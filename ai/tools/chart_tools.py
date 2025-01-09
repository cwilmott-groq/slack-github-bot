import logging
from typing import List, Dict, Optional
from quickchart import QuickChart
from groq import Groq
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChartTool:
    def __init__(self):
        """
        Initialize the chart generation tool.
        """
        self.chart_width = 500
        self.chart_height = 300
        self.device_pixel_ratio = 2.0

    def generate_chart(self, data: List[Dict], chart_type: str, x_key: str, y_key: str, title: Optional[str] = None) -> Optional[str]:
        """
        Generate a chart URL using QuickChart.

        Args:
            data (List[Dict]): List of dictionaries containing the data to be visualized.
            chart_type (str): The type of chart to generate (e.g., "bar", "line").
            x_key (str): The key for x-axis labels in the data.
            y_key (str): The key for y-axis values in the data.
            title (Optional[str]): The title of the chart.

        Returns:
            Optional[str]: The URL of the generated chart, or None if chart generation fails.
        """
        if not data or not x_key or not y_key:
            logger.warning("Insufficient data or keys for chart generation.")
            return None

        try:
            qc = QuickChart()
            qc.width = self.chart_width
            qc.height = self.chart_height
            qc.device_pixel_ratio = self.device_pixel_ratio

            chart_config = {
                "type": chart_type,
                "data": {
                    "labels": [row[x_key] for row in data],
                    "datasets": [{
                        "label": y_key,
                        "data": [row[y_key] for row in data]
                    }]
                }
            }

            if title:
                chart_config["options"] = {"plugins": {"title": {"display": True, "text": title}}}

            qc.config = chart_config
            return qc.get_url()
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None

def create_chart_from_data(data: List[Dict], chart_type: str, x_key: str, y_key: str, title: Optional[str] = None) -> str:
    """
    Standalone function to create a chart URL.

    Args:
        data (List[Dict]): List of dictionaries containing the data to be visualized.
        chart_type (str): The type of chart to generate (e.g., "bar", "line").
        x_key (str): The key for x-axis labels in the data.
        y_key (str): The key for y-axis values in the data.
        title (Optional[str]): The title of the chart.

    Returns:
        str: The generated chart URL or an error message.
    """
    chart_tool = ChartTool()
    chart_url = chart_tool.generate_chart(data, chart_type, x_key, y_key, title)
    if chart_url:
        return chart_url
    else:
        return "Error: Unable to generate chart. Check data and parameters."

def summarize_data(data: List[Dict]) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    llm_client = Groq(api_key=api_key)
    prompt = f"Here is the data: {data}. Please provide a summary of the data."
    response = llm_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    return response.choices[0].message.content


FINAL_RESPONSE_TOOLS = [
    {
    "type": "function",
    "function": {
        "name": "create_chart_from_data",
        "description": "Generate a chart URL using QuickChart based on provided data. Use this tool if the data makes sense to display in a chart.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "The data to be visualized, as a list of dictionaries.",
                    "items": {
                        "type": "object",
                        "description": "A dictionary representing a single data point.",
                        "additionalProperties": {"type": "string"}
                    }
                },
                "chart_type": {
                    "type": "string",
                    "description": "The type of chart to generate (e.g., 'bar', 'line').",
                },
                "x_key": {
                    "type": "string",
                    "description": "The key to use for x-axis labels in the data.",
                },
                "y_key": {
                    "type": "string",
                    "description": "The key to use for y-axis values in the data.",
                },
                "title": {
                    "type": "string",
                    "description": "The title of the chart.",
                    "default": None
                }
            },
            "required": ["data", "chart_type", "x_key", "y_key"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "summarize_data",
        "description": "Summarize the data received. Use this if the data doesn't make sense to display in a chart.",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "The data to be visualized, as a list of dictionaries.",
                    "items": {
                        "type": "object",
                        "description": "A dictionary representing a single data point.",
                        "additionalProperties": {"type": "string"}
                    }
                }
            },
            "required": ["data"]
        }
        
    }
}
]
