# Fragment 유사도 검색 방법론 비교

## 1. 유사도 검색 방식의 종류

### 1.1 Fingerprint 기반 유사도 (Molecular Fingerprint Similarity)

**방법**: 분자를 비트 벡터(fingerprint)로 변환하여 Tanimoto, Dice 등의 계수로 유사도 계산

- **종류**: MACCS Keys, Morgan (ECFP), RDKit Fingerprint, Topological Fingerprint
- **장점**:
  - 계산 속도가 매우 빠름 (비트 연산)
  - 대규모 데이터셋에 적합 (1000만건 이상 처리 가능)
  - Fragment 수준의 부분구조 매칭에 적합 (특히 Morgan FP)
  - 산업 표준으로 검증된 방법
- **단점**:
  - 정보 손실 (해시 충돌)
  - 3D 구조 정보 반영 불가
  - Fragment의 위치/연결 정보가 부분적으로만 반영됨

### 1.2 Substructure Matching (부분구조 매칭)

**방법**: SMARTS 패턴을 이용한 부분구조 검색 (exact substructure match)

- **장점**:
  - 정확한 Fragment 포함 여부 판별
  - 화학적으로 명확한 의미
- **단점**:
  - Boolean 결과 (유사도 스코어 없음)
  - 유연한 검색 불가
  - 대규모 데이터에서 속도 저하

### 1.3 Graph Neural Network (GNN) 기반 유사도

**방법**: GNN으로 분자 그래프를 임베딩 벡터로 변환하여 코사인 유사도 등으로 비교

- **장점**:
  - 분자의 구조적 특성을 깊이 학습
  - 화학적 성질 기반 유사도 반영 가능
  - Transfer learning 활용 가능
- **단점**:
  - 학습 데이터 필요
  - 계산 비용 높음
  - 모델 해석이 어려움

### 1.4 Graph RAG (Retrieval-Augmented Generation with Graph)

**방법**: 분자 그래프를 Knowledge Graph로 구축하고, RAG 파이프라인과 결합하여 검색

- **장점**:
  - Fragment 간 관계를 그래프로 모델링 가능
  - 자연어 질의와 결합 가능 (LLM 활용)
  - 구조-성질 관계를 그래프에 저장하여 풍부한 컨텍스트 제공
  - 새 데이터 추가 시 그래프 확장만으로 대응
- **단점**:
  - 그래프 구축 초기 비용이 높음
  - LLM 호출 비용 발생
  - 화학 도메인에 특화된 그래프 스키마 설계 필요
  - 아직 재료/화학 분야에서 성숙도 낮음

### 1.5 Maximum Common Substructure (MCS)

**방법**: 두 분자 간 최대 공통 부분구조를 찾아 유사도 계산

- **장점**:
  - 화학적으로 직관적인 유사도
  - Fragment 매칭에 매우 적합
- **단점**:
  - NP-hard 문제로 계산 비용 매우 높음
  - 대규모 데이터셋에 부적합

---

## 2. Graph RAG vs 기존 방법 비교

| 항목 | Fingerprint | GNN | Graph RAG |
|------|------------|-----|-----------|
| **검색 속도** | 매우 빠름 | 보통 | 보통~느림 |
| **확장성 (1000만건)** | 우수 | 보통 | 보통 (인덱싱 필요) |
| **Fragment 매칭** | 좋음 | 좋음 | 매우 좋음 |
| **해석 가능성** | 보통 | 낮음 | 높음 |
| **구축 비용** | 낮음 | 높음 | 높음 |
| **자연어 질의** | 불가 | 불가 | 가능 |
| **관계 추론** | 불가 | 제한적 | 가능 |

**Graph RAG가 유리한 경우**:
- Fragment 간 화학적 관계(작용기 변환, 생물학적 활성 등)를 추론해야 할 때
- 연구자가 자연어로 복합 조건을 질의할 때
- 구조-성질 관계를 함께 탐색할 때

**Fingerprint가 유리한 경우**:
- 대규모 스크리닝 (속도가 중요)
- 단순 유사도 순위가 목적일 때
- 인프라 비용을 최소화해야 할 때

---

## 3. 재료 분야 최근 기술 경향

### 3.1 AI/ML 기반 재료 탐색
- **Foundation Models for Chemistry**: 대규모 화학 데이터로 사전학습된 모델 (예: ChemBERTa, MolBERT)이 분자 표현 학습에 활용
- **Inverse Design**: 목표 물성에서 역으로 분자 구조를 생성하는 생성 모델 (VAE, GAN, Diffusion) 활발

### 3.2 Graph 기반 접근
- **Molecular Graph Transformer**: 분자 그래프에 Transformer 적용하여 성질 예측
- **Knowledge Graph for Materials**: MatKG, Materials Project 등 재료 지식 그래프 구축 및 활용 증가

### 3.3 자율 실험 및 에이전트
- **LLM Agent for Chemistry**: LLM 기반 에이전트가 실험 계획, 문헌 검색, 합성 경로 제안
- **Self-Driving Labs**: 자동화된 실험-분석-최적화 루프

### 3.4 Fragment 기반 설계
- **Fragment-Based Drug/Material Design**: Fragment를 조합하여 원하는 성질의 분자 설계
- **Combinatorial Fragment Libraries**: 대규모 Fragment 라이브러리 구축 및 가상 스크리닝

---

## 4. 본 프로젝트 선택: Morgan Fingerprint + Tanimoto 유사도

### 선택 근거
1. **Fragment 매칭에 적합**: Morgan Fingerprint(ECFP)는 원자 주변 환경을 원형으로 인코딩하여 Fragment 패턴 매칭에 최적
2. **확장성**: 1000만건 수준에서도 빠른 검색 가능 (비트 연산 기반)
3. **표준화**: 화학 정보학에서 가장 널리 사용되는 방법
4. **구현 용이**: RDKit으로 즉시 구현 가능
5. **향후 확장**: DB 마이그레이션 시 PostgreSQL + RDKit cartridge 또는 벡터 DB로 자연스럽게 전환 가능

### 유사도 스코어 기준
- **Tanimoto Coefficient**: 0.0 ~ 1.0 범위
  - 1.0: 완전 동일
  - 0.7 이상: 높은 유사도
  - 0.5 ~ 0.7: 중간 유사도
  - 0.5 미만: 낮은 유사도
