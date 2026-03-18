"""
인덱싱 모듈
- Morgan Fingerprint (radius=2, 2048bit) 생성
- Fragment별 역인덱스 구축
- numpy 배열로 메모리 인덱스 구성
"""

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import DataStructs
from collections import defaultdict
from typing import Optional
import pickle
import logging

logger = logging.getLogger(__name__)


class MoleculeIndex:
    """분자 검색을 위한 인덱스 클래스"""

    def __init__(self):
        self.smiles_list: list[str] = []
        self.mol_list: list[Chem.Mol] = []
        self.fingerprints: list[DataStructs.ExplicitBitVect] = []
        self.fp_array: Optional[np.ndarray] = None
        # fragment → [molecule indices] 역인덱스
        self.fragment_index: dict[str, list[int]] = defaultdict(list)
        self._built = False

    def build_from_dataframe(self, df: pd.DataFrame) -> None:
        """
        전처리된 DataFrame으로부터 인덱스를 구축합니다.

        Args:
            df: canonical_smiles, brics_fragments 컬럼이 있는 DataFrame
        """
        logger.info("Building molecule index...")

        self.smiles_list = df["canonical_smiles"].tolist()
        self.mol_list = []
        self.fingerprints = []

        for idx, smi in enumerate(self.smiles_list):
            mol = Chem.MolFromSmiles(smi)
            self.mol_list.append(mol)

            if mol is not None:
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
                self.fingerprints.append(fp)
            else:
                # placeholder (all zeros)
                fp = DataStructs.ExplicitBitVect(2048)
                self.fingerprints.append(fp)

        # numpy array로 변환 (bulk Tanimoto 연산용)
        self.fp_array = np.zeros((len(self.fingerprints), 2048), dtype=np.uint8)
        for i, fp in enumerate(self.fingerprints):
            arr = np.zeros(2048, dtype=np.uint8)
            DataStructs.ConvertToNumpyArray(fp, arr)
            self.fp_array[i] = arr

        # Fragment 역인덱스 구축
        if "brics_fragments" in df.columns:
            for idx, frags in enumerate(df["brics_fragments"]):
                if isinstance(frags, list):
                    for frag in frags:
                        self.fragment_index[frag].append(idx)

        self._built = True
        logger.info(
            f"Index built: {len(self.smiles_list)} molecules, "
            f"{len(self.fragment_index)} unique fragments"
        )

    def get_fingerprint(self, smiles: str) -> Optional[DataStructs.ExplicitBitVect]:
        """SMILES에 대한 Morgan Fingerprint를 생성합니다."""
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)

    def save(self, path: str) -> None:
        """인덱스를 파일로 저장합니다."""
        data = {
            "smiles_list": self.smiles_list,
            "fp_array": self.fp_array,
            "fragment_index": dict(self.fragment_index),
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"Index saved to {path}")

    def load(self, path: str) -> None:
        """저장된 인덱스를 로드합니다."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.smiles_list = data["smiles_list"]
        self.fp_array = data["fp_array"]
        self.fragment_index = defaultdict(list, data["fragment_index"])

        # mol_list 및 fingerprints 재구성
        self.mol_list = [Chem.MolFromSmiles(s) for s in self.smiles_list]
        self.fingerprints = []
        for smi in self.smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol:
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)
            else:
                fp = DataStructs.ExplicitBitVect(2048)
            self.fingerprints.append(fp)

        self._built = True
        logger.info(f"Index loaded: {len(self.smiles_list)} molecules")

    @property
    def is_built(self) -> bool:
        return self._built
