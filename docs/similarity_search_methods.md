# Fragment 유사도 검색 방법론 비교

## 1. 구현된 유사도 검색 방식 (7가지)

### 1.1 Morgan (ECFP4) Fingerprint + Tanimoto

**방법**: 각 원자를 중심으로 반경(radius) 내 원자 환경을 해시하여 2048비트 벡터로 변환하고, Tanimoto 계수로 유사도 측정

- **본 프로젝트 설정**: radius=2 (ECFP4와 동일), nBits=2048
- **장점**:
  - 계산 속도가 매우 빠름 (비트 연산, 0.0003초/42건)
  - 원자 주변 환경을 세밀하게 인코딩하여 치환기 차이에 민감
  - 대규모 데이터셋에 적합 (1000만건 이상 처리 가능)
  - 화학 정보학에서 가장 널리 사용되는 표준 방법
- **단점**:
  - 해시 충돌에 의한 정보 손실 가능
  - 치환기가 달라지면 점수가 급격히 하락 (벤젠→톨루엔: 0.27)
  - 3D 구조 정보 반영 불가
- **참고문헌**: Rogers & Hahn, "Extended-Connectivity Fingerprints", J. Chem. Inf. Model., 2010, 50(5), 742-754

### 1.2 MACCS Keys (166bit) + Tanimoto

**방법**: MDL에서 정의한 166개의 구조 키(작용기, 고리 시스템 등)의 존재 여부를 비트로 표현

- **장점**:
  - 화학적으로 해석 가능한 키 (각 비트가 특정 작용기/패턴에 대응)
  - 매우 빠른 계산 속도
  - 작용기 수준의 유사도에서 높은 점수 부여 (벤젠→톨루엔: 0.75)
- **단점**:
  - 166비트로 제한되어 표현력 한계
  - 새로운 구조 패턴을 반영할 수 없음 (사전 정의 키만 사용)
- **참고문헌**: Durant et al., "Reoptimization of MDL Keys for Use in Drug Discovery", J. Chem. Inf. Comput. Sci., 2002, 42(6), 1273-1280

### 1.3 RDKit Fingerprint + Tanimoto

**방법**: 분자 그래프 위의 경로(linear path)를 열거하여 2048비트 벡터 생성. RDKit 라이브러리의 기본 fingerprint

- **장점**:
  - 경로 기반으로 분자 연결성을 잘 포착
  - Morgan과 MACCS의 중간 수준 점수 분포
  - RDKit에서 기본 제공, 구현 용이
- **단점**:
  - 고리 구조의 특성이 경로로만 표현됨
  - 원자 환경 정보는 Morgan보다 제한적
