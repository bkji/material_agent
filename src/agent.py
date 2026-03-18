# -*- coding: utf-8 -*-
"""Fragment 유사도 검색 LangGraph 에이전트 (다중 방법 비교 지원)

LangGraph의 StateGraph를 사용하여 fragment 유사도 검색 워크플로우를 구현한다.

워크플로우:
1. parse_input: 사용자 입력(fragment SMILES) 파싱 및 검증
2. load_data: QM8 데이터셋 로드
3. search_similar: 선택된 방법(들)로 유사도 검색 수행
4. format_output: 결과 포맷팅 (단일/비교 모드)

지원 방법: morgan, maccs, rdkit, atompair, torsion, mcs
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END

from similarity import (
    load_molecules, parse_fragment, search_fragment,
    METHODS, METHOD_DESCRIPTIONS,
)


# --- State 정의 ---

class AgentState(TypedDict):
    fragment_smiles: str
    top_k: int
    substruct_filter: bool
    methods: list | None       # None이면 전체 방법 사용
    molecules: list | None
    search_result: dict | None
    output: str
    error: str | None


# --- 노드 함수 ---

def parse_input(state: AgentState) -> dict:
    fragment_smiles = state["fragment_smiles"].strip()
    if not fragment_smiles:
        return {"error": "Fragment SMILES가 비어있습니다."}
    mol = parse_fragment(fragment_smiles)
    if mol is None:
        return {"error": f"유효하지 않은 SMILES입니다: {fragment_smiles}"}
    return {"fragment_smiles": fragment_smiles, "error": None}


def load_data(state: AgentState) -> dict:
    try:
        molecules = load_molecules()
        return {"molecules": molecules}
    except Exception as e:
        return {"error": f"데이터 로드 실패: {str(e)}"}


def search_similar(state: AgentState) -> dict:
    result = search_fragment(
        fragment_smiles=state["fragment_smiles"],
        molecules=state["molecules"],
        top_k=state["top_k"],
        substruct_filter=state["substruct_filter"],
        methods=state.get("methods"),
    )
    return {"search_result": result}


def format_output(state: AgentState) -> dict:
    result = state["search_result"]

    if "error" in result and result["error"]:
        return {"output": f"오류: {result['error']}"}

    methods_used = result["methods_used"]
    all_results = result["results"]
    all_elapsed = result["elapsed"]

    lines = []
    lines.append("=" * 80)
    lines.append(f"  Fragment 유사도 검색 결과")
    lines.append(f"  검색 Fragment: {result['query_fragment']}")
    lines.append(f"  후보 분자 수: {result['total_candidates']}")
    lines.append(f"  사용 방법: {', '.join(methods_used)}")
    if "graph_stats" in result and result["graph_stats"]:
        gs = result["graph_stats"]
        lines.append(f"  [Graph RAG] 노드: {gs['nodes']}개 (분자: {gs['molecule_nodes']}, fragment: {gs['fragment_nodes']}), 엣지: {gs['edges']}개")
    lines.append("=" * 80)

    if len(methods_used) == 1:
        # 단일 방법 모드
        method = methods_used[0]
        lines.append(f"\n[{METHOD_DESCRIPTIONS[method]}] (소요시간: {all_elapsed.get(method, 0)}초)")
        lines.append("-" * 70)
        if method == "graph_rag":
            lines.append(f"{'순위':<6}{'SMILES':<40}{'결합':>8}{'Jaccard':>9}{'Tanimoto':>9}{'공유Frag':>9}")
            lines.append("-" * 81)
            for i, item in enumerate(all_results[method], 1):
                smi = item["smiles"]
                if len(smi) > 37:
                    smi = smi[:34] + "..."
                lines.append(
                    f"{i:<6}{smi:<40}{item['similarity_score']:>8.4f}"
                    f"{item.get('jaccard_score', 0):>9.4f}"
                    f"{item.get('tanimoto_score', 0):>9.4f}"
                    f"{item.get('shared_fragments', 0):>9}"
                )
        else:
            lines.append(f"{'순위':<6}{'SMILES':<50}{'유사도':>10}")
            lines.append("-" * 70)
            for i, item in enumerate(all_results[method], 1):
                smi = item["smiles"]
                if len(smi) > 47:
                    smi = smi[:44] + "..."
                lines.append(f"{i:<6}{smi:<50}{item['similarity_score']:>10.4f}")
        lines.append("-" * 70)
    else:
        # 비교 모드: 각 방법별 결과 + 비교 테이블
        for method in methods_used:
            if method not in all_results:
                continue
            lines.append(f"\n[{METHOD_DESCRIPTIONS[method]}] (소요시간: {all_elapsed.get(method, 0)}초)")
            lines.append("-" * 70)
            if method == "graph_rag":
                lines.append(f"{'순위':<6}{'SMILES':<40}{'결합':>8}{'Jaccard':>9}{'Tanimoto':>9}{'공유Frag':>9}")
                lines.append("-" * 81)
                for i, item in enumerate(all_results[method], 1):
                    smi = item["smiles"]
                    if len(smi) > 37:
                        smi = smi[:34] + "..."
                    lines.append(
                        f"{i:<6}{smi:<40}{item['similarity_score']:>8.4f}"
                        f"{item.get('jaccard_score', 0):>9.4f}"
                        f"{item.get('tanimoto_score', 0):>9.4f}"
                        f"{item.get('shared_fragments', 0):>9}"
                    )
            else:
                lines.append(f"{'순위':<6}{'SMILES':<50}{'유사도':>10}")
                lines.append("-" * 70)
                for i, item in enumerate(all_results[method], 1):
                    smi = item["smiles"]
                    if len(smi) > 47:
                        smi = smi[:44] + "..."
                    lines.append(f"{i:<6}{smi:<50}{item['similarity_score']:>10.4f}")
            lines.append("-" * 70)

        # 방법 간 비교 요약 테이블
        lines.append("\n" + "=" * 80)
        lines.append("  방법 간 비교 요약 (Top-1 ~ Top-3)")
        lines.append("=" * 80)

        # 헤더
        header = f"{'방법':<12}"
        for i in range(1, 4):
            header += f"{'Top-'+str(i)+' 유사도':>14}"
        header += f"{'소요시간(초)':>14}"
        lines.append(header)
        lines.append("-" * (12 + 14 * 4))

        for method in methods_used:
            if method not in all_results:
                continue
            row = f"{method:<12}"
            results_m = all_results[method]
            for i in range(3):
                if i < len(results_m):
                    row += f"{results_m[i]['similarity_score']:>14.4f}"
                else:
                    row += f"{'N/A':>14}"
            row += f"{all_elapsed[method]:>14.4f}"
            lines.append(row)

        lines.append("-" * (12 + 14 * 4))

        # Top-1 분자가 방법별로 동일한지 분석
        top1_smiles = {}
        for method in methods_used:
            if method in all_results and all_results[method]:
                top1_smiles[method] = all_results[method][0]["smiles"]

        unique_top1 = set(top1_smiles.values())
        if len(unique_top1) == 1:
            lines.append(f"\n* 모든 방법의 Top-1 분자가 동일합니다: {list(unique_top1)[0][:60]}")
        else:
            lines.append(f"\n* Top-1 분자가 방법별로 다릅니다 ({len(unique_top1)}종):")
            for method, smi in top1_smiles.items():
                smi_short = smi if len(smi) <= 50 else smi[:47] + "..."
                lines.append(f"  - {method}: {smi_short}")

    return {"output": "\n".join(lines)}


# --- 라우팅 함수 ---

def should_continue(state: AgentState) -> str:
    if state.get("error"):
        return "error"
    return "continue"


# --- 그래프 빌드 ---

def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("parse_input", parse_input)
    workflow.add_node("load_data", load_data)
    workflow.add_node("search_similar", search_similar)
    workflow.add_node("format_output", format_output)

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
    methods: list | None = None,
) -> str:
    graph = build_graph()

    initial_state: AgentState = {
        "fragment_smiles": fragment_smiles,
        "top_k": top_k,
        "substruct_filter": substruct_filter,
        "methods": methods,
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
    import argparse

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    parser = argparse.ArgumentParser(
        description="Fragment 유사도 검색 에이전트 (다중 방법 비교)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("fragment", help="검색할 fragment SMILES")
    parser.add_argument("--top-k", type=int, default=10, help="상위 결과 수 (기본: 10)")
    parser.add_argument(
        "--methods", nargs="+", default=None,
        choices=METHODS,
        help=(
            "사용할 유사도 방법 (복수 선택 가능, 기본: 전체)\n"
            "  morgan    : Morgan (ECFP4) Fingerprint\n"
            "  maccs     : MACCS Keys (166bit)\n"
            "  rdkit     : RDKit Fingerprint\n"
            "  atompair  : AtomPair Fingerprint\n"
            "  torsion   : Topological Torsion Fingerprint\n"
            "  mcs       : Maximum Common Substructure\n"
            "  graph_rag : Graph RAG (Knowledge Graph + BRICS)"
        ),
    )
    parser.add_argument(
        "--no-substruct-filter", action="store_true",
        help="부분구조 필터링을 비활성화하고 전체 분자 대상으로 검색",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Fragment 유사도 검색 에이전트 (LangGraph)")
    print("  데이터: QM8 dataset (21,787 molecules)")
    print("=" * 60)

    result = run_agent(
        fragment_smiles=args.fragment,
        top_k=args.top_k,
        substruct_filter=not args.no_substruct_filter,
        methods=args.methods,
    )
    print(result)
