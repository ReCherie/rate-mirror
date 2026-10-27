"""静态页面 + AI 解析接口（stdlib，无需 Flask）。

启动：
    cd rate-mirror && python3 web/server.py
访问：
    http://localhost:8600
"""
from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.parse import normalize_installments, parse_bill_text  # noqa: E402

WEB = ROOT / "web"
PORT = 8600


def _load_key() -> None:
    """环境变量里没有 key 时，尝试从 ~/.zshrc 读取（方便直接跑）。"""
    if os.getenv("DEEPSEEK_API_KEY"):
        return
    rc = Path.home() / ".zshrc"
    if rc.exists():
        m = re.search(r'export\s+DEEPSEEK_API_KEY=["\']?([\w\-]+)', rc.read_text(encoding="utf-8", errors="ignore"))
        if m:
            os.environ["DEEPSEEK_API_KEY"] = m.group(1)


def nominal_apr(text: str) -> float | None:
    """把标称话术换算成名义年化百分比，用于对比条形图。"""
    if not text:
        return None
    t = text.replace("％", "%")
    if "免息" in t and "%" not in t:
        return 0.0
    if m := re.search(r"日息\s*万\s*([一二三四五六七八九十\d])", t):
        cn = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        v = cn.get(m.group(1), None) or (int(m.group(1)) if m.group(1).isdigit() else 5)
        return round(v / 10000 * 365 * 100, 2)      # 日万分之 v → 单利年化
    if m := re.search(r"(\d+(?:\.\d+)?)\s*%", t):
        v = float(m.group(1))
        return round(v * 12, 2) if ("月" in t or "每期" in t) else round(v * 12, 2)
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 静音访问日志
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = "/index.html" if self.path in ("/", "") else self.path.split("?")[0]
        file = (WEB / path.lstrip("/")).resolve()
        if not str(file).startswith(str(WEB)) or not file.exists():
            self._send(404, b'{"error":"not found"}')
            return
        ctype = {"html": "text/html; charset=utf-8", "js": "text/javascript", "css": "text/css",
                 "png": "image/png", "svg": "image/svg+xml"}.get(file.suffix.lstrip("."), "application/octet-stream")
        self._send(200, file.read_bytes(), ctype)

    def do_POST(self):
        _load_key()                              # 每次请求重读，改 key 后无需重启
        if self.path != "/api/parse":
            self._send(404, b'{"error":"not found"}')
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            text = (payload.get("text") or "").strip()
            if not text:
                self._send(400, json.dumps({"error": "文本为空"}, ensure_ascii=False).encode())
                return
            fields = parse_bill_text(text)
            inst = normalize_installments(fields)
            out = {
                "principal": float(fields.get("principal") or 0),
                "periods": len(inst),
                "installments": inst,
                "upfront_fee": float(fields.get("upfront_fee") or 0),
                "fee_names": fields.get("fee_names") or [],
                "nominal_text": fields.get("nominal_rate") or "",
                "nominal_apr": nominal_apr(fields.get("nominal_rate") or ""),
            }
            self._send(200, json.dumps(out, ensure_ascii=False).encode())
        except RuntimeError as e:                    # 未配置 API Key
            self._send(400, json.dumps({"error": str(e)}, ensure_ascii=False).encode())
        except Exception as e:                        # noqa: BLE001
            self._send(500, json.dumps({"error": f"解析失败：{e}"}, ensure_ascii=False).encode())


if __name__ == "__main__":
    _load_key()
    print(f"服务已启动：http://localhost:{PORT}  (API Key: {'已加载' if os.getenv('DEEPSEEK_API_KEY') else '未配置，仅手动模式可用'})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
