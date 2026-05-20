import json
import os

from anthropic import AnthropicBedrockMantle
from rich import print
from rich.text import Text

client = AnthropicBedrockMantle(
    aws_region="eu-north-1",
)

# Context prompt: read all the files in this porject and print a one liner about this project


def _print_truncated(prefix: str, content: str, max_width: int = 100):
    """Print a string, truncating with ellipsis if it exceeds max_width using rich."""
    text = Text(f"{prefix} {content}")
    text.truncate(max_width=max_width, overflow="ellipsis")
    print(text)


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

VIEW_TOOL = {
    "name": "view",
    "description": "Read a file or list directory contents. Cannot access paths outside the current working directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path from current working directory to a file or directory",
            }
        },
        "required": ["path"],
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


def view(path: str) -> str:
    """Read a file or list directory contents, restricted to current workdir."""
    cwd = os.path.abspath(os.getcwd())
    requested = os.path.abspath(os.path.join(cwd, path))

    # Security: prevent traversal outside cwd
    if not requested.startswith(cwd + os.sep) and requested != cwd:
        return json.dumps({"error": "Access denied: path outside working directory"})

    if os.path.isfile(requested):
        try:
            with open(requested, "r", encoding="utf-8") as f:
                content = f.read()
            return json.dumps({"path": path, "type": "file", "content": content})
        except Exception as e:
            return json.dumps({"error": f"Failed to read file: {str(e)}"})
    elif os.path.isdir(requested):
        try:
            entries = os.listdir(requested)
            return json.dumps({"path": path, "type": "directory", "entries": entries})
        except Exception as e:
            return json.dumps({"error": f"Failed to list directory: {str(e)}"})
    else:
        return json.dumps({"error": f"Path not found: {path}"})


_PREVIOUSLY_SENT = None


def _get_context_window(client, model: str) -> int:
    """Fetch the model's max input tokens from the Anthropic SDK."""
    try:
        info = client.models.retrieve(model_id=model)
        return info.max_input_tokens or 200_000
    except Exception:
        return 200_000


def _serialize_messages(messages: list[dict]) -> str:
    """Serialize messages to JSON, delegating SDK object serialization to model_dump()."""

    def default(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(messages, default=default, indent=2)


def _summarize_history(
    messages: list[dict],
    client,
    model: str,
    utilization: float,
    context_threshold: float,
) -> list[dict]:
    """Strategy 1: Summarize old messages when context utilization exceeds a threshold."""
    if utilization <= context_threshold:
        return messages

    summary_resp = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"Summarize this conversation history concisely:\n{_serialize_messages(messages)}",
            }
        ],
    )
    summary_text = summary_resp.content[0].text
    return [
        {"role": "user", "content": f"[Previous conversation summary]: {summary_text}"},
    ]


def _drop_old_tool_results(
    messages: list[dict],
    utilization: float,
    context_threshold: float,
    retain_last: int,
) -> list[dict]:
    """Strategy 2: Replace old tool_result content with [truncated] when context exceeds threshold.

    retain_last -- how many of the most recent tool_result messages to keep as-is.
    """
    if utilization <= context_threshold:
        return messages

    kept = 0
    projected = []
    for msg in reversed(messages):
        content = msg.get("content", [])
        is_tool_result = isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        )
        if is_tool_result:
            kept += 1
            if kept > retain_last:
                msg = {
                    **msg,
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": next(
                                b["tool_use_id"]
                                for b in content
                                if isinstance(b, dict)
                                and b.get("type") == "tool_result"
                            ),
                            "content": "[truncated]",
                        }
                    ],
                }
        projected.append(msg)
    return list(reversed(projected))


def _compute_cache_efficiency(previous, current) -> float:
    """Estimate cache efficiency by prefix-matching against previous payload."""
    if not previous or not current:
        return 0.0
    matched = 0
    for prev_msg, curr_msg in zip(previous, current):
        if prev_msg == curr_msg:
            matched += 1
        else:
            break
    return matched / len(current)


def project_context(
    messages: list[dict],
    client,
    model: str,
    tools: list[dict],
) -> list[dict]:
    """
    Project (transform/filter) the conversation context before sending to the LLM.

    This is the hook for context management techniques such as:
      - Sliding-window truncation (keep only the last N messages)
      - Token-budget summarization (compress early turns into a summary)
      - Relevance filtering (drop messages below a similarity threshold)
      - Structured injection (prepend system prompts or RAG context)

    Currently a no-op: returns messages unchanged.
    """
    global _PREVIOUSLY_SENT

    count_before = client.messages.count_tokens(
        model=model,
        tools=tools,
        messages=messages,
    )

    context_window = _get_context_window(client, model)
    utilization_before = (count_before.input_tokens / context_window) * 100

    # Cache efficiency BEFORE projection
    cache_before = _compute_cache_efficiency(_PREVIOUSLY_SENT, messages)

    projected = messages  # no-op for now

    # Uncomment ONE strategy below to enable context projection:
    # projected = _summarize_history(
    #     messages, client, model, utilization_before, context_threshold=1.0
    # )
    # projected = _drop_old_tool_results(
    #     messages, utilization_before, context_threshold=1.0, retain_last=3
    # )

    count_after = client.messages.count_tokens(
        model=model,
        tools=tools,
        messages=projected,
    )
    utilization_after = (count_after.input_tokens / context_window) * 100

    # Cache efficiency AFTER projection
    cache_after = _compute_cache_efficiency(_PREVIOUSLY_SENT, projected)

    print(
        f"[Context] {len(messages)} messages | "
        f"input_tokens before={count_before.input_tokens} ({utilization_before:.1f}%) "
        f"after={count_after.input_tokens} ({utilization_after:.1f}%) | "
        f"cache before={cache_before:.1%} after={cache_after:.1%}"
    )

    # Snapshot current payload for next comparison
    _PREVIOUSLY_SENT = [m.copy() for m in messages]

    return projected


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

        # Project context immediately before the LLM call
        projected_messages = project_context(
            messages,
            client=client,
            model="anthropic.claude-haiku-4-5",
            tools=[GET_WEATHER_TOOL, VIEW_TOOL],
        )

        response = client.messages.create(
            model="anthropic.claude-haiku-4-5",
            max_tokens=1024,
            tools=[GET_WEATHER_TOOL, VIEW_TOOL],
            messages=projected_messages,
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
                elif tool.name == "view":
                    result = view(**tool.input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool.name}"})

                _print_truncated("[Assistant → Tool]", f" {tool.name}({tool.input})")
                _print_truncated("[Tool → Assistant]", f" {result}")

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
