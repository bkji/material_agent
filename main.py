"""
Fragment Similarity Search Agent - 메인 실행 파일

사용법:
    python main.py                          # 대화형 모드
    python main.py "c1ccccc1"               # 단일 검색 (벤젠 링)
    python main.py "c1ccccc1" --top-k 20    # 상위 20개 결과
    python main.py --build-index            # 인덱스 빌드만 수행
"""

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "0_qm8_260318", "qm8.csv")
INDEX_PATH = os.path.join(PROJECT_ROOT, "data", "molecule_index.pkl")


def build_index(csv_path: str, save_path: str):
    """인덱스를 빌드하고 저장합니다."""
    from src.preprocessing import load_smiles_from_csv, build_fragment_table
    from src.indexing import MoleculeIndex

    logger.info(f"Loading data from {csv_path}")
    df = load_smiles_from_csv(csv_path)
    df = build_fragment_table(df)

    index = MoleculeIndex()
    index.build_from_dataframe(df)
    index.save(save_path)

    logger.info(f"Index built and saved to {save_path}")
    return index


def load_or_build_index(csv_path: str, index_path: str):
    """인덱스를 로드하거나, 없으면 빌드합니다."""
    from src.indexing import MoleculeIndex

    index = MoleculeIndex()

    if os.path.exists(index_path):
        logger.info(f"Loading existing index from {index_path}")
        index.load(index_path)
    else:
        logger.info("No existing index found. Building new index...")
        index = build_index(csv_path, index_path)

    return index


def interactive_mode(engine):
    """대화형 검색 모드"""
    from src.agent import run_search

    print("\n" + "=" * 60)
    print("  Fragment Similarity Search Agent")
    print("  대화형 모드 (종료: quit / exit)")
    print("=" * 60)

    while True:
        try:
            fragment = input("\n🔬 Fragment SMILES 입력> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if fragment.lower() in ("quit", "exit", "q"):
            print("종료합니다.")
            break

        if not fragment:
            continue

        # 옵션 파싱 (간단한 형태)
        top_k = 10
        min_score = 0.0

        parts = fragment.split()
        smiles = parts[0]
        for i, p in enumerate(parts[1:], 1):
            if p.startswith("--top-k="):
                top_k = int(p.split("=")[1])
            elif p.startswith("--min-score="):
                min_score = float(p.split("=")[1])

        result = run_search(engine, smiles, top_k=top_k, min_score=min_score)
        print("\n" + result)


def main():
    parser = argparse.ArgumentParser(
        description="Fragment Similarity Search Agent"
    )
    parser.add_argument(
        "fragment", nargs="?", default=None,
        help="검색할 fragment SMILES (없으면 대화형 모드)"
    )
    parser.add_argument(
        "--top-k", type=int, default=10,
        help="반환할 최대 결과 수 (default: 10)"
    )
    parser.add_argument(
        "--min-score", type=float, default=0.0,
        help="최소 유사도 점수 (default: 0.0)"
    )
    parser.add_argument(
        "--build-index", action="store_true",
        help="인덱스 빌드만 수행"
    )
    parser.add_argument(
        "--data-path", type=str, default=DATA_PATH,
        help="CSV 데이터 경로"
    )
    parser.add_argument(
        "--index-path", type=str, default=INDEX_PATH,
        help="인덱스 저장/로드 경로"
    )

    args = parser.parse_args()

    # 인덱스 빌드만
    if args.build_index:
        build_index(args.data_path, args.index_path)
        return

    # 인덱스 로드 또는 빌드
    index = load_or_build_index(args.data_path, args.index_path)

    # 검색 엔진 초기화
    from src.search_engine import FragmentSearchEngine
    engine = FragmentSearchEngine(index)

    if args.fragment:
        # 단일 검색 모드
        from src.agent import run_search
        result = run_search(engine, args.fragment, top_k=args.top_k, min_score=args.min_score)
        print(result)
    else:
        # 대화형 모드
        interactive_mode(engine)


if __name__ == "__main__":
    main()
