"""
데이터 전처리 모듈
- QM8 CSV에서 SMILES 로드
- RDKit으로 유효성 검증 및 canonical화
- BRICS / Murcko decomposition으로 fragment 분해
"""

import pandas as pd
from rdkit import Chem
from rdkit.Chem import BRICS, AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def load_smiles_from_csv(csv_path: str) -> pd.DataFrame:
    """QM8 CSV에서 SMILES 컬럼만 로드하고 canonical화합니다."""
    df = pd.read_csv(csv_path)
    smiles_col = df.columns[0]  # 첫 번째 컬럼이 SMILES

    records = []
    invalid_count = 0

    for idx, smi in enumerate(df[smiles_col]):
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            canonical = Chem.MolToSmiles(mol)
            records.append({
                "original_smiles": smi,
                "canonical_smiles": canonical,
                "mol_idx": idx
            })
        else:
            invalid_count += 1
            logger.warning(f"Invalid SMILES at row {idx}: {smi}")

    logger.info(f"Loaded {len(records)} valid molecules ({invalid_count} invalid)")
    return pd.DataFrame(records)


def decompose_brics(smiles: str) -> list[str]:
    """BRICS decomposition으로 fragment SMILES 리스트를 반환합니다."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    try:
        fragments = BRICS.BRICSDecompose(mol)
        # dummy atom [*] 표기 제거하여 clean SMILES로 변환
        clean_fragments = []
        for frag in fragments:
            # [숫자*] 패턴을 [H]로 대체
            clean_mol = Chem.MolFromSmiles(frag)
            if clean_mol is not None:
                clean_fragments.append(Chem.MolToSmiles(clean_mol))
        return clean_fragments
    except Exception as e:
        logger.warning(f"BRICS decomposition failed for {smiles}: {e}")
        return []


def get_murcko_scaffold(smiles: str) -> Optional[str]:
    """Murcko scaffold(핵심 골격)를 추출합니다."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    try:
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        return Chem.MolToSmiles(scaffold)
    except Exception as e:
        logger.warning(f"Murcko scaffold failed for {smiles}: {e}")
        return None


def get_generic_scaffold(smiles: str) -> Optional[str]:
    """Generic scaffold(모든 원자를 탄소로 치환한 골격)를 추출합니다."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    try:
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        generic = MurckoScaffold.MakeScaffoldGeneric(scaffold)
        return Chem.MolToSmiles(generic)
    except Exception as e:
        logger.warning(f"Generic scaffold failed for {smiles}: {e}")
        return None


def build_fragment_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    각 분자에 대해 fragment 정보를 추가합니다.

    Returns:
        DataFrame with columns: canonical_smiles, murcko_scaffold, brics_fragments
    """
    df = df.copy()
    df["murcko_scaffold"] = df["canonical_smiles"].apply(get_murcko_scaffold)
    df["brics_fragments"] = df["canonical_smiles"].apply(decompose_brics)

    logger.info(f"Fragment table built: {len(df)} molecules")
    return df


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/0_qm8_260318/qm8.csv"
    df = load_smiles_from_csv(csv_path)
    df = build_fragment_table(df)

    print(f"\nTotal molecules: {len(df)}")
    print(f"Sample:\n{df.head()}")
    print(f"\nSample BRICS fragments: {df['brics_fragments'].iloc[10]}")
