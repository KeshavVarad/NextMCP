# Weather Bot Example

A simple weather information MCP server built with NextMCP.

## Features

This example demonstrates:
- Basic NextMCP application setup
- Tool registration with decorators
- Global middleware (logging, error handling)
- Configuration management
- Mock weather data generation

## Tools

### get_weather
Get current weather information for a city.

**Parameters:**
- `city` (string, required): Name of the city
- `units` (string, optional): Temperature units (fahrenheit or celsius)

### get_forecast
Get weather forecast for the next few days.

**Parameters:**
- `city` (string, required): Name of the city
- `days` (integer, optional): Number of days to forecast (1-7, default: 3)

### search_cities
Search for cities by name or region.

**Parameters:**
- `query` (string, required): Search query
- `limit` (integer, optional): Maximum number of results (default: 5)

## Running the Example

### Option 1: Direct execution
```bash
python app.py
```

### Option 2: Using the mcp CLI
```bash
mcp run app.py
```

### Option 3: With custom host/port
```bash
mcp run app.py --host 0.0.0.0 --port 8080
```

## Configuration

Edit `config.yaml` to customize:
- Server host and port
- Logging level
- Default temperature units
- Maximum forecast days

## Extending the Example

To make this a real weather bot:
1. Sign up for a weather API (e.g., OpenWeatherMap, WeatherAPI)
2. Add your API key to `.env` file
3. Replace mock data with actual API calls
4. Add error handling for API failures
5. Implement caching to reduce API calls

## Next Steps

- Add authentication middleware
- Implement rate limiting
- Add data validation with Pydantic schemas
- Create additional tools for alerts, historical data, etc.
- Deploy to production with proper error handling and monitoring
