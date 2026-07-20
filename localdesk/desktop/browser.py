"""受控的公开网页读取 adapter。

第一版不处理登录、验证码、表单提交、下载或 Cookie；它只读取用户授权域名的
HTTPS 页面，并将网页视为不可信资料而不是可执行指令。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Protocol

import httpx


class BrowserError(ValueError):
    pass


@dataclass(frozen=True)
class WebChunk:
    chunk_id: str
    url: str
    title: str
    text: str
    accessed_at: str

    def citation(self) -> str:
        return f"{self.title} ({self.url}; accessed {self.accessed_at})"


class BrowserAdapter(Protocol):
    def open(self, url: str) -> WebChunk: ...


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = "Untitled web page"
        self._in_title = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title = text
        self._parts.append(text)

    def result(self) -> tuple[str, str]:
        return self.title, " ".join(self._parts)


class HttpBrowserAdapter:
    def __init__(self, timeout_seconds: float = 15, max_chars: int = 30_000) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_chars = max_chars

    def open(self, url: str) -> WebChunk:
        try:
            response = httpx.get(url, follow_redirects=True, timeout=self.timeout_seconds, headers={"User-Agent": "LocalDeskOfficeAgent/0.2"})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserError(f"网页读取失败: {exc}") from exc
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and "text/plain" not in content_type:
            raise BrowserError(f"拒绝非文本网页内容: {content_type or 'unknown'}")
        parser = _TextExtractor()
        parser.feed(response.text)
        title, text = parser.result()
        if not text:
            raise BrowserError("网页未提取到可用正文")
        return WebChunk(
            chunk_id=f"web:{response.url}",
            url=str(response.url),
            title=title,
            text=text[: self.max_chars],
            accessed_at=datetime.now(UTC).isoformat(),
        )


class FakeBrowserAdapter:
    """离线测试 adapter：仅返回预先声明的公开页面。"""

    def __init__(self, pages: dict[str, WebChunk]) -> None:
        self.pages = pages

    def open(self, url: str) -> WebChunk:
        try:
            return self.pages[url]
        except KeyError as exc:
            raise BrowserError(f"Fake browser has no page for: {url}") from exc
