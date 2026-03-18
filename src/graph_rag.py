"""Graph RAG 기반 Fragment 유사도 검색 모듈

분자를 Knowledge Graph로 구축하여 fragment 기반 유사도 검색을 수행한다.

그래프 구조:
  - Molecule 노드: 각 분자 (SMILES, 속성)
  - Fragment 노드: BRICS 분해로 추출된 fragment
  - CONTAINS 엣지: 분자 → fragment (분자가 fragment를 포함)

유사도 계산:
  1. 쿼리 fragment를 포함하는 분자를 그래프 탐색으로 검색
  2. 검색된 분자들의 fragment 집합과 쿼리 fragment의 Jaccard 유사도 계산
  3. 그래프 경로 기반 관계 점수 (공유 fragment 수) 반영

Graph RAG의 핵심 가치:
  - Fragment 간 관계를 명시적으로 모델링
  - "같은 fragment를 공유하는 분자군" 탐색 가능
  - 향후 LLM과 결합하여 자연어 질의 가능
"""

import os
import time
import networkx as nx
import pandas as pd
from rdkit import Chem
from rdkit.Chem import BRICS, AllChem, DataStructs
from rdkit import RDLogger

RDLogger.logger().setLevel(RDLogger.ERROR)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "0_qm8_260318", "qm8.csv")


def decompose_to_fragments(mol: Chem.Mol) -> list[str]:
    """BRICS 분해로 분자를 fragment SMILES 리스트로 분해한다.

    BRICS (Breaking of Retrosynthetically Interesting Chemical Substructures)는
    합성적으로 의미 있는 결합을 끊어 fragment로 분해하는 방법이다.
    """
    try:
        frags = BRICS.BRICSDecompose(mol)
        # BRICS dummy atom([1*] 등)을 제거하여 정규화
        clean_frags = []
        for frag_smi in frags:
            # dummy atom 패턴 제거
            clean = Chem.MolFromSmiles(frag_smi)
            if clean is not None:
                canonical = Chem.MolToSmiles(clean)
                clean_frags.append(canonical)
        return clean_frags if clean_frags else [Chem.MolToSmiles(mol)]
    except Exception:
        return [Chem.MolToSmiles(mol)]


