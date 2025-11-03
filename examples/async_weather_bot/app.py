"""
Async Weather Bot - Example NextMCP Application with Async Support

This example demonstrates:
- Creating a NextMCP application with async tools
- Registering async tools with decorators
- Using async middleware for logging and error handling
- Async/await patterns with external API calls
"""

import asyncio
from nextmcp import NextMCP, setup_logging, log_calls_async, error_handler_async
from typing import Optional
import random

# Setup logging
setup_logging(level="INFO")

# Create the MCP application
app = NextMCP(
    name="async-weather-bot",
    description="An async weather information MCP server"
)

# Add global async middleware
app.add_middleware(log_calls_async)
app.add_middleware(error_handler_async)


@app.tool(
    name="get_weather",
    description="Get current weather information for a city (async)"
)
async def get_weather(city: str, units: str = "fahrenheit") -> dict:
    """
    Retrieve weather information for a specified city using async operations.

    Args:
        city: Name of the city
        units: Temperature units (fahrenheit or celsius)

    Returns:
        Dictionary containing weather information
    """
    # Simulate async API call with delay
    await asyncio.sleep(0.1)

    # This is a mock implementation
    # In a real application, you would use an async HTTP client like httpx
    temperatures = {
        "fahrenheit": random.randint(60, 90),
        "celsius": random.randint(15, 32)
    }

    conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]

    return {
        "city": city,
        "temperature": temperatures.get(units, temperatures["fahrenheit"]),
        "units": units,
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 80),
        "wind_speed": random.randint(5, 25),
        "async": True  # Indicate this was fetched asynchronously
    }


@app.tool(
    name="get_forecast",
    description="Get weather forecast for the next few days (async)"
)
async def get_forecast(city: str, days: int = 3) -> dict:
    """
    Get weather forecast for upcoming days using async operations.

    Args:
        city: Name of the city
        days: Number of days to forecast (1-7)

    Returns:
        Dictionary containing forecast data
    """
    if days < 1 or days > 7:
        raise ValueError("Days must be between 1 and 7")

    # Simulate async API call
    await asyncio.sleep(0.2)

    # Mock forecast data
    forecast = []
    conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]

    for i in range(days):
        forecast.append({
            "day": i + 1,
            "high": random.randint(65, 85),
            "low": random.randint(45, 65),
            "condition": random.choice(conditions),
            "precipitation_chance": random.randint(0, 100)
        })

    return {
        "city": city,
        "forecast": forecast,
        "async": True
    }


@app.tool(
    name="get_batch_weather",
    description="Get weather for multiple cities concurrently (async)"
)
async def get_batch_weather(cities: list, units: str = "fahrenheit") -> dict:
    """
    Get weather for multiple cities using concurrent async operations.

    This demonstrates the power of async - fetching data for multiple
    cities concurrently instead of sequentially.

    Args:
        cities: List of city names
        units: Temperature units (fahrenheit or celsius)

    Returns:
        Dictionary containing weather for all cities
    """
    # Simulate fetching weather for all cities concurrently
    async def fetch_city_weather(city: str) -> dict:
        await asyncio.sleep(0.1)  # Simulate API delay

        temperatures = {
            "fahrenheit": random.randint(60, 90),
            "celsius": random.randint(15, 32)
        }
        conditions = ["sunny", "cloudy", "rainy", "partly cloudy"]

        return {
            "city": city,
            "temperature": temperatures.get(units, temperatures["fahrenheit"]),
            "units": units,
            "condition": random.choice(conditions)
        }

    # Fetch all cities concurrently using asyncio.gather
    weather_data = await asyncio.gather(
        *[fetch_city_weather(city) for city in cities]
    )

    return {
        "cities": weather_data,
        "total_cities": len(cities),
        "fetched_concurrently": True
    }


@app.tool(
    name="search_cities",
    description="Search for cities by name or region (async)"
)
async def search_cities(query: str, limit: int = 5) -> dict:
    """
    Search for cities matching a query using async operations.

    Args:
        query: Search query (city name or region)
        limit: Maximum number of results to return

    Returns:
        Dictionary containing matching cities
    """
    # Simulate async database query
    await asyncio.sleep(0.05)

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
        city for city in cities
        if query_lower in city["name"].lower() or query_lower in city["region"].lower()
    ]

    return {
        "query": query,
        "results": results[:limit],
        "total_found": len(results),
        "async": True
    }


# Example of running async tools directly (for testing)
async def test_async_tools():
    """Test function to demonstrate async tool execution."""
    print("\n=== Testing Async Tools ===\n")

    # Get weather for a single city
    print("1. Testing get_weather...")
    weather = await get_weather("New York")
    print(f"   Result: {weather}")

    # Get forecast
    print("\n2. Testing get_forecast...")
    forecast = await get_forecast("London", days=5)
    print(f"   Result: {forecast}")

    # Get batch weather (concurrent execution)
    print("\n3. Testing get_batch_weather (concurrent)...")
    cities = ["New York", "London", "Tokyo", "Paris"]
    batch_weather = await get_batch_weather(cities)
    print(f"   Result: Fetched weather for {len(cities)} cities concurrently")

    # Search cities
    print("\n4. Testing search_cities...")
    results = await search_cities("new")
    print(f"   Result: Found {results['total_found']} cities")

    print("\n=== All Tests Passed! ===\n")


# Run the application
if __name__ == "__main__":
    print("Starting Async Weather Bot MCP Server...")
    print("Registered tools:", list(app.get_tools().keys()))

    # Run async tests
    print("\nRunning async tool tests...")
    asyncio.run(test_async_tools())

    print("\nReady to serve MCP requests!")
    # app.run()  # Uncomment when FastMCP async support is ready
