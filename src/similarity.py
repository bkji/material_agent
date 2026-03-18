"""Fragment similarity search engine using RDKit.

Provides two complementary search strategies:
1. Substructure filtering — exact fragment match (SMARTS-based)
2. Morgan fingerprint Tanimoto similarity — ranked by structural similarity

For future DB migration (10M+ records), the fingerprint-based approach can be
pre-computed and indexed (e.g. PostgreSQL + RDKit cartridge, or pgvector with
binary fingerprints).
"""

import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs
from rdkit import RDLogger

# Suppress RDKit deprecation warnings
RDLogger.logger().setLevel(RDLogger.ERROR)


def load_smiles(csv_path: str) -> list[str]:
    """Load SMILES column from QM8 CSV."""
    df = pd.read_csv(csv_path)
    return df["smiles"].tolist()


def canonicalize(smiles: str) -> str | None:
    """Return canonical SMILES, or None if invalid."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        mol = Chem.MolFromSmarts(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def compute_morgan_fp(mol, radius: int = 2, n_bits: int = 2048):
    """Compute Morgan fingerprint (ECFP-like) for a molecule."""
    gen = AllChem.GetMorganGenerator(radius=radius, fpSize=n_bits)
    return gen.GetFingerprint(mol)


def substructure_filter(smiles_list: list[str], fragment_smiles: str) -> list[str]:
    """Return SMILES that contain the fragment as a substructure."""
    frag_mol = Chem.MolFromSmarts(fragment_smiles)
    if frag_mol is None:
        frag_mol = Chem.MolFromSmiles(fragment_smiles)
    if frag_mol is None:
        return []

    matches = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol and mol.HasSubstructMatch(frag_mol):
            matches.append(smi)
    return matches


def tanimoto_search(
    smiles_list: list[str],
    fragment_smiles: str,
    top_k: int = 20,
    radius: int = 2,
    n_bits: int = 2048,
) -> list[dict]:
    """Rank molecules by Tanimoto similarity of Morgan fingerprints to fragment.

    Returns list of {"smiles": str, "canonical": str, "score": float}
    sorted descending by score.
    """
    frag_mol = Chem.MolFromSmiles(fragment_smiles)
    if frag_mol is None:
        frag_mol = Chem.MolFromSmarts(fragment_smiles)
    if frag_mol is None:
        return []

    frag_fp = compute_morgan_fp(frag_mol, radius, n_bits)

    results = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        mol_fp = compute_morgan_fp(mol, radius, n_bits)
        score = DataStructs.TanimotoSimilarity(frag_fp, mol_fp)
        results.append({
            "smiles": smi,
            "canonical": Chem.MolToSmiles(mol),
            "score": round(score, 4),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def fragment_similarity_search(
    csv_path: str,
    fragment_smiles: str,
    top_k: int = 20,
    use_substructure_filter: bool = True,
) -> list[dict]:
    """Main search: optionally filter by substructure, then rank by Tanimoto.

    Args:
        csv_path: Path to QM8 CSV file.
        fragment_smiles: SMILES of the fragment to search for.
        top_k: Number of top results to return.
        use_substructure_filter: If True, first filter to molecules containing
            the fragment, then rank. If False, rank all molecules.

    Returns:
        List of dicts with keys: smiles, canonical, score.
    """
    all_smiles = load_smiles(csv_path)

    if use_substructure_filter:
        candidates = substructure_filter(all_smiles, fragment_smiles)
        if not candidates:
            # Fall back to full search if no substructure matches
            candidates = all_smiles
    else:
        candidates = all_smiles

    return tanimoto_search(candidates, fragment_smiles, top_k=top_k)
