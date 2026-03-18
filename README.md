# Fragment Similarity Search Agent

분자 fragment의 SMILES를 입력하면, QM8 데이터셋에서 해당 fragment를 포함하거나 유사한 전체 분자 SMILES와 유사도 점수를 반환하는 LangGraph 기반 에이전트입니다.

## 아키텍처

```
[사용자 입력: Fragment SMILES]
        ↓
  ┌─────────────┐
  │ parse_input  │  SMILES 유효성 검증 + canonical화
  └──────┬──────┘
         ↓
  ┌──────────────────┐
  │ search_molecules │  1차: Substructure Match → 2차: Tanimoto Ranking
  └──────┬───────────┘
         ↓
  ┌───────────────┐
  │ format_output │  결과 포맷팅
  └───────────────┘
         ↓
  [출력: SMILES + Score 리스트]
```

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

### 대화형 모드
```bash
python main.py
```

### 단일 검색
```bash
# 벤젠 링 fragment로 검색
python main.py "c1ccccc1"

# 상위 20개, 최소 유사도 0.3 이상
python main.py "c1ccccc1" --top-k 20 --min-score 0.3
```

### 인덱스 빌드
```bash
python main.py --build-index
```

## 프로젝트 구조

```
material_agent/
├── main.py                 # 메인 실행 파일
├── requirements.txt        # 의존성
├── README.md
├── data/
│   └── 0_qm8_260318/
│       └── qm8.csv        # QM8 데이터셋 (~21,787 분자)
└── src/
    ├── __init__.py
    ├── preprocessing.py    # 데이터 전처리 (SMILES 로드, fragment 분해)
    ├── indexing.py         # 인덱싱 (Morgan FP, 역인덱스)
    ├── search_engine.py    # 유사도 검색 엔진
    ├── agent.py            # LangGraph Agent
    └── backend.py          # 백엔드 추상화 (CSV/DB)
```

## 유사도 점수 기준

- **Tanimoto coefficient** (0~1): Morgan Fingerprint 기반
- 0.7 이상: 높은 유사도
- 0.5~0.7: 중간 유사도
- 0.5 미만: 낮은 유사도

## 향후 확장

- PostgreSQL + RDKit cartridge로 DB 전환 (1,000만건 대응)
- `backend.py`의 `PostgreSQLBackend` 클래스 참조
