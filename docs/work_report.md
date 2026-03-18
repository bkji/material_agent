# Fragment 유사도 검색 에이전트 - 작업 결과 보고서

작성일: 2026-03-19 (최종 업데이트: Graph RAG 추가)

---

## 1. 구현 내용

### 1.1 Fragment 유사도 검색 에이전트 (`src/agent.py`)
- LangGraph StateGraph 기반 4단계 워크플로우
  - `parse_input`: 사용자 입력 SMILES 파싱 및 유효성 검증
  - `load_data`: QM8 데이터셋 로드 (21,787 molecules)
  - `search_similar`: 선택된 방법(들)로 fragment 유사도 검색 수행
  - `format_output`: 결과 포맷팅 (단일 방법 / 비교 모드 자동 전환)
- CLI 지원: `--methods`, `--top-k`, `--no-substruct-filter` 옵션
- 에러 핸들링 (유효하지 않은 SMILES 처리)

### 1.2 유사도 검색 엔진 (`src/similarity.py`) — 7가지 방법 지원

| 방법 | 설명 | 원리 |
|------|------|------|
| `morgan` | Morgan (ECFP4) FP + Tanimoto | 각 원자 주변 반경 2의 환경을 해시하여 2048bit 벡터 생성 |
| `maccs` | MACCS Keys (166bit) + Tanimoto | 사전 정의된 166개 구조 키(작용기, 고리 등)의 존재 여부를 비트로 표현 |
| `rdkit` | RDKit FP + Tanimoto | 분자 그래프 위의 경로(path)를 열거하여 2048bit 벡터 생성 |
| `atompair` | AtomPair FP + Tanimoto | 모든 원자 쌍의 (원자 종류, 거리) 조합을 인코딩 |
| `torsion` | Topological Torsion FP + Tanimoto | 연속 4개 원자 경로(torsion angle 위상)를 인코딩 |
| `mcs` | Maximum Common Substructure | 두 분자의 최대 공통 부분구조 원자수 / 큰 쪽 원자수 |
| `graph_rag` | Graph RAG | BRICS 분해 → Knowledge Graph 구축 → Jaccard(60%) + Tanimoto(40%) 결합 |

### 1.3 Graph RAG 모듈 (`src/graph_rag.py`)
- BRICS 분해로 분자를 합성적으로 의미 있는 fragment로 분해
- networkx 기반 Knowledge Graph 구축
  - 분자 노드: 21,744개, Fragment 노드: 15,701개, CONTAINS 엣지: 31,655개
- 그래프 탐색으로 관련 fragment 집합을 추론하여 Jaccard 유사도 계산
- Morgan Tanimoto와 가중 결합하여 최종 점수 산출

### 1.4 방법론 비교 문서 (`docs/similarity_search_methods.md`)
- 7가지 유사도 검색 방식 상세 비교 (원리, 장단점, 실측 성능)
- Graph RAG 상세 분석 (그래프 구조, 검색 전략, Fingerprint와의 비교)
- 재료 분야 최근 기술 동향
- 참고문헌 12편

---

## 2. 프로젝트 구조

```
material_agent/
├── CLAUDE.md                                # 프로젝트 설정
├── Instruction_fragement_similarity_search.md  # 작업지시서
├── requirements.txt                         # Python 의존성
├── data/
│   └── 0_qm8_260318/
│       └── qm8.csv                          # QM8 데이터셋 (21,787 molecules)
├── docs/
│   ├── similarity_search_methods.md         # 유사도 검색 방법론 비교 (참고문헌 포함)
│   └── work_report.md                       # 본 보고서
└── src/
    ├── __init__.py
    ├── agent.py                             # LangGraph 에이전트 (CLI)
    ├── similarity.py                        # 유사도 검색 엔진 (7가지 방법)
    └── graph_rag.py                         # Graph RAG 모듈 (Knowledge Graph)
```

---

## 3. 사용 방법

```bash
# 전체 7가지 방법 비교 (기본)
python src/agent.py "c1ccccc1" --top-k 5

# 특정 방법만 선택하여 비교
python src/agent.py "c1ccccc1" --methods morgan maccs mcs graph_rag --top-k 5

# Graph RAG만 단독 사용
python src/agent.py "c1ccccc1" --methods graph_rag --top-k 10

# 단일 fingerprint 방법
python src/agent.py "C=O" --methods morgan --top-k 10

# 부분구조 필터 없이 전체 분자 대상 검색
python src/agent.py "c1ccccc1" --no-substruct-filter --top-k 5
```

---

## 4. 테스트 결과

### 4.1 테스트 설명

**테스트 목적**: 동일한 fragment SMILES를 입력했을 때, 7가지 유사도 방법이 각각 어떤 분자를 높은 순위로 반환하는지, 유사도 점수 분포는 어떻게 다른지, 소요시간은 얼마인지를 비교한다.

**테스트 방법**:
1. QM8 데이터셋(21,787개 분자)에서 fragment를 부분구조로 포함하는 분자를 먼저 필터링 (Substructure Match)
2. 필터링된 후보 분자들에 대해 7가지 방법으로 각각 유사도를 계산
3. 유사도 높은 순으로 정렬하여 상위 3개(Top-3) 결과를 비교

