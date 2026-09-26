"""로컬 Markdown → 토큰 청킹 → 임베딩 → 문서별 top-5."""
import os
from datetime import datetime
from pathlib import Path

import numpy as np
from charset_normalizer import from_bytes


class Retrieval:
    def __init__(self, model):
        self.model = model
        self.chunks = []
        self.vectors = None

    def sync(self, folders):
        if not isinstance(folders, list) or not folders:
            raise ValueError("폴더를 하나 이상 등록하세요.")
        paths = set()

        def fail(error):
            raise error

        print("[retrieval.py Retrieval.sync] finding files...")

        for folder in folders:
            if not isinstance(folder, str) or not folder.strip():
                raise ValueError("폴더 경로가 올바르지 않습니다.")
            root = Path(folder).resolve(strict=True)
            if not root.is_dir():
                raise ValueError(f"폴더가 아닙니다: {root}")
            for directory, _, names in os.walk(root):#, onerror=fail):
                for name in names:
                    path = Path(directory) / name
                    if path.suffix.lower() == ".md" and not path.is_symlink():
                        paths.add(path.resolve())

        print("[retrieval.py Retrieval.sync] start tokenizing")

        tokenizer = self.model.tokenizer
        size = self.model.max_seq_length - tokenizer.num_special_tokens_to_add(pair=False)
        overlap = min(20, size // 4)
        chunks, total_bytes, empty = [], 0, 0
        for path in sorted(paths):
            try:
                raw = path.read_bytes()
            except Exception as e:
                print(f"[retrieval.py Retrieval.sync] 파일 읽기 에러 - {str(path)}")
                print(e)
                continue
            total_bytes += len(raw)
            try:
                content = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                match = from_bytes(raw).best()
                if match is None:
                    raise ValueError(f"인코딩을 판별할 수 없습니다: {path}")
                content = str(match)
            tokens = tokenizer.encode(content, add_special_tokens=False)
            if not content.strip() or not tokens:
                empty += 1
                continue
            for start in range(0, len(tokens), size - overlap):
                chunks.append({
                    "document_id": str(path), "chunk_id": f"{path}#{start}",
                    "title": path.stem, "source": "local",
                    "text": tokenizer.decode(tokens[start:start + size], skip_special_tokens=True),
                })
                if start + size >= len(tokens):
                    break

        # ponytail: 전체 벡터를 메모리에 보관. 큰 문서 집합이 필요해지면 배치 저장으로 전환.
        vectors = self.model.encode(
            [chunk["text"] for chunk in chunks], normalize_embeddings=True,
            convert_to_numpy=True, show_progress_bar=False,
        ) if chunks else None
        # 읽기/임베딩 실패 시 이전 인덱스를 유지한다.
        self.chunks, self.vectors = chunks, vectors
        return {"documents": len(paths), "chunks": len(chunks), "bytes": total_bytes,
                "empty": empty, "synced_at": datetime.now().astimezone().isoformat(timespec="seconds")}

    def search(self, query):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("검색어를 입력하세요.")
        tokenizer = self.model.tokenizer
        if len(tokenizer.encode(query)) > self.model.max_seq_length:
            raise ValueError("검색어가 모델의 입력 길이를 초과합니다. 더 짧게 입력하세요.")
        if self.vectors is None:
            return []
        vector = self.model.encode([query], normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False)[0]
        scores = self.vectors @ vector
        hits, seen = [], set()
        for index in np.argsort(-scores, kind="stable"):
            chunk = self.chunks[index]
            if chunk["document_id"] in seen:
                continue
            seen.add(chunk["document_id"])
            hits.append({**chunk, "score": float(scores[index])})
            if len(hits) == 5:
                break
        return hits
