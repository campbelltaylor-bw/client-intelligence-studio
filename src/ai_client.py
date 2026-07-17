import anthropic


class AnthropicClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def call(self, messages: list[dict], system_prompt: str = "") -> str:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        ) as stream:
            return stream.get_final_message().content[0].text

    def call_with_tools(self, messages: list[dict], tools: list[dict], system_prompt: str = "") -> str:
        """Run a tool-use loop with beta tools (e.g. web_search). Returns final text."""
        msgs = list(messages)
        for _ in range(10):
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system_prompt,
                messages=msgs,
                tools=tools,
                betas=["web-search-2025-03-05"],
            )
            texts = [b.text for b in response.content if hasattr(b, "text") and b.type == "text"]
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason == "end_turn" or not tool_uses:
                return " ".join(texts)
            msgs.append({"role": "assistant", "content": response.content})
            msgs.append({
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tu.id, "content": ""}
                    for tu in tool_uses
                ],
            })
        return ""
