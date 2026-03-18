# 분자 유사도 검색 방식 비교

## 1. 주요 유사도 검색 방식

### 1.1 Fingerprint 기반 (Tanimoto Similarity)
- **방식**: 분자를 비트 벡터(fingerprint)로 변환 후 Tanimoto 계수로 유사도 측정
- **종류**: Morgan(ECFP), MACCS keys, Topological, AtomPair 등
- **장점**: 빠른 연산 속도, 대규모 DB 검색에 적합, 사전 계산/인덱싱 가능
- **단점**: 3D 구조 정보 손실, fingerprint 종류에 따라 결과 편차

### 1.2 Substructure Matching (SMARTS)
- **방식**: 쿼리 fragment를 SMARTS 패턴으로 변환하여 부분구조 포함 여부 판별
- **장점**: 정확한 구조적 포함 관계 확인, 화학적 직관과 일치
- **단점**: 유사도 순위 부여 불가(있다/없다만 판별), 대규모 DB에서 느림

### 1.3 Graph Neural Network (GNN) 기반
- **방식**: 분자 그래프를 GNN으로 임베딩하여 벡터 유사도 계산
- **종류**: GCN, GAT, MPNN, SchNet 등
- **장점**: 분자의 구조적 특성을 심층 학습, 높은 표현력
- **단점**: 학습 데이터 필요, 해석 어려움, 추론 비용

### 1.4 Shape/Pharmacophore 기반
- **방식**: 3D 형태 또는 pharmacophore 특성 비교
- **장점**: 물리적 상호작용 관점에서 유사도 평가
- **단점**: 3D conformer 생성 필요, 연산 비용 높음

---

## 2. Graph RAG (Retrieval-Augmented Generation) 분석

### 개념
Graph RAG는 기존 RAG에 knowledge graph를 결합한 방식으로, 분자 구조를 그래프 DB(예: Neo4j)에 저장하고 그래프 쿼리를 통해 검색한 후 LLM이 결과를 해석/생성한다.

### 장점
| 항목 | 설명 |
|------|------|
| **관계 표현** | 분자-fragment-속성 간 다중 관계를 자연스럽게 모델링 |
| **추론 가능** | 그래프 경로 탐색으로 간접적 유사 관계 발견 (예: 같은 fragment를 공유하는 분자군) |
| **LLM 연동** | 검색 결과를 LLM 컨텍스트에 주입하여 자연어 기반 질의/해석 가능 |
| **확장성** | 새 속성/관계 추가가 스키마 변경 없이 가능 |

### 단점
| 항목 | 설명 |
|------|------|
| **구축 비용** | Knowledge graph 설계 및 데이터 적재에 초기 공수가 큼 |
| **정량적 유사도** | 그래프 기반 검색은 연속적 유사도 점수 산출에 약함 (fingerprint 대비) |
| **인프라** | Neo4j 등 그래프 DB 운영 필요, 기존 RDBMS와 이중 관리 |
| **LLM 의존** | 토큰 비용, 환각(hallucination) 위험 |

### 권장 시나리오
- 단순 유사도 순위: **Fingerprint + Tanimoto** (본 프로젝트의 현재 구현)
- 구조적 관계 탐색 + 자연어 질의: **Graph RAG**
- 대규모(1000만건) 스케일링: Fingerprint 사전 계산 + PostgreSQL RDKit cartridge 또는 벡터 DB

---

## 3. 재료/소재 분야 최근 기술 경향

### 3.1 Foundation Model for Materials
- **MatterGen** (Microsoft, 2024): 확산 모델 기반 신소재 생성
- **GNoME** (Google DeepMind, 2023): GNN으로 220만 개 안정 결정 구조 예측
- 대규모 사전학습 모델이 소재 발견 파이프라인을 변화시키는 중

### 3.2 LLM + Chemistry
- **ChemCrow**, **Coscientist**: LLM이 도구(RDKit, 실험장비 API)를 호출하여 자율적 화학 실험 설계
- LangChain/LangGraph 기반 chemistry agent가 실험실 자동화로 확장

### 3.3 Inverse Design
- 목표 물성 → 분자/소재 구조 역설계
- VAE, diffusion model, reinforcement learning 활용
- fragment 기반 조합 최적화(fragment-based drug/material design)가 활발

### 3.4 Vector DB + Molecular Search
- 분자 fingerprint/embedding을 벡터 DB(Milvus, Pinecone, pgvector)에 저장
- 수천만 건 수준에서 ms 단위 유사도 검색 가능
- 본 프로젝트의 향후 DB 마이그레이션 시 권장 방향

---

## 4. 본 프로젝트 적용 전략

| 단계 | 방식 | 규모 |
|------|------|------|
| **현재** (Phase 1) | CSV + RDKit fingerprint + LangGraph agent | ~22K molecules |
| **Phase 2** | PostgreSQL + RDKit cartridge 또는 pgvector | ~1M molecules |
| **Phase 3** | 벡터 DB (Milvus/pgvector) + Graph RAG | 10M+ molecules |

### 유사도 점수 기준 (본 프로젝트)
- **Tanimoto coefficient** (Morgan FP, radius=2, 2048 bits)
- 범위: 0.0 (완전 다름) ~ 1.0 (동일)
- 일반적 기준: ≥0.85 높은 유사도, ≥0.7 중간, <0.5 낮음
