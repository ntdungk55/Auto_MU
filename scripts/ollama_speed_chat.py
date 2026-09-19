#!/usr/bin/env python3
"""Interactive Ollama chat with Cloudflare Access and speed measurements."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://myllm.mcp88.uk/v1"


def environment_value(name: str) -> str:
    """Read the process environment, then the persistent Windows user environment."""
    value = str(os.environ.get(name, "") or "").strip()
    if value or os.name != "nt":
        return value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
        return str(value or "").strip()
    except (FileNotFoundError, OSError):
        return ""


def api_root(base_url: str) -> str:
    root = str(base_url or "").strip().rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3]
    if not root.startswith(("http://", "https://")):
        raise ValueError("Base URL phải bắt đầu bằng http:// hoặc https://")
    return root.rstrip("/")


def access_headers() -> dict[str, str]:
    client_id = environment_value("CF_ACCESS_CLIENT_ID")
    client_secret = environment_value("CF_ACCESS_CLIENT_SECRET")
    missing = [
        name
        for name, value in (
            ("CF_ACCESS_CLIENT_ID", client_id),
            ("CF_ACCESS_CLIENT_SECRET", client_secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Thiếu biến môi trường: {', '.join(missing)}")
    return {
        "CF-Access-Client-Id": client_id,
        "CF-Access-Client-Secret": client_secret,
        "Accept": "application/json",
        "User-Agent": "ollama-speed-chat/1.0",
    }


def request_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"HTTP {error.code} từ {url}: {detail or error.reason}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Không kết nối được {url}: {error.reason}") from error


def list_models(root: str, headers: dict[str, str], timeout: float) -> list[str]:
    payload = request_json(f"{root}/api/tags", headers, timeout)
    return [
        str(item.get("name") or item.get("model") or "").strip()
        for item in payload.get("models", [])
        if str(item.get("name") or item.get("model") or "").strip()
    ]


def choose_model(models: list[str], current: str | None = None) -> str:
    if not models:
        raise RuntimeError("Ollama không trả về model nào")
    print("\nModel có sẵn:")
    for index, model in enumerate(models, start=1):
        marker = " *" if model == current else ""
        print(f"  {index:>2}. {model}{marker}")
    while True:
        raw = input("Chọn model (số hoặc tên): ").strip()
        if raw in models:
            return raw
        try:
            selected = int(raw)
        except ValueError:
            selected = 0
        if 1 <= selected <= len(models):
            return models[selected - 1]
        print("Lựa chọn không hợp lệ.")


def seconds(nanoseconds: Any) -> float:
    try:
        return max(0.0, float(nanoseconds) / 1_000_000_000)
    except (TypeError, ValueError):
        return 0.0


def stream_chat(
    root: str,
    headers: dict[str, str],
    model: str,
    messages: list[dict[str, str]],
    *,
    timeout: float,
    num_predict: int,
    think: bool,
) -> tuple[str, dict[str, Any]]:
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": True,
            "think": think,
            "options": {"num_predict": num_predict},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request_headers = dict(headers)
    request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{root}/api/chat",
        data=body,
        headers=request_headers,
        method="POST",
    )
    started = time.perf_counter()
    first_token_at: float | None = None
    chunks: list[str] = []
    final: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                item = json.loads(line)
                message = item.get("message") or {}
                content = str(message.get("content") or "")
                thinking = str(message.get("thinking") or "")
                visible = thinking if think and thinking else content
                if visible:
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                    print(visible, end="", flush=True)
                if content:
                    chunks.append(content)
                if item.get("done"):
                    final = item
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"HTTP {error.code}: {detail or error.reason}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Lỗi kết nối: {error.reason}") from error

    finished = time.perf_counter()
    print()
    metrics = {
        "wall_seconds": finished - started,
        "ttft_seconds": (first_token_at - started) if first_token_at else None,
        "load_seconds": seconds(final.get("load_duration")),
        "prompt_tokens": int(final.get("prompt_eval_count") or 0),
        "prompt_seconds": seconds(final.get("prompt_eval_duration")),
        "output_tokens": int(final.get("eval_count") or 0),
        "output_seconds": seconds(final.get("eval_duration")),
    }
    return "".join(chunks), metrics


def print_metrics(metrics: dict[str, Any]) -> None:
    output_tokens = int(metrics["output_tokens"])
    output_seconds = float(metrics["output_seconds"])
    prompt_tokens = int(metrics["prompt_tokens"])
    prompt_seconds = float(metrics["prompt_seconds"])
    server_speed = output_tokens / output_seconds if output_seconds > 0 else 0.0
    prompt_speed = prompt_tokens / prompt_seconds if prompt_seconds > 0 else 0.0
    ttft = metrics["ttft_seconds"]
    print("\n--- Speed ---")
    print(f"TTFT:          {ttft:.3f} s" if ttft is not None else "TTFT:          n/a")
    print(f"Tổng thời gian: {metrics['wall_seconds']:.3f} s")
    print(f"Load model:     {metrics['load_seconds']:.3f} s")
    print(f"Prompt:         {prompt_tokens} token | {prompt_speed:.2f} token/s")
    print(f"Output:         {output_tokens} token | {server_speed:.2f} token/s")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Ollama URL, có thể kết thúc bằng /v1")
    result.add_argument("--model", help="Bỏ qua menu chọn model")
    result.add_argument("--prompt", help="Gửi một prompt rồi thoát")
    result.add_argument("--system", default="You are a helpful assistant.", help="System prompt")
    result.add_argument("--num-predict", type=int, default=512, help="Số output token tối đa")
    result.add_argument("--timeout", type=float, default=600.0, help="Timeout mỗi request, tính bằng giây")
    result.add_argument("--think", action="store_true", help="Bật chế độ thinking nếu model hỗ trợ")
    result.add_argument("--list-models", action="store_true", help="Chỉ in danh sách model")
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = parser().parse_args()
    if args.num_predict <= 0 or args.timeout <= 0:
        print("--num-predict và --timeout phải lớn hơn 0", file=sys.stderr)
        return 2
    try:
        root = api_root(args.base_url)
        headers = access_headers()
        models = list_models(root, headers, args.timeout)
        if args.list_models:
            print("\n".join(models))
            return 0
        model = args.model or choose_model(models)
        if model not in models:
            raise RuntimeError(f"Model không tồn tại trên server: {model}")
        messages: list[dict[str, str]] = [{"role": "system", "content": args.system}]
        print(f"\nEndpoint: {root}")
        print(f"Model:    {model}")
        print("Lệnh: /model, /clear, /exit\n")

        pending_prompt = args.prompt
        while True:
            prompt = pending_prompt if pending_prompt is not None else input("Bạn: ").strip()
            pending_prompt = None
            if not prompt:
                if args.prompt is not None:
                    return 0
                continue
            command = prompt.casefold()
            if command in {"/exit", "/quit"}:
                return 0
            if command == "/clear":
                messages = [messages[0]]
                print("Đã xóa lịch sử hội thoại.\n")
                continue
            if command == "/model":
                model = choose_model(models, current=model)
                messages = [messages[0]]
                print(f"Đã chuyển sang {model}; lịch sử đã được xóa.\n")
                continue

            messages.append({"role": "user", "content": prompt})
            print("AI: ", end="", flush=True)
            answer, metrics = stream_chat(
                root,
                headers,
                model,
                messages,
                timeout=args.timeout,
                num_predict=args.num_predict,
                think=args.think,
            )
            messages.append({"role": "assistant", "content": answer})
            print_metrics(metrics)
            print()
            if args.prompt is not None:
                return 0
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Lỗi: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nĐã dừng.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