**결과 테이블 읽는 법**:
- **행(row)**: 각 유사도 방법 (morgan, maccs, rdkit, atompair, torsion, mcs, graph_rag)
- **Top-N 유사도**: 해당 방법으로 계산한 유사도 순위에서 N번째 분자의 점수
  - Fingerprint/MCS: 1.0 = fragment와 완전 동일, 0.0 = 전혀 유사하지 않음
  - Graph RAG: Jaccard(60%) + Tanimoto(40%) 결합 점수
- **소요시간**: 후보 분자 전체에 대해 유사도를 계산하고 정렬하는 데 걸린 시간 (초)
  - Graph RAG의 소요시간에는 Knowledge Graph 구축 시간이 포함됨

**Graph RAG 상세 열**:
- **결합**: 최종 점수 = Jaccard × 0.6 + Tanimoto × 0.4
- **Jaccard**: 쿼리 관련 fragment 집합과 후보 분자 fragment 집합의 Jaccard 유사도
- **Tanimoto**: Morgan FP 기반 Tanimoto 유사도 (보조 점수)
- **공유Frag**: 후보 분자가 쿼리 관련 fragment 중 몇 개를 공유하는지

---

### 4.2 벤젠 fragment (`c1ccccc1`) — 방향족 고리

**테스트 의도**: 벤젠 고리(6각 방향족 고리)를 fragment로 입력하여, 벤젠을 포함하는 분자 중 구조적으로 가장 유사한 것을 찾는다.

- 후보 분자 수: **42개** (21,787개 중 벤젠 고리를 포함하는 분자)
- Knowledge Graph: 노드 37,445개 (분자 21,744 + fragment 15,701), 엣지 31,655개

#### 방법 간 비교 요약

| 방법 | Top-1 유사도 | Top-2 유사도 | Top-3 유사도 | 소요시간(초) |
|------|-------------|-------------|-------------|-------------|
| morgan | 1.0000 | 0.2727 | 0.2727 | 0.0003 |
| maccs | 1.0000 | 0.7500 | 0.7500 | 0.0001 |
| rdkit | 1.0000 | 0.3243 | 0.3158 | 0.0002 |
| atompair | 1.0000 | 0.4444 | 0.4211 | 0.0001 |
| torsion | 1.0000 | 0.2222 | 0.2222 | 0.0001 |
| mcs | 1.0000 | 0.8571 | 0.8571 | 0.0042 |
| graph_rag | 0.4136 | 0.1227 | 0.1227 | 18.00 |

**분석**:
- Top-1은 모든 방법에서 벤젠 자체를 선택 (동일 분자)
- **MCS**가 Top-2에서 가장 높은 점수(0.857) → 공통 부분구조 비율이 직관적
- **MACCS**도 높은 점수(0.75) → 166개 구조 키 중 벤젠 관련 키가 많이 겹침
- **Graph RAG**는 Jaccard 비중이 높아 점수가 상대적으로 낮지만, 공유 fragment 수 정보를 추가 제공
- **Morgan**은 치환기 변화에 민감하여 점수 갭이 큼 (1.0 → 0.27)
- 속도: Fingerprint 5종 ~0.0001초, MCS 0.004초, Graph RAG 18초 (그래프 구축 포함)

#### Graph RAG Top-3 상세

| 순위 | SMILES | 결합점수 | Jaccard | Tanimoto | 공유Fragment |
|------|--------|---------|---------|----------|-------------|
| 1 | `[H]c1c([H])c([H])c([H])c([H])c1[H]` (벤젠) | 0.4136 | 0.0227 | 1.0000 | 1 |
| 2 | 톨루엔 (메틸벤젠) | 0.1227 | 0.0227 | 0.2727 | 1 |
| 3 | 아닐린 (아미노벤젠) | 0.1227 | 0.0227 | 0.2727 | 1 |

→ 벤젠 관련 BRICS fragment를 1개 공유, Jaccard가 낮은 것은 관련 fragment 집합이 매우 크기 때문

---

### 4.3 카르보닐 fragment (`C=O`) — 작용기

**테스트 의도**: 카르보닐기(C=O)는 알데히드, 케톤, 카르복시산, 아미드 등 다양한 작용기의 핵심이다. 작은 fragment로 검색 시 각 방법의 반응을 비교한다.

- 후보 분자 수: **7,544개** (전체의 약 35%가 C=O를 포함)

#### 방법 간 비교 요약

| 방법 | Top-1 유사도 | Top-2 유사도 | Top-3 유사도 | 소요시간(초) |
|------|-------------|-------------|-------------|-------------|
| morgan | 1.0000 | 0.1429 | 0.1333 | 0.0248 |
| maccs | 1.0000 | 0.5000 | 0.5000 | 0.0233 |
| rdkit | 1.0000 | 0.3333 | 0.3333 | 0.0252 |
| atompair | 1.0000 | 0.0667 | 0.0667 | 0.0247 |
| torsion | **0.0000** | 0.0000 | 0.0000 | 0.0257 |
| mcs | 1.0000 | 0.6667 | 0.6667 | 0.0067 |
| graph_rag | 0.4001 | 0.0573 | 0.0536 | 19.28 |

