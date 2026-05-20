import json

from anthropic import AnthropicBedrockMantle
from rich import print

client = AnthropicBedrockMantle(
    aws_region="eu-north-1",
)


GET_WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Get the current weather for a given location.",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city, for example, Cairo, EG",
            }
        },
        "required": ["location"],
    },
}


def get_weather(location: str) -> str:
    """The actual implementation the agent will execute."""
    return json.dumps(
        {
            "location": location,
            "temperature": "40°C",
            "condition": "Sunny",
        }
    )


messages = []

try:
    while True:
        if not messages or messages[-1]["role"] == "assistant":
            # Block on user input when there's no pending tool call
            try:
                user_input = input("\n[User] ")
            except KeyboardInterrupt:
                print("\n[Agent] Interrupted. Goodbye!")
                break
            if user_input.lower() in ("exit", "quit"):
                break

            messages.append(
                {
                    "role": "user",
                    "content": user_input,
                }
            )

        response = client.messages.create(
            model="anthropic.claude-haiku-4-5",
            max_tokens=1024,
            tools=[GET_WEATHER_TOOL],
            messages=messages,
        )

        messages.append(
            {
                "role": "assistant",
                "content": response.content,
            }
        )

        if response.stop_reason == "tool_use":
            tool_calls = [c for c in response.content if c.type == "tool_use"]

            for tool in tool_calls:
                if tool.name == "get_weather":
                    result = get_weather(**tool.input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool.name}"})

                print(f"[Assistant → Tool] {tool.name}({tool.input})")
                print(f"[Tool → Assistant] {result}")

                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool.id,
                                "content": result,
                            }
                        ],
                    }
                )
            # Loop back to send tool results to the model

        elif response.stop_reason == "end_turn":
            # Print the assistant's text response and block for more user input
            for block in response.content:
                if block.type == "text":
                    print(f"[Assistant] {block.text}")
            # Loop back to prompt for user input

        else:
            print(f"[Assistant] (stop_reason: {response.stop_reason})")
            for block in response.content:
                if block.type == "text":
                    print(block.text)
except KeyboardInterrupt:
    print("\n[Agent] Interrupted. Goodbye!")
