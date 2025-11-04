"""
Weather Bot - Example NextMCP Application

This example demonstrates:
- Creating a NextMCP application
- Registering tools with decorators
- Using middleware for logging and error handling
- Configuration management
"""

from nextmcp import NextMCP, setup_logging, log_calls, error_handler
from typing import Optional
import random

# Setup logging
setup_logging(level="INFO")

# Create the MCP application
app = NextMCP(name="weather-bot", description="A simple weather information MCP server")

# Add global middleware
app.add_middleware(log_calls)
app.add_middleware(error_handler)


@app.tool(name="get_weather", description="Get current weather information for a city")
def get_weather(city: str, units: str = "fahrenheit") -> dict:
    """
    Retrieve weather information for a specified city.

    Args:
        city: Name of the city
        units: Temperature units (fahrenheit or celsius)

    Returns:
        Dictionary containing weather information
    """
    # This is a mock implementation
    # In a real application, you would call a weather API
    temperatures = {"fahrenheit": random.randint(60, 90), "celsius": random.randint(15, 32)}

    conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]

    return {
        "city": city,
        "temperature": temperatures.get(units, temperatures["fahrenheit"]),
        "units": units,
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 80),
        "wind_speed": random.randint(5, 25),
    }


@app.tool(name="get_forecast", description="Get weather forecast for the next few days")
def get_forecast(city: str, days: int = 3) -> dict:
    """
    Get weather forecast for upcoming days.

    Args:
        city: Name of the city
        days: Number of days to forecast (1-7)

    Returns:
        Dictionary containing forecast data
    """
    if days < 1 or days > 7:
        raise ValueError("Days must be between 1 and 7")

    # Mock forecast data
    forecast = []
    conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]

    for i in range(days):
        forecast.append(
            {
                "day": i + 1,
                "high": random.randint(65, 85),
                "low": random.randint(45, 65),
                "condition": random.choice(conditions),
                "precipitation_chance": random.randint(0, 100),
            }
        )

    return {"city": city, "forecast": forecast}


@app.tool(name="search_cities", description="Search for cities by name or region")
def search_cities(query: str, limit: int = 5) -> dict:
    """
    Search for cities matching a query.

    Args:
        query: Search query (city name or region)
        limit: Maximum number of results to return

    Returns:
        Dictionary containing matching cities
    """
    # Mock city database
    cities = [
        {"name": "New York", "country": "USA", "region": "Northeast"},
        {"name": "Los Angeles", "country": "USA", "region": "West Coast"},
        {"name": "Chicago", "country": "USA", "region": "Midwest"},
        {"name": "London", "country": "UK", "region": "England"},
        {"name": "Paris", "country": "France", "region": "Île-de-France"},
        {"name": "Tokyo", "country": "Japan", "region": "Kanto"},
        {"name": "Sydney", "country": "Australia", "region": "New South Wales"},
    ]

    # Simple search by city name
    query_lower = query.lower()
    results = [
        city
        for city in cities
        if query_lower in city["name"].lower() or query_lower in city["region"].lower()
    ]

    return {"query": query, "results": results[:limit], "total_found": len(results)}


# Run the application
if __name__ == "__main__":
    print("Starting Weather Bot MCP Server...")
    print("Registered tools:", list(app.get_tools().keys()))
    app.run()