- **참고문헌**: RDKit Documentation, "RDKit Fingerprints" (https://www.rdkit.org/docs/GettingStartedInPython.html)

### 1.4 AtomPair Fingerprint + Tanimoto

**방법**: 분자 내 모든 원자 쌍의 (원자 종류, 최단 거리) 조합을 인코딩

- **장점**:
  - 원자 간 거리 정보를 반영
  - 골격 구조의 유사성에 민감
- **단점**:
  - 큰 분자에서 원자 쌍이 매우 많아질 수 있음
  - 작은 fragment에서는 쌍이 적어 변별력 저하
- **참고문헌**: Carhart et al., "Atom Pairs as Molecular Features in Structure-Activity Studies", J. Chem. Inf. Comput. Sci., 1985, 25(2), 64-73

### 1.5 Topological Torsion Fingerprint + Tanimoto

**방법**: 연속 4개 원자 경로(torsion angle의 위상적 표현)를 인코딩

- **장점**:
  - 분자 골격의 3D 유사성을 간접적으로 반영
  - 큰 분자의 형태 비교에 유용
- **단점**:
  - **원자 4개 미만 fragment에서는 패턴이 생성되지 않아 유사도 0.0** (C=O 테스트에서 확인)
  - 작은 fragment 검색에 부적합
- **참고문헌**: Nilakantan et al., "Topological Torsion: A New Molecular Descriptor for SAR Applications", J. Chem. Inf. Comput. Sci., 1987, 27(2), 82-85

### 1.6 Maximum Common Substructure (MCS) 기반 유사도

**방법**: 두 분자의 최대 공통 부분구조(MCS)를 찾아, MCS 원자수 / max(두 분자 원자수)로 유사도 산출

- **본 프로젝트 설정**: timeout=1초, ringMatchesRingOnly=True, 후보 200개 제한
- **장점**:
  - 화학적으로 가장 직관적인 유사도 (공통 구조의 비율)
  - 작은 fragment에서도 의미 있는 점수 (벤젠→톨루엔: 0.857)
  - Fragment 매칭에 매우 적합
- **단점**:
  - NP-hard 문제로 계산 비용 높음 (0.004초/42건, fingerprint 대비 ~40배 느림)
  - 대규모 데이터셋에 직접 적용 어려움 (사전 필터링 필수)
- **참고문헌**: Raymond & Willett, "Maximum Common Subgraph Isomorphism Algorithms for the Matching of Chemical Structures", J. Comput.-Aided Mol. Des., 2002, 16, 521-533

### 1.7 Graph RAG (Knowledge Graph + BRICS Fragment + Jaccard/Tanimoto)

**방법**: 분자를 BRICS 분해하여 fragment를 추출하고, 분자-fragment 관계를 Knowledge Graph(networkx)로 구축. 그래프 탐색으로 관련 fragment를 찾은 뒤, Jaccard 유사도(60%)와 Morgan Tanimoto(40%)를 결합하여 최종 점수 산출

- **그래프 구조**:
  - Molecule 노드: 21,744개 (QM8 데이터셋의 유효 분자)
  - Fragment 노드: 15,701개 (BRICS 분해로 추출된 고유 fragment)
  - CONTAINS 엣지: 31,655개 (분자→fragment 관계)
- **BRICS 분해**: Breaking of Retrosynthetically Interesting Chemical Substructures — 합성적으로 의미 있는 결합을 끊어 fragment로 분해
- **검색 전략**:
  1. Substructure match로 쿼리 fragment를 포함하는 분자 필터링
  2. 그래프 탐색: 매칭된 fragment 노드의 이웃 분자 → 그 분자들의 다른 fragment 수집 (관련 fragment 집합)
  3. 각 후보 분자의 fragment 집합과 관련 fragment 집합의 Jaccard 유사도 계산
  4. Morgan Tanimoto와 가중 결합 (Jaccard 60% + Tanimoto 40%)
- **장점**:
  - Fragment 간 관계를 명시적으로 모델링 (공유 fragment 수 제공)
  - "같은 fragment를 공유하는 분자군" 탐색 가능
  - 향후 LLM과 결합하여 자연어 질의 가능 (RAG 파이프라인 확장)
  - 새 데이터 추가 시 그래프 확장만으로 대응
  - 구조-성질 관계를 그래프에 추가 저장 가능
- **단점**:
  - 그래프 구축에 ~18초 소요 (사전 구축 시 검색만은 빠름)
  - Jaccard 점수가 fragment 집합 크기에 의존하여, 범용 fragment일수록 낮은 점수
  - 외부 그래프 DB(Neo4j) 없이 메모리 기반이므로 대규모 확장 시 별도 인프라 필요
- **참고문헌**:
  - Degen et al., "On the Art of Compiling and Using 'Drug-Like' Chemical Fragment Spaces", ChemMedChem, 2008, 3(10), 1503-1507 (BRICS)
  - Lewis, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS, 2020 (RAG)
  - Microsoft Research, "From Local to Global: A Graph RAG Approach to Query-Focused Summarization", 2024 (Graph RAG)

---

## 2. 방법 간 비교

### 2.1 실측 성능 비교 (벤젠 fragment, 42개 후보)

| 방법 | Top-1 유사도 | Top-2 유사도 | Top-3 유사도 | 소요시간(초) | 특징 |
|------|-------------|-------------|-------------|-------------|------|
| morgan | 1.0000 | 0.2727 | 0.2727 | 0.0003 | 치환기에 민감, 점수 갭 큼 |
| maccs | 1.0000 | 0.7500 | 0.7500 | 0.0001 | 작용기 수준에서 높은 점수 |
| rdkit | 1.0000 | 0.3243 | 0.3158 | 0.0002 | Morgan과 MACCS의 중간 |
| atompair | 1.0000 | 0.4444 | 0.4211 | 0.0001 | 원자 거리 반영 |
| torsion | 1.0000 | 0.2222 | 0.2222 | 0.0001 | 4원자 이상 필요 |
| mcs | 1.0000 | 0.8571 | 0.8571 | 0.0042 | 가장 직관적 |
| graph_rag | 0.4136 | 0.1227 | 0.1227 | 18.00 | 관계 추론, 확장성 |

### 2.2 방법 유형별 비교

| 항목 | Fingerprint 5종 | MCS | Graph RAG | GNN (미구현) |
|------|-----------------|-----|-----------|-------------|
| **검색 속도** | 매우 빠름 | 느림 | 그래프 구축 후 빠름 | 추론 비용 |
| **확장성 (1000만건)** | 우수 | 사전 필터링 필수 | 그래프 DB 필요 | GPU 필요 |
| **Fragment 매칭** | 좋음 | 매우 좋음 | 매우 좋음 | 좋음 |
| **해석 가능성** | 보통 | 높음 | 높음 (공유 fragment) | 낮음 |
| **구축 비용** | 낮음 | 낮음 | 중간 | 높음 (학습 필요) |
| **자연어 질의** | 불가 | 불가 | 가능 (LLM 연동) | 불가 |
| **관계 추론** | 불가 | 불가 | 가능 | 제한적 |

### 2.3 사용 시나리오별 권장 방법

| 시나리오 | 권장 방법 | 이유 |
|---------|----------|------|
| 대규모 스크리닝 (속도 중요) | morgan, maccs | 0.0001초 단위 검색 |
| 작용기 수준 유사도 | maccs | 화학적 키 기반 |
| 엄밀한 구조 비교 | morgan | 치환기까지 세밀 구분 |
| 직관적 해석이 필요할 때 | mcs | 공통 구조 비율 |
| 관계 탐색 + 자연어 질의 | graph_rag | Knowledge Graph + LLM |
| 작은 fragment (2-3원자) | maccs, mcs, graph_rag | torsion 제외 |
| 큰 fragment (>4원자) | morgan, torsion | 골격 비교에 유리 |

---

## 3. Graph RAG 상세 분석

### 3.1 개념

Graph RAG는 기존 RAG(Retrieval-Augmented Generation)에 Knowledge Graph를 결합한 방식이다. 본 프로젝트에서는:

1. **Knowledge Graph 구축**: 분자를 BRICS 분해하여 fragment를 추출하고, 분자-fragment 관계를 그래프로 저장
2. **그래프 기반 검색**: 쿼리 fragment와 관련된 분자/fragment를 그래프 탐색으로 검색
3. **유사도 계산**: 그래프 관계(Jaccard)와 구조적 유사도(Tanimoto)를 결합

### 3.2 본 프로젝트 구현 내용

```
Knowledge Graph 구조:
  [Molecule_1] --CONTAINS--> [Fragment_A]
  [Molecule_1] --CONTAINS--> [Fragment_B]
  [Molecule_2] --CONTAINS--> [Fragment_A]  ← 같은 fragment 공유
  [Molecule_2] --CONTAINS--> [Fragment_C]

검색 과정:
  Query: Fragment_A
    → Molecule_1, Molecule_2 (substructure match)
    → 관련 fragment: {A, B, C} (이웃 탐색)
    → Jaccard(후보의 fragment집합, 관련 fragment집합) + Tanimoto
```

### 3.3 Graph RAG vs Fingerprint 비교 (실측)

| 항목 | Fingerprint (morgan) | Graph RAG |
|------|---------------------|-----------|
| 벤젠 Top-1 점수 | 1.0000 | 0.4136 |
| C=O Top-1 점수 | 1.0000 | 0.4001 |
| 검색 시간 (42건) | 0.0003초 | 18초 (그래프 구축 포함) |
| 제공 정보 | 유사도 점수만 | 유사도 + 공유 fragment 수 + Jaccard/Tanimoto 분리 |
| 확장 가능성 | 벡터 DB | 그래프 DB + LLM |

### 3.4 향후 확장 방향

- **Neo4j 마이그레이션**: 현재 networkx(메모리)에서 Neo4j(디스크)로 전환하여 1000만건 대응
- **LLM 연동**: 그래프 검색 결과를 LLM 컨텍스트에 주입하여 자연어 질의/해석
- **속성 그래프 확장**: 분자 노드에 물성(에너지, 진동자 강도 등) 추가하여 구조-성질 관계 탐색

---

## 4. 재료 분야 최근 기술 경향

### 4.1 AI/ML 기반 재료 탐색
- **Foundation Models for Chemistry**: 대규모 화학 데이터로 사전학습된 모델 (ChemBERTa, MolBERT, Uni-Mol)이 분자 표현 학습에 활용
- **Inverse Design**: 목표 물성에서 역으로 분자 구조를 생성하는 생성 모델 (VAE, GAN, Diffusion) 활발
- **GNoME** (Google DeepMind, 2023): GNN으로 220만 개 안정 결정 구조 예측
- **MatterGen** (Microsoft, 2024): 확산 모델 기반 신소재 생성

### 4.2 Graph 기반 접근
- **Molecular Graph Transformer**: 분자 그래프에 Transformer 적용하여 성질 예측
- **Knowledge Graph for Materials**: MatKG, Materials Project 등 재료 지식 그래프 구축 및 활용 증가
- **Graph RAG**: Microsoft Research (2024)가 제안한 그래프 기반 RAG 아키텍처가 화학/재료 분야에도 적용 시작

### 4.3 자율 실험 및 에이전트
- **LLM Agent for Chemistry**: ChemCrow, Coscientist 등 LLM 기반 에이전트가 실험 계획, 문헌 검색, 합성 경로 제안
- **LangGraph 활용**: LangChain/LangGraph 기반 chemistry agent가 실험실 자동화로 확장
- **Self-Driving Labs**: 자동화된 실험-분석-최적화 루프

### 4.4 Fragment 기반 설계
- **Fragment-Based Drug/Material Design**: Fragment를 조합하여 원하는 성질의 분자 설계
- **BRICS 분해**: 합성적으로 의미 있는 fragment로 분해하여 조합 라이브러리 구축
- **Combinatorial Fragment Libraries**: 대규모 Fragment 라이브러리 구축 및 가상 스크리닝

### 4.5 벡터 DB + 분자 검색
- 분자 fingerprint/embedding을 벡터 DB(Milvus, Pinecone, pgvector)에 저장
- 수천만 건 수준에서 ms 단위 유사도 검색 가능
- PostgreSQL + RDKit cartridge로 화학 특화 인덱싱

---

## 5. 본 프로젝트 적용 전략

| 단계 | 방식 | 규모 | 방법 |
|------|------|------|------|
| **현재** (Phase 1) | CSV + RDKit + networkx + LangGraph | ~22K molecules | 7가지 방법 비교 |
| **Phase 2** | PostgreSQL + RDKit cartridge 또는 pgvector | ~1M molecules | FP 사전 계산 + 인덱싱 |
| **Phase 3** | Neo4j + 벡터 DB + LLM | 10M+ molecules | Graph RAG + 자연어 질의 |

### 유사도 스코어 기준

**Tanimoto Coefficient** (Fingerprint 5종 + MCS):
- 범위: 0.0 ~ 1.0
- 1.0: 완전 동일
- ≥ 0.85: 높은 유사도 (MCS 기준)
- ≥ 0.7: 중간 유사도 (MACCS 기준)
- < 0.5: 낮은 유사도

**Graph RAG 결합 점수**:
- 범위: 0.0 ~ 1.0
- 계산: Jaccard(fragment 집합) × 0.6 + Tanimoto(Morgan FP) × 0.4
- Jaccard 비중이 높아 그래프 관계를 더 많이 반영

---

## 참고문헌

1. Rogers, D. & Hahn, M. "Extended-Connectivity Fingerprints." *J. Chem. Inf. Model.*, 2010, 50(5), 742-754.
2. Durant, J.L. et al. "Reoptimization of MDL Keys for Use in Drug Discovery." *J. Chem. Inf. Comput. Sci.*, 2002, 42(6), 1273-1280.
3. Carhart, R.E. et al. "Atom Pairs as Molecular Features in Structure-Activity Studies." *J. Chem. Inf. Comput. Sci.*, 1985, 25(2), 64-73.
4. Nilakantan, R. et al. "Topological Torsion: A New Molecular Descriptor for SAR Applications." *J. Chem. Inf. Comput. Sci.*, 1987, 27(2), 82-85.
5. Raymond, J.W. & Willett, P. "Maximum Common Subgraph Isomorphism Algorithms for the Matching of Chemical Structures." *J. Comput.-Aided Mol. Des.*, 2002, 16, 521-533.
6. Degen, J. et al. "On the Art of Compiling and Using 'Drug-Like' Chemical Fragment Spaces." *ChemMedChem*, 2008, 3(10), 1503-1507. (BRICS)
7. Lewis, P. et al. "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *NeurIPS*, 2020. (RAG)
8. Edge, D. et al. "From Local to Global: A Graph RAG Approach to Query-Focused Summarization." Microsoft Research, 2024. (Graph RAG)
9. RDKit: Open-Source Cheminformatics Software. https://www.rdkit.org/
10. LangGraph Documentation. https://langchain-ai.github.io/langgraph/
11. Merchant, A. et al. "Scaling deep learning for materials discovery." *Nature*, 2023, 624, 80-85. (GNoME)
12. Zeni, C. et al. "MatterGen: a generative model for inorganic materials design." *Nature*, 2025, 637, 85-91.
