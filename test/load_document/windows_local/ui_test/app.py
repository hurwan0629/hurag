import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def list_markdown(folder):
    if not isinstance(folder, str) or not folder.strip():
        raise ValueError("폴더 경로를 입력하세요.")
    root = Path(folder.strip().strip('"')).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("폴더 경로가 아닙니다.")

    def raise_error(error):
        raise error

    files = []
    for directory, _, names in os.walk(root, onerror=raise_error):
        for name in names:
            if Path(name).suffix.lower() == ".md":
                files.append(str((Path(directory) / name).relative_to(root)))
    return {"folder": str(root), "files": sorted(files, key=str.casefold)}


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        self.respond(200, Path(__file__).with_name("index.html").read_bytes(),
                     "text/html; charset=utf-8")

    def do_POST(self):
        origin = "http://127.0.0.1:8000"
        if self.headers.get("Host") != "127.0.0.1:8000" or self.headers.get("Origin") != origin:
            self.send_error(403)
            return
        if self.path != "/api/files":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("요청 크기가 올바르지 않습니다.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("요청 형식이 올바르지 않습니다.")
            result = list_markdown(data.get("folder"))
            status = 200
        except (OSError, ValueError, RuntimeError) as error:
            status, result = 400, {"error": str(error)}
        self.respond(status, json.dumps(result, ensure_ascii=False).encode("utf-8"),
                     "application/json; charset=utf-8")


def self_test():
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "하위 폴더").mkdir()
        for name in ("a.md", "하위 폴더/B.MD", "ignore.txt"):
            (root / name).touch()
        assert list_markdown(directory)["files"] == ["a.md", str(Path("하위 폴더/B.MD"))]
        for invalid in ("", str(root / "a.md"), str(root / "missing")):
            try:
                list_markdown(invalid)
            except (ValueError, OSError):
                pass
            else:
                raise AssertionError(invalid)
    print("Self-test passed")


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        with ThreadingHTTPServer(("127.0.0.1", 8000), Handler) as server:
            print("브라우저에서 http://127.0.0.1:8000 을 여세요. 종료: Ctrl+C", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
