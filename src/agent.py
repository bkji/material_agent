"""
LangGraph 기반 Fragment Similarity Search Agent

노드 구성:
  - parse_input: 사용자 SMILES 파싱 및 유효성 검증
  - search_substructure: substructure match 필터링 + Tanimoto 랭킹
  - format_output: 결과 포맷팅
"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
import logging

from .search_engine import FragmentSearchEngine, SearchResult
from .indexing import MoleculeIndex

logger = logging.getLogger(__name__)


# ─── State 정의 ───

class AgentState(TypedDict):
    """Agent의 상태를 정의합니다."""
    # 입력
    fragment_smiles: str
    top_k: int
    min_score: float

    # 중간 결과
    canonical_smiles: Optional[str]
    is_valid: bool
    error_message: Optional[str]

    # 검색 결과
    results: list[dict]

    # 최종 출력
    formatted_output: str


# ─── 노드 함수들 ───

def parse_input(state: AgentState) -> AgentState:
    """
    사용자 입력 SMILES를 파싱하고 유효성을 검증합니다.
    """
    from rdkit import Chem

    fragment_smiles = state["fragment_smiles"].strip()
    mol = Chem.MolFromSmiles(fragment_smiles)

    if mol is None:
        return {
            **state,
            "is_valid": False,
            "error_message": f"유효하지 않은 SMILES입니다: {fragment_smiles}",
            "canonical_smiles": None,
        }

    canonical = Chem.MolToSmiles(mol)
    logger.info(f"Input parsed: {fragment_smiles} → {canonical}")

    return {
        **state,
        "is_valid": True,
        "canonical_smiles": canonical,
        "error_message": None,
    }


def search_molecules(state: AgentState, engine: FragmentSearchEngine) -> AgentState:
    """
    Fragment로 유사 분자를 검색합니다.
    1차: Substructure match 필터링
    2차: Tanimoto similarity 랭킹
    """
    if not state.get("is_valid"):
        return state

    try:
        results = engine.search(
            fragment_smiles=state["canonical_smiles"],
            top_k=state.get("top_k", 10),
            min_score=state.get("min_score", 0.0),
        )
        return {
            **state,
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            **state,
            "is_valid": False,
            "error_message": f"검색 중 오류 발생: {str(e)}",
            "results": [],
        }


def format_output(state: AgentState) -> AgentState:
    """검색 결과를 포맷팅합니다."""
    if not state.get("is_valid"):
        return {
            **state,
            "formatted_output": f"❌ Error: {state.get('error_message', 'Unknown error')}",
        }

    results = state.get("results", [])
    if not results:
        return {
            **state,
            "formatted_output": f"🔍 Fragment: {state['canonical_smiles']}\n\n결과 없음 (유사한 분자를 찾지 못했습니다)",
        }

    lines = [
        f"🔍 Input Fragment: {state['canonical_smiles']}",
        f"📊 검색 결과: {len(results)}건\n",
        f"{'순위':<4} {'SMILES':<40} {'유사도':<8} {'매칭 유형'}",
        "-" * 70,
    ]

    for i, r in enumerate(results, 1):
        match_icon = "🎯" if r["match_type"] == "substructure" else "📐"
        lines.append(
            f"{i:<4} {r['smiles']:<40} {r['score']:<8.4f} {match_icon} {r['match_type']}"
        )

    lines.append(f"\n🎯 = substructure match (fragment 포함)")
    lines.append(f"📐 = similarity only (구조 유사)")

    return {
        **state,
        "formatted_output": "\n".join(lines),
    }


# ─── Agent 그래프 구성 ───

def create_agent(engine: FragmentSearchEngine) -> StateGraph:
    """
    LangGraph Agent를 생성합니다.

    Args:
        engine: 초기화된 FragmentSearchEngine

    Returns:
        컴파일된 LangGraph StateGraph
    """

    def search_node(state: AgentState) -> AgentState:
        return search_molecules(state, engine)

    # 그래프 정의
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("search", search_node)
    workflow.add_node("format_output", format_output)

    # 엣지 정의
    workflow.set_entry_point("parse_input")

    # 유효성 검증 후 분기
    def should_search(state: AgentState) -> str:
        if state.get("is_valid"):
            return "search"
        return "format_output"  # 에러 시 바로 출력으로

    workflow.add_conditional_edges("parse_input", should_search)
    workflow.add_edge("search", "format_output")
    workflow.add_edge("format_output", END)

    return workflow.compile()


# ─── 편의 함수 ───

def run_search(
    engine: FragmentSearchEngine,
    fragment_smiles: str,
    top_k: int = 10,
    min_score: float = 0.0,
) -> str:
    """
    단일 검색을 실행하는 편의 함수입니다.

    Args:
        engine: FragmentSearchEngine 인스턴스
        fragment_smiles: 검색할 fragment SMILES
        top_k: 반환할 최대 결과 수
        min_score: 최소 유사도 점수

    Returns:
        포맷팅된 결과 문자열
    """
    agent = create_agent(engine)

    initial_state: AgentState = {
        "fragment_smiles": fragment_smiles,
        "top_k": top_k,
        "min_score": min_score,
        "canonical_smiles": None,
        "is_valid": False,
        "error_message": None,
        "results": [],
        "formatted_output": "",
    }

    result = agent.invoke(initial_state)
    return result["formatted_output"]