def build_knowledge_graph(data_path: str = DATA_PATH) -> nx.Graph:
    """QM8 데이터셋으로부터 분자-fragment Knowledge Graph를 구축한다.

    노드 타입:
      - molecule: SMILES, mol 객체, fingerprint 보유
      - fragment: BRICS 분해된 fragment SMILES

    엣지:
      - molecule -- CONTAINS --> fragment
    """
    G = nx.Graph()

    df = pd.read_csv(data_path)
    smiles_list = df["smiles"].tolist()

    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue

        # Molecule 노드 추가
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
        G.add_node(
            smi,
            node_type="molecule",
            mol=mol,
            fingerprint=fp,
        )

        # BRICS fragment 분해 및 Fragment 노드/엣지 추가
        fragments = decompose_to_fragments(mol)
        for frag_smi in fragments:
            if not G.has_node(frag_smi) or G.nodes[frag_smi].get("node_type") != "fragment":
                frag_mol = Chem.MolFromSmiles(frag_smi)
                G.add_node(
                    frag_smi,
                    node_type="fragment",
                    mol=frag_mol,
                )
            G.add_edge(smi, frag_smi, relation="CONTAINS")

    return G


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """두 집합의 Jaccard 유사도를 계산한다."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def graph_rag_search(
    G: nx.Graph,
    query_fragment_smiles: str,
    top_k: int = 10,
) -> dict:
    """Graph RAG 방식으로 fragment 유사도 검색을 수행한다.

    검색 전략:
    1단계 - 직접 매칭: 쿼리 fragment를 부분구조로 포함하는 분자를 substructure match로 검색
    2단계 - 그래프 탐색: 검색된 분자들의 이웃 fragment를 수집하여 fragment 집합 생성
    3단계 - 유사도 계산: 각 후보 분자의 fragment 집합과 쿼리 관련 fragment 집합의
            Jaccard 유사도 + Tanimoto 유사도를 결합하여 최종 점수 산출

    Args:
        G: 구축된 Knowledge Graph
        query_fragment_smiles: 검색할 fragment SMILES
        top_k: 반환할 상위 결과 수

    Returns:
        {
            "query_fragment": str,
            "graph_stats": {nodes, edges, molecule_nodes, fragment_nodes},
            "total_candidates": int,
            "results": [{smiles, similarity_score, shared_fragments, total_fragments}],
            "elapsed": float,
        }
    """
    t0 = time.perf_counter()

    # 그래프 통계
    mol_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "molecule"]
    frag_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "fragment"]

    graph_stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "molecule_nodes": len(mol_nodes),
        "fragment_nodes": len(frag_nodes),
    }

    # 쿼리 fragment 파싱
    query_mol = Chem.MolFromSmiles(query_fragment_smiles)
    if query_mol is None:
        query_mol = Chem.MolFromSmarts(query_fragment_smiles)
    if query_mol is None:
        return {
            "query_fragment": query_fragment_smiles,
            "graph_stats": graph_stats,
            "error": f"유효하지 않은 SMILES: {query_fragment_smiles}",
            "total_candidates": 0,
            "results": [],
            "elapsed": round(time.perf_counter() - t0, 4),
        }

    query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, radius=2, nBits=2048)

    # 1단계: substructure match로 후보 분자 검색
    candidate_molecules = []
    for mol_smi in mol_nodes:
        mol = G.nodes[mol_smi].get("mol")
        if mol is not None and mol.HasSubstructMatch(query_mol):
            candidate_molecules.append(mol_smi)

    if not candidate_molecules:
        candidate_molecules = mol_nodes

    # 2단계: 쿼리 fragment의 이웃 분석 (그래프 탐색)
    # 쿼리 fragment가 그래프에 있으면 그 이웃의 fragment 집합을 수집
    query_related_fragments = set()
    query_canonical = Chem.MolToSmiles(query_mol)

    # 쿼리와 substructure match하는 fragment 노드 찾기
    matching_frag_nodes = []
    for frag_smi in frag_nodes:
        frag_mol = G.nodes[frag_smi].get("mol")
        if frag_mol is not None:
            try:
                if frag_mol.HasSubstructMatch(query_mol) or query_mol.HasSubstructMatch(frag_mol):
                    matching_frag_nodes.append(frag_smi)
            except Exception:
                continue

    # 매칭된 fragment의 이웃(분자)의 다른 fragment를 수집 → 관련 fragment 집합
    for frag_smi in matching_frag_nodes:
        query_related_fragments.add(frag_smi)
        for neighbor in G.neighbors(frag_smi):
            if G.nodes[neighbor].get("node_type") == "molecule":
                for mol_neighbor in G.neighbors(neighbor):
                    if G.nodes[mol_neighbor].get("node_type") == "fragment":
                        query_related_fragments.add(mol_neighbor)

    # 3단계: 각 후보 분자의 유사도 계산
    results = []
    for mol_smi in candidate_molecules:
        mol_data = G.nodes[mol_smi]
        mol_fp = mol_data.get("fingerprint")

        # 이 분자의 fragment 집합
        mol_fragments = set()
        for neighbor in G.neighbors(mol_smi):
            if G.nodes[neighbor].get("node_type") == "fragment":
                mol_fragments.add(neighbor)

        # Fragment Jaccard 유사도 (그래프 기반)
        if query_related_fragments:
            jaccard_score = _jaccard_similarity(query_related_fragments, mol_fragments)
        else:
            jaccard_score = 0.0

        # Morgan Tanimoto 유사도 (보조)
        tanimoto_score = 0.0
        if mol_fp is not None:
            tanimoto_score = DataStructs.TanimotoSimilarity(query_fp, mol_fp)

        # 최종 점수: Jaccard 60% + Tanimoto 40% (그래프 관계 중심)
        combined_score = 0.6 * jaccard_score + 0.4 * tanimoto_score

        shared = len(query_related_fragments & mol_fragments) if query_related_fragments else 0

        results.append({
            "smiles": mol_smi,
            "similarity_score": round(combined_score, 4),
            "jaccard_score": round(jaccard_score, 4),
            "tanimoto_score": round(tanimoto_score, 4),
            "shared_fragments": shared,
            "total_fragments": len(mol_fragments),
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    elapsed = round(time.perf_counter() - t0, 4)

    return {
        "query_fragment": query_fragment_smiles,
        "graph_stats": graph_stats,
        "total_candidates": len(candidate_molecules),
        "results": results[:top_k],
        "elapsed": elapsed,
    }
