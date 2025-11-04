"""
WebSocket Chat Client - Example client for NextMCP WebSocket server

This example demonstrates:
- Connecting to a WebSocket server
- Invoking tools over WebSocket
- Listing available tools
- Real-time communication
"""

import asyncio
from nextmcp.transport import WebSocketClient


async def main():
    """Main client function."""
    server_uri = "ws://localhost:8765"

    print("=" * 60)
    print("WebSocket Chat Client")
    print("=" * 60)
    print(f"Connecting to: {server_uri}\n")

    try:
        async with WebSocketClient(server_uri) as client:
            print("✓ Connected successfully!\n")

            # List available tools
            print("1. Listing available tools...")
            tools_info = await client.list_tools()
            print(f"   Available tools ({len(tools_info['tools'])}):")
            for tool in tools_info["tools"]:
                print(f"   - {tool['name']}: {tool['description']}")
            print()

            # Test ping
            print("2. Testing connection (ping)...")
            pong = await client.ping()
            print(f"   Ping successful: {pong}\n")

            # Send a chat message
            print("3. Sending a chat message...")
            result = await client.invoke_tool(
                "send_message", {"username": "Alice", "message": "Hello from the WebSocket client!"}
            )
            print(f"   Message sent: {result['status']}")
            print(f"   Timestamp: {result['message']['timestamp']}\n")

            # Send another message
            print("4. Sending another message...")
            result = await client.invoke_tool(
                "send_message", {"username": "Bob", "message": "Hey Alice, WebSocket is awesome!"}
            )
            print(f"   Message sent: {result['status']}\n")

            # Get recent messages
            print("5. Retrieving recent messages...")
            result = await client.invoke_tool("get_messages", {"limit": 5})
            print(f"   Total messages in history: {result['total']}")
            print(f"   Recent messages:")
            for msg in result["messages"]:
                print(f"   [{msg['timestamp']}] {msg['username']}: {msg['message']}")
            print()

            # Get chat statistics
            print("6. Getting chat statistics...")
            stats = await client.invoke_tool("get_stats")
            print(f"   Total messages: {stats['total_messages']}")
            print(f"   Unique users: {stats['unique_users']}")
            print(f"   Users: {', '.join(stats['users'])}\n")

            # Test echo (concurrent calls)
            print("7. Testing concurrent tool invocation...")
            echo_tasks = [client.invoke_tool("echo", {"message": f"Message {i}"}) for i in range(5)]
            results = await asyncio.gather(*echo_tasks)
            print(f"   Sent 5 concurrent echo requests")
            print(f"   All received back successfully ✓\n")

            print("=" * 60)
            print("All tests completed successfully!")
            print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
