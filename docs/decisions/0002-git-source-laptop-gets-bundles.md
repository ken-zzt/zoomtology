---
type: decision
status: active
created: 2026-10-28
updated: 2026-10-28
last_verified: 2026-10-28
sources:
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-챗지피티.pdf
  - docs/research/사내 온톨로지(지식그래프) 구축 가이드-클로드.pdf
  - Service/kenny-agents/docs/90-decisions/0020-code-confidentiality-rules.md
tags: [decision, git, deploy, kenny]
related_to:
  - 0001-property-graph-in-prism-mysql.md
  - 0003-metadata-only.md
---

# 0002. Git 저장소(zoomtology)가 원본이고 그래프 DB 는 재생성 가능한 산출물이다. 노트북(mbp2017)엔 번들만 보낸다

| 항목 | 값 |
|---|---|
| 상태 | 채택 |
| 결정일 | 2026-10-28 |
| 결정자 | Ken |

## 배경

보고서들은 한목소리로 "Git 이 진짜 원본, 그래프 DB 는 언제든 Git 에서 다시 만드는 결과물" 을 권했다(C 4.2 ④, O "Git 을 중심으로 한 협업 절차", G1 4.1 "Data-as-Code").
이유: 변경 이력·검토·롤백이 공짜로 생기고, 무료 그래프 DB 의 백업 약점이 상쇄된다.

줌줌투어엔 추가 제약이 있다. kenny 는 mbp2017 의 `Service/` 아래를 통째로 "서비스의 사실" 로 읽는다.
kenny-agents·hermes-personal 처럼 **에이전트 자신에 관한 설계·계획 문서는 그 트리에 두지 않는다** 는 운영 규칙이 있고,
2026-10-26 에 zoomtology 도 같은 취급("mbp2017 에 두지 않는다")으로 정했다.
그런데 그래프는 kenny 가 써야 하므로, 데이터는 노트북에 가야 한다.

## 검토한 선택지

### A. zoomtology 저장소를 mbp2017 에도 clone 하고 거기서 빌드
- 장점: 노트북이 스스로 최신 그래프를 만든다(매시간 repo-pull 뒤에 붙일 수 있다)
- 단점: 설계 문서·ADR·큐레이션 YAML·추출기 코드가 kenny 의 증거 트리나 code-guard 인덱스에 섞인다. 관리 대상(갱신 경로·무결성 점검)이 하나 는다. 원본이 두 곳이 된다

### B. 원본은 Ken 의 Mac 의 zoomtology 에만, **노트북엔 빌드 산출물(번들)만** Prism 배포 경로로 전달 (채택)
- 장점: kenny 의 증거 트리가 깨끗하다. 노트북엔 "그래프 데이터" 만 있고 관리할 코드가 없다. 빌드는 메인 Mac 한 곳
- 단점: 갱신은 Ken 의 Mac 에서 스크립트를 돌려야 한다(1차는 수동). 노트북 그래프의 신선도 = 마지막 배포 시점

### C. zoomzoom-services(문서 허브) 안에 둔다
- 장점: 이미 kenny 가 읽고 매시간 당기는 저장소
- 단점: 문서 허브는 code-guard 의 화이트리스트(`DOC_REPOS`)다. 그래프 데이터가 코드 조각을 담으면 가드가 약해진다. 허브의 "1회성 산출물 금지" 규칙과도 어긋난다

## 결정

**B 를 선택한다.** 저장소 구성:
- 원본: `Service/zoomtology` (GitHub private `ken-zzt/zoomtology`) — `ontology/`, `extractors/`, `curated/`, `state/`, `build/latest/{manifest.json,report.md}`, `docs/`.
- 산출물: `build/dist/zoomtology-<version>.tar.gz` (gitignore; `bundle/<version>` 태그로 재현). `scripts/deploy-laptop.sh` 가 `scp` 로 노트북 `~/apps/agent-prism/var/kg/` 에 올리고 Prism 로더가 적재한다.
- 같은 입력이면 번들은 바이트 동일(정렬된 JSONL)이다 — 재현성 테스트의 기준.

## 결과

- `zoomtology` 는 `zoomzoom-services/tools/repos.tsv`·워크스페이스 저장소 지도·`docs/10-services/` 에 넣지 않는다(기존 결정 유지). 허브에 한 줄 언급할지는 4단계에서 다시 본다.
- 번들 보관(태그만 / GitHub release / 정렬 JSONL 커밋)은 5단계에서 결정한다.
- kenny 가 스스로 재빌드해야 하는 날이 오면 `Service/` **밖**(예: `~/apps/zoomtology`)에 clone 하는 방식으로 A 를 재검토한다. 새 ADR 로 남긴다.
