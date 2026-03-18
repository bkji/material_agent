"""
유사도 검색 엔진
- 1차 필터: RDKit HasSubstructMatch로 fragment 포함 분자 필터링
- 2차 랭킹: Morgan Fingerprint Tanimoto similarity로 점수화
"""

from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem
from dataclasses import dataclass
from typing import Optional
import logging

from .indexing import MoleculeIndex

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """검색 결과 단일 항목"""
    smiles: str
    score: float
    match_type: str  # "substructure" or "similarity"

    def to_dict(self) -> dict:
        return {
            "smiles": self.smiles,
            "score": round(self.score, 4),
            "match_type": self.match_type
        }


class FragmentSearchEngine:
    """Fragment 기반 분자 유사도 검색 엔진"""

    def __init__(self, index: MoleculeIndex):
        self.index = index

    def search(
        self,
        fragment_smiles: str,
        top_k: int = 10,
        min_score: float = 0.0,
        substructure_only: bool = False,
    ) -> list[SearchResult]:
        """
        Fragment SMILES로 유사한 분자를 검색합니다.

        Args:
            fragment_smiles: 검색할 fragment의 SMILES 문자열
            top_k: 반환할 최대 결과 수
            min_score: 최소 유사도 점수 (0~1)
            substructure_only: True이면 substructure match만 수행

        Returns:
            SearchResult 리스트 (유사도 내림차순)
        """
        if not self.index.is_built:
            raise RuntimeError("Index is not built. Call build_from_dataframe first.")

        fragment_mol = Chem.MolFromSmiles(fragment_smiles)
        if fragment_mol is None:
            raise ValueError(f"Invalid SMILES: {fragment_smiles}")

        # Phase 1: Substructure match 필터링
        substruct_hits = self._substructure_search(fragment_mol)
        logger.info(f"Substructure matches: {len(substruct_hits)}")

        if substructure_only:
            # substructure match된 분자만 Tanimoto로 랭킹
            candidates = substruct_hits
        else:
            # 전체 분자에 대해 Tanimoto 유사도 계산
            candidates = set(range(len(self.index.smiles_list)))

        # Phase 2: Tanimoto similarity 랭킹
        fragment_fp = AllChem.GetMorganFingerprintAsBitVect(
            fragment_mol, radius=2, nBits=2048
        )
        results = self._tanimoto_rank(
            fragment_fp, candidates, substruct_hits, top_k, min_score
        )

        return results

    def _substructure_search(self, fragment_mol: Chem.Mol) -> set[int]:
        """Substructure match로 fragment를 포함하는 분자 인덱스를 반환합니다."""
        hits = set()
        for idx, mol in enumerate(self.index.mol_list):
            if mol is not None:
                try:
                    if mol.HasSubstructMatch(fragment_mol):
                        hits.add(idx)
                except Exception:
                    continue
        return hits

    def _tanimoto_rank(
        self,
        query_fp: DataStructs.ExplicitBitVect,
        candidates: set[int],
        substruct_hits: set[int],
        top_k: int,
        min_score: float,
    ) -> list[SearchResult]:
        """Tanimoto similarity로 후보 분자를 랭킹합니다."""
        scored = []

        for idx in candidates:
            if idx >= len(self.index.fingerprints):
                continue

            score = DataStructs.TanimotoSimilarity(
                query_fp, self.index.fingerprints[idx]
            )

            if score >= min_score:
                match_type = "substructure" if idx in substruct_hits else "similarity"
                scored.append(SearchResult(
                    smiles=self.index.smiles_list[idx],
                    score=score,
                    match_type=match_type,
                ))

        # 유사도 내림차순 정렬, substructure match 우선
        scored.sort(key=lambda r: (-int(r.match_type == "substructure"), -r.score))

        return scored[:top_k]

    def validate_smiles(self, smiles: str) -> tuple[bool, Optional[str]]:
        """
        SMILES 유효성을 검증합니다.

        Returns:
            (유효 여부, canonical SMILES 또는 에러 메시지)
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, f"Invalid SMILES string: {smiles}"
        return True, Chem.MolToSmiles(mol)
