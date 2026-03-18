"""
백엔드 추상화 모듈
- CSV와 DB 백엔드를 교체 가능하도록 인터페이스 분리
- 향후 PostgreSQL + RDKit cartridge 전환 대비
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class SearchBackend(ABC):
    """검색 백엔드 추상 인터페이스"""

    @abstractmethod
    def load_data(self, **kwargs) -> pd.DataFrame:
        """데이터를 로드하여 DataFrame으로 반환합니다."""
        pass

    @abstractmethod
    def substructure_search(self, fragment_smiles: str) -> list[str]:
        """Substructure match로 fragment를 포함하는 SMILES 리스트를 반환합니다."""
        pass

    @abstractmethod
    def get_molecule_count(self) -> int:
        """저장된 분자 수를 반환합니다."""
        pass


class CSVBackend(SearchBackend):
    """CSV 파일 기반 백엔드 (현재 구현)"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._df: Optional[pd.DataFrame] = None

    def load_data(self, **kwargs) -> pd.DataFrame:
        from .preprocessing import load_smiles_from_csv, build_fragment_table

        df = load_smiles_from_csv(self.csv_path)
        df = build_fragment_table(df)
        self._df = df
        return df

    def substructure_search(self, fragment_smiles: str) -> list[str]:
        from rdkit import Chem

        if self._df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        fragment_mol = Chem.MolFromSmiles(fragment_smiles)
        if fragment_mol is None:
            return []

        hits = []
        for smi in self._df["canonical_smiles"]:
            mol = Chem.MolFromSmiles(smi)
            if mol and mol.HasSubstructMatch(fragment_mol):
                hits.append(smi)
        return hits

    def get_molecule_count(self) -> int:
        return len(self._df) if self._df is not None else 0


class PostgreSQLBackend(SearchBackend):
    """
    PostgreSQL + RDKit cartridge 백엔드 (향후 구현)

    필요 설정:
    - PostgreSQL with RDKit extension
    - GiST index on mol column

    예시 쿼리:
        SELECT smiles, tanimoto_sml(fp, morganbv_fp(%s))
        FROM molecules
        WHERE mol @> %s  -- substructure match
        ORDER BY tanimoto_sml DESC
        LIMIT %s;
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        logger.info(
            "PostgreSQL backend initialized. "
            "Note: Full implementation requires psycopg2 and RDKit PostgreSQL cartridge."
        )

    def load_data(self, **kwargs) -> pd.DataFrame:
        raise NotImplementedError(
            "PostgreSQL backend: load_data는 DB에서 직접 처리합니다. "
            "대신 SQL 쿼리를 통해 접근하세요.\n"
            "필요 테이블 구조:\n"
            "  CREATE TABLE molecules (\n"
            "    id SERIAL PRIMARY KEY,\n"
            "    smiles TEXT NOT NULL,\n"
            "    mol MOL GENERATED ALWAYS AS (mol_from_smiles(smiles::cstring)) STORED,\n"
            "    fp BFP GENERATED ALWAYS AS (morganbv_fp(mol)) STORED\n"
            "  );\n"
            "  CREATE INDEX idx_mol_substruct ON molecules USING gist(mol);\n"
            "  CREATE INDEX idx_fp_tanimoto ON molecules USING gist(fp);"
        )

    def substructure_search(self, fragment_smiles: str) -> list[str]:
        raise NotImplementedError(
            "PostgreSQL backend의 substructure search는 SQL로 직접 실행합니다:\n"
            "  SELECT smiles FROM molecules WHERE mol @> mol_from_smiles(%s::cstring);"
        )

    def get_molecule_count(self) -> int:
        raise NotImplementedError(
            "PostgreSQL backend: SELECT COUNT(*) FROM molecules;"
        )
