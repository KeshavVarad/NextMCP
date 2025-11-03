# Async Weather Bot Example

This example demonstrates how to build an async MCP server using SecureMCP with full async/await support.

## Features

- **Async Tool Registration**: Register async functions as MCP tools
- **Async Middleware**: Use async middleware for logging, error handling, etc.
- **Concurrent Operations**: Fetch data from multiple sources concurrently
- **Real-world Patterns**: Demonstrates best practices for async applications

## Running the Example

```bash
cd examples/async_weather_bot
python app.py
```

## Tools Available

### 1. `get_weather`
Get current weather for a city using async operations.

```python
await get_weather("New York", units="fahrenheit")
```

### 2. `get_forecast`
Get weather forecast for the next few days.

```python
await get_forecast("London", days=5)
```

### 3. `get_batch_weather` (Concurrent)
Fetch weather for multiple cities **concurrently** - this demonstrates the power of async!

```python
await get_batch_weather(["New York", "London", "Tokyo", "Paris"])
```

This tool uses `asyncio.gather()` to fetch weather for all cities at the same time, rather than sequentially. For 4 cities with a 0.1s delay each:
- Sync approach: 0.4s (sequential)
- Async approach: ~0.1s (concurrent)

### 4. `search_cities`
Search for cities by name or region.

```python
await search_cities("new", limit=5)
```

## Key Concepts

### Async Tool Definition

```python
@app.tool()
async def my_async_tool(param: str) -> dict:
    # Use await for async operations
    result = await external_api_call(param)
    return result
```

### Async Middleware

```python
from securemcp import log_calls_async, error_handler_async

app.add_middleware(log_calls_async)
app.add_middleware(error_handler_async)
```

### Concurrent Operations

```python
# Fetch multiple items concurrently
results = await asyncio.gather(
    fetch_item_1(),
    fetch_item_2(),
    fetch_item_3()
)
```

## When to Use Async

Use async tools when:

1. **I/O-bound operations**: Network requests, database queries, file operations
2. **Multiple concurrent operations**: Fetching data from multiple sources
3. **External APIs**: Calling third-party services
4. **Long-running operations**: Tasks that wait for external resources

Don't use async for:

1. **CPU-bound operations**: Heavy computations, data processing
2. **Simple synchronous code**: When there's no I/O or waiting involved

## Real-World Usage

In a production application, you would use async HTTP clients like `httpx`:

```python
import httpx

@app.tool()
async def get_real_weather(city: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.weather.com/v1/current",
            params={"city": city, "apikey": API_KEY}
        )
        return response.json()
```

## Performance Benefits

Async shines when handling multiple I/O operations:

```python
# Sync: Total time = sum of all delays (1s + 1s + 1s = 3s)
def sync_fetch():
    result1 = api_call_1()  # 1 second
    result2 = api_call_2()  # 1 second
    result3 = api_call_3()  # 1 second
    return [result1, result2, result3]

# Async: Total time = max of all delays (~1s)
async def async_fetch():
    results = await asyncio.gather(
        api_call_1(),  # 1 second
        api_call_2(),  # 1 second
        api_call_3(),  # 1 second
    )
    return results
```

## Next Steps

- Add rate limiting with `rate_limit_async`
- Implement caching with `cache_results_async`
- Add authentication with `require_auth_async`
- Connect to real weather APIs
- Add timeout handling with `timeout_async`
