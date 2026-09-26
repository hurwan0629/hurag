"""python -B test_retrieval.py: 다운로드 없이 파이프라인 계약 검증."""
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from retrieval import Retrieval


class FakeModel:
    """의미 품질 평가용이 아닌, 순위/청킹/실패 보존 검증용 고정 임베딩."""
    max_seq_length = 8
    broken = False

    def __init__(self):
        self.tokenizer = self

    def num_special_tokens_to_add(self, pair=False):
        return 2

    def encode(self, text, add_special_tokens=True, **kwargs):
        if isinstance(text, str):
            return text.split() + (["SPECIAL", "SPECIAL"] if add_special_tokens else [])
        if self.broken:
            raise RuntimeError("embedding failed")
        vectors = np.array([[item.split().count("apple"), 1] for item in text], dtype=float)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def decode(self, tokens, **kwargs):
        return " ".join(tokens)


def main():
    model = FakeModel()
    engine = Retrieval(model)
    assert engine.search("apple") == []
    # 임시 파일도 요청된 실험 디렉터리 안에서만 생성한다.
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        root = Path(directory)
        (root / "nested").mkdir()
        (root / "best.md").write_text("apple " * 13, encoding="utf-8")
        (root / "nested" / "second.MD").write_text("apple banana", encoding="utf-8")
        (root / "empty.md").write_text("   ", encoding="utf-8")
        (root / "ignore.txt").write_text("apple", encoding="utf-8")
        for i in range(5):
            (root / f"other{i}.md").write_text("banana", encoding="utf-8")
        stats = engine.sync([str(root), str(root / "nested")])
        assert stats["documents"] == 8 and stats["empty"] == 1
        assert stats["chunks"] == 9
        assert all(len(chunk["text"].split()) <= 6 for chunk in engine.chunks)
        assert len({chunk["chunk_id"] for chunk in engine.chunks}) == 9
        hits = engine.search("apple")
        assert len(hits) == len({hit["document_id"] for hit in hits}) == 5
        assert hits[0]["title"] == "second" and hits[1]["title"] == "best"
        assert all(a["score"] >= b["score"] for a, b in zip(hits, hits[1:]))
        for invalid in ("", " ", None, "apple " * 7):
            try:
                engine.search(invalid)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid query accepted")
        for invalid in ([], None, [str(root / "missing")], [str(root / "best.md")]):
            try:
                engine.sync(invalid)
            except (ValueError, OSError):
                pass
            else:
                raise AssertionError("invalid folder accepted")
            assert engine.search("apple") == hits
        model.broken = True
        try:
            engine.sync([str(root)])
        except RuntimeError:
            pass
        else:
            raise AssertionError("embedding error swallowed")
        model.broken = False
        assert engine.search("apple") == hits
        (root / "vacant").mkdir()
        assert engine.sync([str(root / "vacant")])["documents"] == 0
        assert engine.search("apple") == []
    print("PASS: recursive loading, deduplication, chunking, top-5, validation, atomic sync, empty sync")
    check_http(engine)


def check_http(engine):
    import json
    from http.client import HTTPConnection
    from http.server import HTTPServer
    from threading import Thread
    from app import Handler, ORIGIN

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        server.retrieval = engine
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            connection.request("GET", "/", headers={"Host": "127.0.0.1:8001"})
            response = connection.getresponse()
            assert response.status == 200 and b"/api/" in response.read()
            for origin, body, expected in (
                (ORIGIN, {"query": "apple"}, 200),
                (ORIGIN, {"query": ""}, 400),
                ("http://untrusted.example", {"query": "apple"}, 403),
            ):
                connection.request("POST", "/api/search", json.dumps(body),
                                   {"Host": "127.0.0.1:8001", "Origin": origin})
                response = connection.getresponse()
                result = json.loads(response.read())
                assert response.status == expected, result
                assert ("hits" if expected == 200 else "error") in result
        finally:
            connection.close()
            server.shutdown()
            thread.join()
    print("PASS: HTML serving, search API, invalid query, origin rejection")


if __name__ == "__main__":
    main()