**분석**:
- **Torsion이 전부 0.0** → C=O는 원자 2개뿐이라 torsion 패턴(4원자 필요)이 생성되지 않음. **작은 fragment에 부적합한 방법**
- **MCS**가 가장 직관적 → 포름알데히드(2원자) / 아세트알데히드(3원자): MCS = 2/3 = 0.667
- **Graph RAG** Top-3에서 공유 fragment 2개인 분자도 발견 (더 복잡한 분자가 여러 fragment를 공유)
- 후보가 7,544개로 많아 Fingerprint도 ~0.025초, Graph RAG는 ~19초

---

### 4.4 질소 fragment (`N`) — 최소 단위 원자

**테스트 의도**: 단일 질소 원자를 fragment로 입력하여 가장 작은 단위의 검색 동작을 확인한다.

- 후보 분자 수: **12,675개** (전체의 약 58%가 질소를 포함)

#### 주요 방법 비교 (morgan, maccs, mcs, graph_rag)

| 방법 | Top-1 유사도 | Top-2 유사도 | Top-3 유사도 | 소요시간(초) |
|------|-------------|-------------|-------------|-------------|
| morgan | 1.0000 | 0.0625 | 0.0588 | 0.0408 |
| maccs | 1.0000 | 0.3333 | 0.2500 | 0.0390 |
| mcs | 1.0000 | 0.5000 | 0.3333 | 0.0048 |
| graph_rag | 0.4001 | 0.0251 | 0.0237 | 20.48 |

**분석**:
- MCS: 암모니아(1원자/1원자=1.0), HCN(1원자/2원자=0.5), 아세토니트릴(1원자/3원자=0.33) → 매우 직관적
- Graph RAG: Top-2, 3에서 공유 fragment 2개인 분자 발견 → 단일 N보다 풍부한 관계 정보

---

### 4.5 에러 처리 테스트 (`INVALID_SMILES`)

**결과**: `오류: 유효하지 않은 SMILES입니다: INVALID_SMILES` — 프로그램 중단 없이 에러 메시지 정상 출력

---

### 4.6 테스트 종합 요약

| 테스트 | Fragment | 의미 | 후보 수 | 전체 방법 동작 | 특이사항 |
|--------|----------|------|---------|---------------|---------|
| 벤젠 | `c1ccccc1` | 방향족 고리 | 42 | 7/7 정상 | 모든 방법 Top-1 동일 |
| 카르보닐 | `C=O` | 작용기 (작은) | 7,544 | 6/7 정상 | torsion 0.0 (원자 부족, 정상 동작) |
| 질소 | `N` | 단일 원자 | 12,675 | 7/7 정상 | 대규모 후보에서도 성능 유지 |
| 에러 | `INVALID` | 잘못된 입력 | - | 에러 처리 | 중단 없이 메시지 출력 |

### 4.7 방법별 특성 종합

| 방법 | 점수 분포 | 작은 fragment | 속도 | 추가 정보 | 적합 사례 |
|------|----------|-------------|------|----------|----------|
| **morgan** | 갭이 큼 | 사용 가능 | 매우 빠름 | 없음 | 치환기까지 엄밀 구분 |
| **maccs** | 비교적 높음 | 사용 가능 | 매우 빠름 | 없음 | 작용기 수준 유사도 |
| **rdkit** | 중간 | 사용 가능 | 매우 빠름 | 없음 | 범용적 유사도 |
| **atompair** | 갭이 큼 | 사용 가능 | 매우 빠름 | 없음 | 원자 거리 기반 비교 |
| **torsion** | 큰 분자만 | **4원자 미만 0.0** | 매우 빠름 | 없음 | 골격 형태 비교 |
| **mcs** | 가장 직관적 | 우수 | 느림 | 없음 | 해석 가능한 유사도 |
| **graph_rag** | Jaccard 의존 | 사용 가능 | 가장 느림 | 공유Frag수, Jaccard/Tanimoto 분리 | 관계 추론, LLM 연동 |

---

## 5. 기술 스택

| 항목 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| 화학정보학 | RDKit (Morgan, MACCS, RDKit FP, AtomPair, Torsion, MCS, BRICS) |
| 그래프 | networkx (Knowledge Graph 구축) |
| 에이전트 프레임워크 | LangGraph (StateGraph) |
| 데이터 처리 | pandas, numpy |
| 데이터셋 | QM8 (21,787 molecules) |

---

## 6. 향후 확장 방향

| 단계 | 방식 | 규모 | 방법 |
|------|------|------|------|
| **현재** (Phase 1) | CSV + RDKit + networkx + LangGraph | ~22K molecules | 7가지 방법 비교 |
| **Phase 2** | PostgreSQL + RDKit cartridge 또는 pgvector | ~1M molecules | FP 사전 계산 + 인덱싱 |
| **Phase 3** | Neo4j + 벡터 DB + LLM | 10M+ molecules | Graph RAG + 자연어 질의 |
