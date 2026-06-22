"""MarkItDown MCP server — converts files and URLs to Markdown using Microsoft's MarkItDown."""

from __future__ import annotations

import os
from pathlib import Path

from markitdown import MarkItDown
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls",
    # Web / markup
    ".html", ".htm", ".xml",
    # Plain text / data
    ".txt", ".csv", ".tsv", ".json",
    # Images (needs vision-capable LLM configured)
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    # Audio (needs speech model)
    ".mp3", ".wav", ".m4a",
    # E-book
    ".epub",
    # ZIP archives
    ".zip",
}


def _convert_source(source: str, llm_client=None, llm_model: str | None = None) -> str:
    kwargs: dict = {}
    if llm_client:
        kwargs["llm_client"] = llm_client
        if llm_model:
            kwargs["llm_model"] = llm_model

    md = MarkItDown(**kwargs)
    result = md.convert(source)
    return result.text_content or "[No content extracted]"


def _make_llm_client(api_key: str):
    """Return an Anthropic client wrapped for MarkItDown's OpenAI-compatible interface."""
    try:
        import anthropic

        class _AnthropicAdapter:
            """Minimal OpenAI-compatible wrapper around Anthropic for MarkItDown."""

            def __init__(self, key: str):
                self._client = anthropic.Anthropic(api_key=key)

            class chat:
                class completions:
                    @staticmethod
                    def create(model, messages, max_tokens=1024, **_):
                        import anthropic as _a

                        client = _a.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
                        # Convert OpenAI-style messages to Anthropic format
                        anthropic_messages = []
                        system = ""
                        for m in messages:
                            if m["role"] == "system":
                                system = m["content"]
                            else:
                                anthropic_messages.append({"role": m["role"], "content": m["content"]})
                        resp = client.messages.create(
                            model=model,
                            max_tokens=max_tokens,
                            system=system,
                            messages=anthropic_messages,
                        )

                        class _Choice:
                            class message:
                                content = resp.content[0].text

                        class _Resp:
                            choices = [_Choice()]

                        return _Resp()

        return _AnthropicAdapter(api_key)
    except Exception:
        return None


def build_server() -> Server:
    server = Server("markitdown-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="convert_file",
                description=(
                    "Convert a local file to Markdown. Supports PDF, Word (.docx), "
                    "PowerPoint (.pptx), Excel (.xlsx), HTML, CSV, JSON, images, audio, "
                    "EPUB, ZIP archives, and plain text files."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute or relative path to the file to convert.",
                        },
                        "use_llm": {
                            "type": "boolean",
                            "description": (
                                "Enable LLM-assisted conversion for images and audio "
                                "(requires ANTHROPIC_API_KEY). Defaults to false."
                            ),
                            "default": False,
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="convert_url",
                description=(
                    "Fetch a URL and convert its content to Markdown. Works with web pages, "
                    "YouTube video URLs (transcript), and direct file links."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to fetch and convert.",
                        },
                        "use_llm": {
                            "type": "boolean",
                            "description": (
                                "Enable LLM-assisted conversion for images/audio content "
                                "(requires ANTHROPIC_API_KEY). Defaults to false."
                            ),
                            "default": False,
                        },
                    },
                    "required": ["url"],
                },
            ),
            Tool(
                name="list_supported_formats",
                description="List all file formats supported by the convert_file tool.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "list_supported_formats":
                exts = sorted(SUPPORTED_EXTENSIONS)
                result = "Supported file extensions:\n" + "\n".join(f"  {e}" for e in exts)

            elif name in ("convert_file", "convert_url"):
                use_llm = arguments.get("use_llm", False)
                llm_client = None
                llm_model = None

                if use_llm:
                    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                    if not api_key:
                        return [TextContent(
                            type="text",
                            text="Error: use_llm=true requires ANTHROPIC_API_KEY to be set.",
                        )]
                    llm_client = _make_llm_client(api_key)
                    llm_model = "claude-haiku-4-5-20251001"

                if name == "convert_file":
                    path = Path(arguments["file_path"]).expanduser().resolve()
                    if not path.exists():
                        return [TextContent(type="text", text=f"Error: File not found: {arguments['file_path']}")]
                    result = _convert_source(str(path), llm_client, llm_model)
                else:
                    result = _convert_source(arguments["url"], llm_client, llm_model)

            else:
                result = f"Unknown tool: {name}"

        except Exception as exc:
            result = f"Error: {exc}"

        return [TextContent(type="text", text=result)]

    return server


async def _run() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    main()
