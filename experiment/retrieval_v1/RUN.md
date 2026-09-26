# 실행 방법

기존 프로젝트 파일을 바꾸지 않는 독립 실험입니다. PowerShell에서 아래 순서로 실행합니다.

```powershell
cd C:\HUR\Document\hurag\experiment\retrieval_v1
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B app.py
```

브라우저에서 http://127.0.0.1:8001 을 열고 **폴더 추가 → 전체 동기화 → 검색**을 실행합니다. Windows의 폴더 선택 창이 열립니다. 종료는 터미널에서 Ctrl+C입니다.

- Python 3.12 이상, tkinter가 포함된 Python 배포판을 사용하세요.
- 첫 동기화는 인터넷 연결이 필요합니다. 모델은 이 폴더의 `.cache`에 다운로드하며 CPU에서 실행합니다. 문서 본문은 외부 API에 보내지 않습니다.
- 폴더 목록만 브라우저 localStorage에 남습니다. 문서·청크·벡터는 메모리에만 있으며 서버 재시작 후 다시 동기화해야 합니다.
- 전체 동기화는 등록된 폴더로 인덱스를 교체합니다. 읽기나 임베딩이 실패하면 이전 인덱스를 보존합니다. 빈 폴더로 성공적으로 동기화하면 인덱스도 비워집니다.
- 하위 폴더의 `.md`/`.MD`를 읽으며 중복 경로는 한 번만 처리합니다. 심볼릭 링크 파일과 하위 디렉터리는 따라가지 않습니다. UTF-8을 먼저 시도하고 다른 인코딩은 자동 감지합니다.
- 모델의 입력 토큰 길이에 맞춰 중첩 청킹합니다. 검색 결과의 청크는 토크나이저로 복원한 텍스트여서 원본 공백과 서식은 다를 수 있습니다.
- 정규화 벡터의 내적으로 코사인 유사도를 계산합니다. 문서별 최고 점수 청크를 선택하고 상위 5개를 보여줍니다. 점수는 정답 확률이 아닙니다.
- 현재 전체/로컬 검색 범위는 같은 로컬 인덱스를 사용합니다. 날짜 필터, LLM 답변, DB, 외부 소스는 구현하지 않았습니다.
- 동기화 중에는 다른 요청이 대기합니다. 이 실험은 소규모 로컬 문서 집합을 위한 것입니다.

## 자동 검증

```powershell
.\.venv\Scripts\python.exe -B test_retrieval.py
```

자동 검증은 가짜 임베딩으로 청킹, 재귀 읽기, 중복 제거, 순위, top-5, 입력 검증, 실패 시 기존 인덱스 보존을 확인합니다. 모델 다운로드 없이 실행되며 **실제 의미 검색 품질은 검증하지 않습니다.** 기존 프로젝트 가상환경에서도 실행할 수 있습니다.

실제 품질은 서로 다른 주제의 Markdown 문서를 등록한 뒤, 문서의 문장을 그대로 복사하지 않은 한국어 질문으로 확인하세요. 관련 문서가 상위에 나오는지와 화면에 표시되는 청크를 확인하면 됩니다. 서버를 재시작하여 인덱스가 사라지는 것도 확인할 수 있습니다.

## 모델/API 참고

- [다국어 MiniLM 모델](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- [SentenceTransformer API](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)
