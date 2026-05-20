from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(
    aws_region="eu-north-1",
)

message = client.messages.create(
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "Heyo, Claude",
        }
    ],
    model="anthropic.claude-haiku-4-5",
)

print(message.content[0].text)
