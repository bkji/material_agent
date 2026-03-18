"""Fragment 유사도 검색 모듈 (다중 방법 지원)

SMILES fragment를 입력받아 QM8 데이터셋에서 해당 fragment를 포함하는
분자를 유사도 순으로 검색한다.

지원하는 유사도 방법:
1. Morgan (ECFP) Fingerprint + Tanimoto
2. MACCS Keys + Tanimoto
3. RDKit Fingerprint + Tanimoto
4. AtomPair Fingerprint + Tanimoto
5. Topological Torsion Fingerprint + Tanimoto
6. MCS (Maximum Common Substructure) 기반 유사도
"""

import os
import time
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs, MACCSkeys, rdFingerprintGenerator, rdFMCS
from rdkit import RDLogger

RDLogger.logger().setLevel(RDLogger.ERROR)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "0_qm8_260318", "qm8.csv")

# 지원하는 유사도 방법 목록
METHODS = ["morgan", "maccs", "rdkit", "atompair", "torsion", "mcs"]

METHOD_DESCRIPTIONS = {
    "morgan": "Morgan (ECFP4) Fingerprint + Tanimoto",
    "maccs": "MACCS Keys (166bit) + Tanimoto",
    "rdkit": "RDKit Fingerprint + Tanimoto",
    "atompair": "AtomPair Fingerprint + Tanimoto",
    "torsion": "Topological Torsion Fingerprint + Tanimoto",
    "mcs": "Maximum Common Substructure (MCS) 기반 유사도",
}


def load_molecules(data_path: str = DATA_PATH) -> list[dict]:
    """QM8 데이터셋에서 SMILES를 로드하고 RDKit Mol 객체 및 전체 fingerprint를 생성한다."""
    df = pd.read_csv(data_path)
    smiles_list = df["smiles"].tolist()

    molecules = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            molecules.append({
                "smiles": smi,
                "mol": mol,
                "fp_morgan": AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048),
                "fp_maccs": MACCSkeys.GenMACCSKeys(mol),
                "fp_rdkit": Chem.RDKFingerprint(mol, fpSize=2048),
                "fp_atompair": rdFingerprintGenerator.GetAtomPairGenerator().GetFingerprint(mol),
                "fp_torsion": rdFingerprintGenerator.GetTopologicalTorsionGenerator().GetFingerprint(mol),
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


def _compute_fragment_fps(fragment_mol: Chem.Mol) -> dict:
    """Fragment의 모든 fingerprint를 한번에 계산한다."""
    return {
        "fp_morgan": AllChem.GetMorganFingerprintAsBitVect(fragment_mol, radius=2, nBits=2048),
        "fp_maccs": MACCSkeys.GenMACCSKeys(fragment_mol),
        "fp_rdkit": Chem.RDKFingerprint(fragment_mol, fpSize=2048),
        "fp_atompair": rdFingerprintGenerator.GetAtomPairGenerator().GetFingerprint(fragment_mol),
        "fp_torsion": rdFingerprintGenerator.GetTopologicalTorsionGenerator().GetFingerprint(fragment_mol),
    }


def _calc_mcs_similarity(fragment_mol: Chem.Mol, target_mol: Chem.Mol) -> float:
    """MCS 기반 유사도를 계산한다. MCS 원자수 / max(두 분자 원자수)."""
    mcs = rdFMCS.FindMCS(
        [fragment_mol, target_mol],
        timeout=1,
        matchValences=False,
        ringMatchesRingOnly=True,
    )
    if mcs.canceled or mcs.numAtoms == 0:
        return 0.0
    max_atoms = max(fragment_mol.GetNumAtoms(), target_mol.GetNumAtoms())
    if max_atoms == 0:
        return 0.0
    return mcs.numAtoms / max_atoms


def search_fragment(
    fragment_smiles: str,
    molecules: list[dict] | None = None,
    top_k: int = 10,
    substruct_filter: bool = True,
    methods: list[str] | None = None,
    data_path: str = DATA_PATH,
) -> dict:
    """Fragment 유사도 검색 메인 함수 (다중 방법 지원).

    Args:
        fragment_smiles: 검색할 fragment SMILES
        molecules: 사전 로드된 분자 리스트 (None이면 자동 로드)
        top_k: 반환할 상위 결과 수
        substruct_filter: 부분구조 필터링 사용 여부
        methods: 사용할 유사도 방법 리스트 (None이면 전체)
        data_path: QM8 데이터 경로

    Returns:
        {
            "query_fragment": str,
            "methods_used": [str],
            "total_candidates": int,
            "results": {method: [{smiles, similarity_score}, ...]},
            "elapsed": {method: float (초)},
        }
    """
    if molecules is None:
        molecules = load_molecules(data_path)

    if methods is None:
        methods = METHODS.copy()
    else:
        methods = [m for m in methods if m in METHODS]

    fragment_mol = parse_fragment(fragment_smiles)
    if fragment_mol is None:
        return {
            "query_fragment": fragment_smiles,
            "error": f"유효하지 않은 SMILES: {fragment_smiles}",
            "methods_used": methods,
            "total_candidates": 0,
            "results": {},
            "elapsed": {},
        }

    # 부분구조 필터링
    if substruct_filter:
        candidates = search_by_substructure(fragment_mol, molecules)
    else:
        candidates = molecules

    total_candidates = len(candidates)
    fragment_fps = _compute_fragment_fps(fragment_mol)

    all_results = {}
    all_elapsed = {}

    # Fingerprint 기반 방법들
    fp_methods = [m for m in methods if m != "mcs"]
    for method in fp_methods:
        t0 = time.perf_counter()
        fp_key = f"fp_{method}"
        frag_fp = fragment_fps[fp_key]

        results = []
        for mol_data in candidates:
            sim = DataStructs.TanimotoSimilarity(frag_fp, mol_data[fp_key])
            results.append({
                "smiles": mol_data["smiles"],
                "similarity_score": round(sim, 4),
            })
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        all_results[method] = results[:top_k]
        all_elapsed[method] = round(time.perf_counter() - t0, 4)

    # MCS 방법 (후보가 너무 많으면 상위 substructure match만 대상)
    if "mcs" in methods:
        t0 = time.perf_counter()
        mcs_candidates = candidates[:200] if len(candidates) > 200 else candidates
        results = []
        for mol_data in mcs_candidates:
            sim = _calc_mcs_similarity(fragment_mol, mol_data["mol"])
            results.append({
                "smiles": mol_data["smiles"],
                "similarity_score": round(sim, 4),
            })
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        all_results["mcs"] = results[:top_k]
        all_elapsed["mcs"] = round(time.perf_counter() - t0, 4)

    return {
        "query_fragment": fragment_smiles,
        "methods_used": methods,
        "total_candidates": total_candidates,
        "results": all_results,
        "elapsed": all_elapsed,
    }
