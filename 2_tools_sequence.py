import json
import textwrap

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


# Column positions (0-indexed) for the three lifelines
USER_COL = 3
LLM_COL = 35
TOOL_COL = 67
LINE_WIDTH = 78


def lifeline():
    """Return a line with │ at each column position, spaces elsewhere."""
    line = [" "] * LINE_WIDTH
    line[USER_COL] = "│"
    line[LLM_COL] = "│"
    line[TOOL_COL] = "│"
    return "".join(line)


def text_lines(text, seg_idx):
    """Wrap text and place it in segment seg_idx (0=User→LLM, 1=LLM→Tool)."""
    start = [USER_COL, LLM_COL][seg_idx] + 2
    end = [LLM_COL, TOOL_COL][seg_idx]
    avail = end - start - 1
    wrapped = textwrap.wrap(text, width=avail) or [""]
    out = []
    for w in wrapped:
        line = list(lifeline())
        for i, ch in enumerate(w):
            if start + i < end:
                line[start + i] = ch
        out.append("".join(line))
    return out


def arrow(from_idx, to_idx):
    """Draw an arrow between two columns (0=User, 1=LLM, 2=Tool)."""
    cols = [USER_COL, LLM_COL, TOOL_COL]
    line = list(lifeline())
    a, b = sorted([cols[from_idx], cols[to_idx]])
    for i in range(a + 1, b):
        line[i] = "─"
    if from_idx < to_idx:
        line[b - 1] = ">"
    else:
        line[a + 1] = "<"
    return "".join(line)


def print_diagram_header():
    print("┌─────┐                         ┌─────┐                      ┌────────────┐")
    print("│User │                         │ LLM │                      │get_weather │")
    print("└──┬──┘                         └──┬──┘                      └─────┬──────┘")


def print_diagram_footer():
    print(lifeline())
    print("┌──┴──┐                         ┌──┴──┐                      ┌─────┴─────┐")
    print("│User │                         │ LLM │                      │get_weather│")
    print("└─────┘                         └─────┘                      └───────────┘")


print_diagram_header()
print(lifeline())

# Step 1: User asks
for ln in text_lines("How's the weather in Cairo?", 0):
    print(ln)
print(arrow(0, 1))

response = client.messages.create(
    model="anthropic.claude-haiku-4-5",
    max_tokens=1024,
    tools=[GET_WEATHER_TOOL],
    messages=messages,
)

tool_call = response.content[0]

# Step 2: LLM calls tool
for ln in text_lines(f"{tool_call.name}({tool_call.input})", 1):
    print(ln)
print(arrow(1, 2))

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

        # Step 3: Tool returns result
        for ln in text_lines(result, 1):
            print(ln)
        print(arrow(2, 1))

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

    # Step 4: LLM replies to user
    for ln in text_lines(final_response.content[0].text, 0):
        print(ln)
    print(arrow(1, 0))

print_diagram_footer()
