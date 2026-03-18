# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a materials science / computational chemistry project ("material_agent"). It currently contains quantum chemistry datasets and is in early stages.

## Data

- `data/0_qm8_260318/qm8.csv` — QM8 dataset (~21,787 molecules). Columns: SMILES string, then excited-state energies (E1, E2) and oscillator strengths (f1, f2) computed with CC2, PBE0, and CAM-B3LYP methods. Note: PBE0 columns appear twice (likely DFT/TDDFT distinction).

---
# VM npm 패키지 사용 가이드

## 핵심 원칙

**VM에서 `npm install`은 절대 시도하지 않는다.** 프록시 allowlist에 의해 항상 실패한다. 다른 우회 설치 방법(curl, wget 등)도 시도하지 않는다.

## 1. 프리설치 패키지 (우선 사용)

아래 패키지들이 `/usr/local/lib/node_modules_global/lib/node_modules/`에 프리설치되어 있다.

- `docx` (v9.5.3) — Word 문서 생성 (ESM only)
- `pptxgenjs` — PowerPoint 생성
- `pdf-lib` — PDF 생성/편집
- `pdfjs-dist` — PDF 읽기/파싱
- `sharp` — 이미지 처리
- `marked` — Markdown → HTML
- `markdown-toc` — Markdown 목차 생성
- `graphviz` — 그래프 시각화
- `typescript` / `tsx` / `ts-node` — TypeScript
- `@anthropic-ai` — Anthropic SDK

### 세션 시작 시 심볼릭 링크

```bash
mkdir -p node_modules && for pkg in /usr/local/lib/node_modules_global/lib/node_modules/*/; do ln -sf "$pkg" "node_modules/$(basename "$pkg")"; done
```

### 사용 시 주의

- `docx`, `marked` 등 ESM 패키지는 `import`를 사용 (`require()` 불가)
- `.mjs` 파일이나 `--input-type=module` 플래그를 사용할 것

## 2. 프리설치에 없는 패키지가 필요할 때

**VM에서 직접 설치를 시도하지 않는다.** `npm install`, `curl`, `wget` 등 어떤 방법으로도 시도하지 않는다.

대신 유저에게 현재 선택된 폴더에서 직접 설치하도록 안내한다.

### 유저에게 안내할 내용

```bash
npm install <패키지명>
```

- 유저의 로컬 터미널에서, Cowork에 선택된 폴더 안에서 위 명령 실행
- 설치 완료되면 알려달라고 요청

### VM에서 참조하는 방법

워크스페이스 마운트 경로는 세션마다 다르므로 하드코딩하지 않는다. 아래 방법으로 동적 탐색한다.

```bash
# 워크스페이스 경로 찾기 (uploads 제외)
WS=$(find "$HOME/mnt" -maxdepth 1 -mindepth 1 -type d ! -name uploads | head -1)
```

```js
// CommonJS
const path = require('path');
const fs = require('fs');
const wsDir = fs.readdirSync(process.env.HOME + '/mnt')
  .find(d => d !== 'uploads' && d !== '.skills');
const pkg = require(path.join(process.env.HOME, 'mnt', wsDir, 'node_modules', '<패키지명>'));

// ESM — 심볼릭 링크 후 import 가능
```

### 주의사항

- 워크스페이스의 `node_modules/`는 유저 폴더에 남으므로, 작업 완료 후 불필요하면 정리 안내
- 프리설치 패키지가 있으면 반드시 프리설치 우선 사용
