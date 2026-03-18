"""Fragment 유사도 검색 모듈

SMILES fragment를 입력받아 QM8 데이터셋에서 해당 fragment를 포함하는
분자를 유사도 순으로 검색한다.

유사도 계산 방식:
1. Substructure Match: fragment가 분자에 포함되는지 확인
2. Morgan Fingerprint + Tanimoto: fragment 기반 fingerprint 유사도 계산
"""

import os
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs
from rdkit import RDLogger

# RDKit 경고 메시지 억제
RDLogger.logger().setLevel(RDLogger.ERROR)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "0_qm8_260318", "qm8.csv")


def load_molecules(data_path: str = DATA_PATH) -> list[dict]:
    """QM8 데이터셋에서 SMILES를 로드하고 RDKit Mol 객체로 변환한다."""
    df = pd.read_csv(data_path)
    smiles_list = df["smiles"].tolist()

    molecules = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
            molecules.append({
                "smiles": smi,
                "mol": mol,
                "fingerprint": fp,
            })
    return molecules


def parse_fragment(fragment_smiles: str) -> Chem.Mol | None:
    """Fragment SMILES를 파싱하여 Mol 객체를 반환한다."""
    mol = Chem.MolFromSmiles(fragment_smiles)
    if mol is None:
        mol = Chem.MolFromSmarts(fragment_smiles)
    return mol


def search_by_substructure(fragment_mol: Chem.Mol, molecules: list[dict]) -> list[dict]:
    """Fragment를 부분구조로 포함하는 분자를 검색한다."""
    matches = []
    for mol_data in molecules:
        if mol_data["mol"].HasSubstructMatch(fragment_mol):
            matches.append(mol_data)
    return matches


def calculate_tanimoto_similarity(
    fragment_smiles: str,
    molecules: list[dict],
    top_k: int = 10,
    substruct_filter: bool = True,
) -> list[dict]:
    """Fragment와의 Tanimoto 유사도를 계산하여 상위 k개를 반환한다.

    Args:
        fragment_smiles: 검색할 fragment SMILES
        molecules: 로드된 분자 리스트
        top_k: 반환할 상위 결과 수
        substruct_filter: True면 부분구조 매칭 결과만 대상으로 유사도 계산

    Returns:
        유사도 순으로 정렬된 결과 리스트 [{smiles, similarity_score}, ...]
    """
    fragment_mol = parse_fragment(fragment_smiles)
    if fragment_mol is None:
        return []

    fragment_fp = AllChem.GetMorganFingerprintAsBitVect(fragment_mol, radius=2, nBits=2048)

    if substruct_filter:
        candidates = search_by_substructure(fragment_mol, molecules)
    else:
        candidates = molecules

    results = []
    for mol_data in candidates:
        similarity = DataStructs.TanimotoSimilarity(fragment_fp, mol_data["fingerprint"])
        results.append({
            "smiles": mol_data["smiles"],
            "similarity_score": round(similarity, 4),
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:top_k]


def search_fragment(
    fragment_smiles: str,
    molecules: list[dict] | None = None,
    top_k: int = 10,
    substruct_filter: bool = True,
    data_path: str = DATA_PATH,
) -> dict:
    """Fragment 유사도 검색의 메인 함수.

    Args:
        fragment_smiles: 검색할 fragment SMILES
        molecules: 사전 로드된 분자 리스트 (None이면 자동 로드)
        top_k: 반환할 상위 결과 수
        substruct_filter: 부분구조 필터링 사용 여부
        data_path: QM8 데이터 경로

    Returns:
        {
            "query_fragment": str,
            "total_candidates": int,
            "results": [{smiles, similarity_score}, ...]
        }
    """
    if molecules is None:
        molecules = load_molecules(data_path)

    fragment_mol = parse_fragment(fragment_smiles)
    if fragment_mol is None:
        return {
            "query_fragment": fragment_smiles,
            "error": f"유효하지 않은 SMILES: {fragment_smiles}",
            "total_candidates": 0,
            "results": [],
        }

    if substruct_filter:
        candidates = search_by_substructure(fragment_mol, molecules)
    else:
        candidates = molecules

    fragment_fp = AllChem.GetMorganFingerprintAsBitVect(fragment_mol, radius=2, nBits=2048)

    results = []
    for mol_data in candidates:
        similarity = DataStructs.TanimotoSimilarity(fragment_fp, mol_data["fingerprint"])
        results.append({
            "smiles": mol_data["smiles"],
            "similarity_score": round(similarity, 4),
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {
        "query_fragment": fragment_smiles,
        "total_candidates": len(candidates),
        "results": results[:top_k],
    }
