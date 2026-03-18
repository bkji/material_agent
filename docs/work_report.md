# Fragment 유사도 검색 에이전트 - 작업 결과 보고서

작성일: 2026-03-19

---

## 1. 구현 내용

### 1.1 Fragment 유사도 검색 에이전트 (`src/agent.py`)
- LangGraph StateGraph 기반 4단계 워크플로우
  - `parse_input`: 사용자 입력 SMILES 파싱 및 유효성 검증
  - `load_data`: QM8 데이터셋 로드 (21,787 molecules)
  - `search_similar`: fragment 유사도 검색 수행
  - `format_output`: 결과 포맷팅 및 출력
- CLI 지원 (커맨드라인 인자 / 대화형 모드)
- 에러 핸들링 (유효하지 않은 SMILES 처리)

### 1.2 유사도 검색 엔진 (`src/similarity.py`)
- **Morgan Fingerprint** (ECFP, radius=2, 2048bits) + **Tanimoto Coefficient**
- 2단계 검색 전략:
  1. Substructure 필터링: fragment를 부분구조로 포함하는 분자만 추출
  2. Tanimoto 유사도 순위: fingerprint 기반 유사도 계산 후 정렬
- 유사도 점수 기준: 0.0(완전 다름) ~ 1.0(동일)

### 1.3 방법론 비교 문서 (`docs/similarity_search_methods.md`)
- 5가지 유사도 검색 방식 비교: Fingerprint, Substructure, GNN, Graph RAG, MCS
- Graph RAG 장/단점 상세 분석
- 재료 분야 최근 기술 동향 (Foundation Models, LLM+Chemistry, Inverse Design, Vector DB)
- 향후 확장 전략 (CSV → PostgreSQL → Vector DB/Graph RAG)

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
│   ├── similarity_search_methods.md         # 유사도 검색 방법론 비교
│   └── work_report.md                       # 본 보고서
└── src/
    ├── __init__.py
    ├── agent.py                             # LangGraph 에이전트
    └── similarity.py                        # 유사도 검색 엔진
```

---

## 3. 사용 방법

```bash
# 커맨드라인 실행 (fragment SMILES, top_k)
python src/agent.py "c1ccccc1" 10

# 대화형 모드
python src/agent.py
```

---

## 4. 테스트 결과

### 4.1 벤젠 fragment (`c1ccccc1`)

```
=== Fragment 유사도 검색 결과 ===
검색 Fragment: c1ccccc1
후보 분자 수: 42
상위 5개 결과:
------------------------------------------------------------
순위    SMILES                                         유사도
------------------------------------------------------------
1     [H]c1c([H])c([H])c([H])c([H])c1[H]          1.0000
2     [H]c1c([H])c([H])c(C([H])([H])[H])...       0.2727
3     [H]c1c([H])c([H])c(N([H])[H])c([H]...       0.2727
4     [H]Oc1c([H])c([H])c([H])c([H])c1[H]         0.2727
5     [H]c1c([H])c([H])c(F)c([H])c1[H]            0.2727
------------------------------------------------------------
```

### 4.2 카르보닐 fragment (`C=O`)

```
=== Fragment 유사도 검색 결과 ===
검색 Fragment: C=O
후보 분자 수: 7544
상위 5개 결과:
------------------------------------------------------------
순위    SMILES                                         유사도
------------------------------------------------------------
1     [H]C([H])=O                                 1.0000
2     [H]C(=O)C([H])=O                            0.1429
3     [H]C(=O)C([H])(C([H])=O)N1C([H])([...       0.1333
4     [H]C(=O)C([H])([H])[H]                      0.1250
5     [H]C(=O)N([H])[H]                           0.1250
------------------------------------------------------------
```

### 4.3 질소 fragment (`N`)

```
=== Fragment 유사도 검색 결과 ===
검색 Fragment: N
후보 분자 수: 12675
상위 5개 결과:
------------------------------------------------------------
순위    SMILES                                         유사도
------------------------------------------------------------
1     [H]N([H])[H]                                1.0000
2     [H]C([H])([H])C1([H])C([H])([H])C(...       0.0625
3     [H]OC1([H])C2([H])N([H])C1([H])C21...       0.0588
4     [H]C([H])([H])C1([H])N(C2([H])C([H...       0.0588
5     [H]OC1([H])C([H])([H])C(=O)N([H])C...       0.0556
------------------------------------------------------------
```

### 4.4 에러 처리 테스트 (`INVALID_SMILES`)

```
오류: 유효하지 않은 SMILES입니다: INVALID_SMILES
```

### 4.5 테스트 결과 요약

| 테스트 | Fragment | 후보 수 | Top-1 유사도 | 결과 |
|--------|----------|---------|-------------|------|
| 벤젠 | `c1ccccc1` | 42 | 1.0000 | 정상 |
| 카르보닐 | `C=O` | 7,544 | 1.0000 | 정상 |
| 질소 | `N` | 12,675 | 1.0000 | 정상 |
| 에러처리 | `INVALID_SMILES` | - | - | 에러 메시지 정상 출력 |

---

## 5. 기술 스택

| 항목 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| 화학정보학 | RDKit (Morgan Fingerprint, Tanimoto Similarity) |
| 에이전트 프레임워크 | LangGraph (StateGraph) |
| 데이터 처리 | pandas, numpy |
| 데이터셋 | QM8 (21,787 molecules) |

---

## 6. 향후 확장 방향

| 단계 | 방식 | 규모 |
|------|------|------|
| **현재** (Phase 1) | CSV + RDKit fingerprint + LangGraph agent | ~22K molecules |
| **Phase 2** | PostgreSQL + RDKit cartridge 또는 pgvector | ~1M molecules |
| **Phase 3** | Vector DB (Milvus/pgvector) + Graph RAG | 10M+ molecules |
