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


messages = [
    {
        "role": "user",
        "content": "How's the weather in Cairo?",
    }
]

print(f"[User] {messages[0]['content']}")

response = client.messages.create(
    model="anthropic.claude-haiku-4-5",
    max_tokens=1024,
    tools=[GET_WEATHER_TOOL],
    messages=messages,
)

print(f"[Assistant → Tool] {response.content[0].name}({response.content[0].input})")

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

    final_response = client.messages.create(
        model="anthropic.claude-haiku-4-5",
        max_tokens=1024,
        tools=[GET_WEATHER_TOOL],
        messages=messages,
    )

    print(f"[Assistant] {final_response.content[0].text}")
