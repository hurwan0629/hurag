"""실행: python -B app.py / 브라우저: http://127.0.0.1:8001"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.environ["HF_HOME"] = str(BASE / ".cache" / "huggingface")
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
ORIGIN = "http://127.0.0.1:8001"


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("Host") != "127.0.0.1:8001":
            self.send_error(403)
        elif self.path == "/":
            self.respond(200, (BASE / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        if (self.headers.get("Host") != "127.0.0.1:8001"
                or self.headers.get("Origin") != ORIGIN):
            self.respond(403, {"error": "로컬 실험 페이지에서만 요청할 수 있습니다."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                raise ValueError("요청 크기가 올바르지 않습니다.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("JSON 객체가 필요합니다.")
            if self.path == "/api/folder":
                import tkinter as tk
                from tkinter.filedialog import askdirectory
                window = tk.Tk()
                window.withdraw()
                window.attributes("-topmost", True)
                try:
                    result = {"folder": askdirectory(parent=window, title="Markdown 폴더 선택")}
                finally:
                    window.destroy()
            elif self.path in ("/api/sync", "/api/search"):
                if self.server.retrieval is None:
                    from sentence_transformers import SentenceTransformer
                    from retrieval import Retrieval
                    self.server.retrieval = Retrieval(SentenceTransformer(
                        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        cache_folder=str(BASE / ".cache" / "models"), device="cpu",
                    ))
                engine = self.server.retrieval
                print(f"folers: {data.get("folders")}")
                print(f"query: {data.get("query")}")
                result = (engine.sync(data.get("folders")) if self.path == "/api/sync"
                          else {"hits": engine.search(data.get("query"))})
            else:
                self.respond(404, {"error": "없는 API입니다."})
                return
            self.respond(200, result)
        except (ValueError, OSError) as error:
            self.respond(400, {"error": str(error)})
        except Exception as error:
            self.respond(500, {"error": f"{type(error).__name__}: {error}"})


if __name__ == "__main__":
    # 단일 요청 처리로 폴더 선택과 인덱스 갱신을 직렬화한다.
    with HTTPServer(("127.0.0.1", 8001), Handler) as server:
        server.retrieval = None
        print(f"브라우저에서 {ORIGIN} 을 여세요. 종료: Ctrl+C", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
