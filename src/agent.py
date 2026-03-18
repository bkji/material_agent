# -*- coding: utf-8 -*-
"""Fragment 유사도 검색 LangGraph 에이전트

LangGraph의 StateGraph를 사용하여 fragment 유사도 검색 워크플로우를 구현한다.

워크플로우:
1. parse_input: 사용자 입력(fragment SMILES) 파싱 및 검증
2. load_data: QM8 데이터셋 로드
3. search_similar: fragment 유사도 검색 수행
4. format_output: 결과 포맷팅 및 출력
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END

from similarity import load_molecules, parse_fragment, search_fragment


# --- State 정의 ---

class AgentState(TypedDict):
    """에이전트의 상태를 관리하는 TypedDict."""
    fragment_smiles: str
    top_k: int
    substruct_filter: bool
    molecules: list | None
    search_result: dict | None
    output: str
    error: str | None


# --- 노드 함수 ---

def parse_input(state: AgentState) -> dict:
    """사용자 입력을 검증한다."""
    fragment_smiles = state["fragment_smiles"].strip()

    if not fragment_smiles:
        return {"error": "Fragment SMILES가 비어있습니다."}

    mol = parse_fragment(fragment_smiles)
    if mol is None:
        return {"error": f"유효하지 않은 SMILES입니다: {fragment_smiles}"}

    return {"fragment_smiles": fragment_smiles, "error": None}


def load_data(state: AgentState) -> dict:
    """QM8 데이터셋을 로드한다."""
    try:
        molecules = load_molecules()
        return {"molecules": molecules}
    except Exception as e:
        return {"error": f"데이터 로드 실패: {str(e)}"}


def search_similar(state: AgentState) -> dict:
    """Fragment 유사도 검색을 수행한다."""
    result = search_fragment(
        fragment_smiles=state["fragment_smiles"],
        molecules=state["molecules"],
        top_k=state["top_k"],
        substruct_filter=state["substruct_filter"],
    )
    return {"search_result": result}


def format_output(state: AgentState) -> dict:
    """검색 결과를 사용자에게 보여줄 형식으로 포맷팅한다."""
    result = state["search_result"]

    if "error" in result:
        return {"output": f"오류: {result['error']}"}

    lines = []
    lines.append(f"=== Fragment 유사도 검색 결과 ===")
    lines.append(f"검색 Fragment: {result['query_fragment']}")
    lines.append(f"후보 분자 수: {result['total_candidates']}")
    lines.append(f"상위 {len(result['results'])}개 결과:")
    lines.append("-" * 60)
    lines.append(f"{'순위':<6}{'SMILES':<40}{'유사도':>10}")
    lines.append("-" * 60)

    for i, item in enumerate(result["results"], 1):
        smiles = item["smiles"]
        if len(smiles) > 37:
            smiles = smiles[:34] + "..."
        score = item["similarity_score"]
        lines.append(f"{i:<6}{smiles:<40}{score:>10.4f}")

    lines.append("-" * 60)
    return {"output": "\n".join(lines)}


# --- 라우팅 함수 ---

def should_continue(state: AgentState) -> str:
    """에러가 있으면 종료, 없으면 다음 단계로 진행."""
    if state.get("error"):
        return "error"
    return "continue"


# --- 그래프 빌드 ---

def build_graph() -> StateGraph:
    """LangGraph 워크플로우를 구성한다."""
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("load_data", load_data)
    workflow.add_node("search_similar", search_similar)
    workflow.add_node("format_output", format_output)

    # 엣지 설정
    workflow.set_entry_point("parse_input")

    workflow.add_conditional_edges(
        "parse_input",
        should_continue,
        {"continue": "load_data", "error": END},
    )

    workflow.add_conditional_edges(
        "load_data",
        should_continue,
        {"continue": "search_similar", "error": END},
    )

    workflow.add_edge("search_similar", "format_output")
    workflow.add_edge("format_output", END)

    return workflow.compile()


def run_agent(
    fragment_smiles: str,
    top_k: int = 10,
    substruct_filter: bool = True,
) -> str:
    """에이전트를 실행하여 fragment 유사도 검색을 수행한다.

    Args:
        fragment_smiles: 검색할 fragment SMILES
        top_k: 반환할 상위 결과 수
        substruct_filter: 부분구조 필터링 사용 여부

    Returns:
        포맷팅된 검색 결과 문자열
    """
    graph = build_graph()

    initial_state: AgentState = {
        "fragment_smiles": fragment_smiles,
        "top_k": top_k,
        "substruct_filter": substruct_filter,
        "molecules": None,
        "search_result": None,
        "output": "",
        "error": None,
    }

    final_state = graph.invoke(initial_state)

    if final_state.get("error"):
        return f"오류: {final_state['error']}"

    return final_state["output"]


# --- CLI 인터페이스 ---

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("  Fragment 유사도 검색 에이전트 (LangGraph)")
    print("  데이터: QM8 dataset (21,787 molecules)")
    print("  유사도: Morgan Fingerprint + Tanimoto Coefficient")
    print("=" * 60)

    if len(sys.argv) > 1:
        # 커맨드라인 인자로 실행
        fragment = sys.argv[1]
        top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(f"\n입력 Fragment: {fragment}")
        result = run_agent(fragment, top_k=top_k)
        print(result)
    else:
        # 대화형 모드
        print("\nFragment SMILES를 입력하세요 (종료: q)")
        print("예시: c1ccccc1 (벤젠), [NH2] (아미노기), C=O (카르보닐)")
        print()

        while True:
            fragment = input("Fragment SMILES> ").strip()
            if fragment.lower() in ("q", "quit", "exit"):
                print("종료합니다.")
                break
            if not fragment:
                continue

            print("\n검색 중...")
            result = run_agent(fragment, top_k=10)
            print(result)
            print()
