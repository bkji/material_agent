# 작업지시서
사용자 input: fragement의 smiles 
출력:
- 1. 전체 구조의 smiles 
- 2. 유사도 score (유사도 score의 기준은 니가 정해줘.)

유사도 검색하는 방식의 종류와 장/단점
유사도 검색하는 방식 중 graph rag에 관심이 있는데, 장/단점 비교
재료분야에서 최근 기술 경향

# ./data/qm8.csv의 구조
1번 열 정보인 smiles만 사용

smiles는 core + fragement로 구성되어 있고, fragement만으로 유사한 순으로 검색하는 agent를 개발하고 싶다.


# 사용언어
python, 
langgraph

# 제약사항
현재는 data가 csv파일로 가지고 있으나, 이후에는 DB에 적재예정임. 
1000만건 수준.


