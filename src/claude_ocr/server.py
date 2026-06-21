"""OCR MCP server — exposes ocr_file, ocr_url, and ocr_base64 tools for Claude."""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

import anthropic
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SUPPORTED_MIME = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

OCR_PROMPT = (
    "Extract ALL text visible in this image exactly as it appears. "
    "Preserve the original layout, line breaks, and structure where possible. "
    "Do not add explanations or summaries — output only the extracted text. "
    "If no text is visible, respond with: [No text found]"
)


def _guess_mime(path_or_name: str) -> str:
    mime, _ = mimetypes.guess_type(path_or_name)
    if mime in SUPPORTED_MIME:
        return mime
    return "image/jpeg"


def _call_claude_vision(image_b64: str, media_type: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ],
    )
    return message.content[0].text


def ocr_from_file(file_path: str, api_key: str) -> str:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    raw = path.read_bytes()
    image_b64 = base64.standard_b64encode(raw).decode()
    media_type = _guess_mime(path.name)
    return _call_claude_vision(image_b64, media_type, api_key)


def ocr_from_url(url: str, api_key: str) -> str:
    with httpx.Client(follow_redirects=True, timeout=30) as client:
        response = client.get(url)
        response.raise_for_status()
    content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    if content_type not in SUPPORTED_MIME:
        content_type = _guess_mime(url)
    image_b64 = base64.standard_b64encode(response.content).decode()
    return _call_claude_vision(image_b64, content_type, api_key)


def ocr_from_base64(data: str, media_type: str, api_key: str) -> str:
    if media_type not in SUPPORTED_MIME:
        raise ValueError(
            f"Unsupported media type '{media_type}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_MIME))}"
        )
    # Strip data URI prefix if present
    if "," in data:
        data = data.split(",", 1)[1]
    return _call_claude_vision(data, media_type, api_key)


def build_server() -> Server:
    server = Server("claude-ocr")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="ocr_file",
                description=(
                    "Extract text from a local image file using Claude's vision. "
                    "Supports JPEG, PNG, GIF, and WebP."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute or relative path to the image file.",
                        }
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="ocr_url",
                description=(
                    "Download an image from a URL and extract its text using Claude's vision. "
                    "Supports JPEG, PNG, GIF, and WebP."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Public URL of the image to process.",
                        }
                    },
                    "required": ["url"],
                },
            ),
            Tool(
                name="ocr_base64",
                description=(
                    "Extract text from a base64-encoded image using Claude's vision. "
                    "Accepts raw base64 or a data URI (data:<mime>;base64,<data>)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "string",
                            "description": "Base64-encoded image data or data URI string.",
                        },
                        "media_type": {
                            "type": "string",
                            "enum": sorted(SUPPORTED_MIME),
                            "description": "MIME type of the image (e.g. image/png). Ignored when a data URI is passed.",
                        },
                    },
                    "required": ["data", "media_type"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return [TextContent(type="text", text="Error: ANTHROPIC_API_KEY environment variable is not set.")]

        try:
            if name == "ocr_file":
                result = ocr_from_file(arguments["file_path"], api_key)
            elif name == "ocr_url":
                result = ocr_from_url(arguments["url"], api_key)
            elif name == "ocr_base64":
                result = ocr_from_base64(arguments["data"], arguments["media_type"], api_key)
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
