---
name: harness-sync
description: 클론한 하네스 프로젝트의 환경을 동기화한다. 의존성 설치 + 스크립트 권한 설정 + 하네스 무결성 검사. 최초 셋업 머신에서는 실행할 필요 없음. 다른 머신에 클론 직후 한 번만 실행. "환경 셋업 안 됨", "클론했는데 안 돌아감", "harness-sync" 요청 시 사용.
---

# harness-sync 스킬

**한 번만 돌리는 스킬.** 클론한 하네스 프로젝트에서 개발 환경을 실제 설치/동기화한다.

## 전제

- 이 프로젝트는 `h-setup.sh`로 하네스가 이미 셋업되어 있어야 한다 (`.claude/HARNESS.json` 존재).
- `CLAUDE.md`의 `## 환경` 섹션이 채워져 있어야 한다 (패키지 매니저, 빌드/실행 명령어 등).
- 최초 셋업 머신에서는 **실행하지 않는다.** 이미 환경이 구성되어 있음.

## 멱등성 — 핵심 제약

**이 스킬은 기계당 한 번만 유의미하게 실행된다.**
`.claude/.env_synced` 마커 파일을 기준으로 판단:

- 마커 존재 → "이미 sync됨" 알리고 종료. 재실행 금지.
- 마커 없음 → 전체 sync 흐름 진행 후, 마커 생성.

마커 내용:
```
synced_at: 2026-04-08T12:34:56Z
host: <hostname>
profile: <HARNESS.json의 profile>
```

사용자가 강제 재실행을 원하면 마커를 삭제하라고 안내하고, Claude가 임의로 삭제하지 않는다.

## 흐름

### Step 1. 사전 점검

- [ ] `.claude/HARNESS.json`이 있는가? 없으면 "이 프로젝트는 하네스 셋업이 안 되어 있음" 보고 후 중단.
- [ ] `CLAUDE.md`가 있는가? 없으면 중단.
- [ ] `.claude/.env_synced` 마커가 있는가? 있으면:
  ```
  ✅ 이 머신은 이미 sync되었습니다 ([synced_at] 기준).
  재동기화가 필요하면 .claude/.env_synced를 삭제하고 다시 실행하세요.
  ```
  그리고 종료.

### Step 2. CLAUDE.md 환경 섹션 파싱

`## 환경` 섹션을 읽어 key-value 추출:

```
- 패키지 매니저: pnpm
- 빌드/실행 명령어: pnpm dev
- 배포 방식: vercel
- 의존 도구: node@20, docker
```

파싱 결과를 사용자에게 표로 보여주고 확인받는다. 비어 있는 항목이 있으면 "harness-init을 먼저 돌려야 한다"고 보고.

### Step 3. 의존성 설치

**패키지 매니저별 명령 매핑** (흔한 것만):

| 패키지 매니저 | 설치 명령 | lock 파일 |
|---------------|----------|----------|
| npm | `npm install` | package-lock.json |
| pnpm | `pnpm install` | pnpm-lock.yaml |
| yarn | `yarn install` | yarn.lock |
| bun | `bun install` | bun.lockb |
| pip | `pip install -r requirements.txt` | requirements.txt |
| poetry | `poetry install` | poetry.lock |
| uv | `uv sync` | uv.lock |
| cargo | `cargo build` | Cargo.lock |
| go | `go mod download` | go.sum |

- lock 파일 존재 확인 → 없으면 "lock 파일 없음, 의존성 설치 건너뜀" 경고.
- 명령 실행 전 사용자에게 **확인받는다.** "다음 명령을 실행하려 합니다: `pnpm install`. 진행할까요?"
- 실행. 실패 시 **추측 금지**, 에러 그대로 보고하고 중단.

### Step 4. 시스템 도구 확인

`## 환경`의 `의존 도구:` 항목(있으면) 각각에 대해:

- `command -v <tool>` 또는 `<tool> --version`으로 존재 확인.
- 누락된 도구는 **리스트로 보고만** 한다. 자동 설치하지 않는다(OS별 상이, sudo 위험).
- 사용자에게 설치 방법을 안내(공식 사이트 링크 정도).

### Step 5. 스크립트 권한 설정 + starter hook 설치

`.claude/scripts/*.sh`에 실행 권한 부여:

```bash
chmod +x .claude/scripts/*.sh 2>/dev/null || true
```

Windows(Git Bash 등)에서는 no-op이 되어도 무방. 에러 무시.

`is_starter: true`인 repo라면 git hook도 설치:

```bash
bash .claude/scripts/install-starter-hooks.sh
```

다운스트림(`is_starter: false`)은 스크립트가 즉시 exit — 무해.

### Step 6. 하네스 무결성 검사

`.claude/HARNESS.json`의 `skills` 목록과 실제 `.claude/skills/` 하위 디렉토리를 비교.

- 누락된 스킬이 있으면 경고 (하네스 파일이 클론 과정에서 빠졌을 가능성).
- 추가 스킬이 있으면 정보만 출력 (사용자가 `--add`로 추가했을 수 있음).

### Step 7. 마커 생성 및 완료 보고

```bash
cat > .claude/.env_synced <<EOF
synced_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
host: $(hostname)
profile: <HARNESS.json에서 읽은 값>
EOF
```

완료 메시지:

```
✅ harness-sync 완료

설치된 것:
  - 의존성: [패키지 매니저 + 설치된 개수 또는 "skipped"]
  - 시스템 도구: [OK / 누락 목록]
  - 스크립트 권한: 설정됨
  - 하네스 스킬: [프로파일] / N개 확인

📄 .claude/.env_synced 생성됨. 재실행하지 않아도 됩니다.

다음: docs/WIP/에서 진행 중인 작업을 확인하세요.
```

## .gitignore 권고

`.claude/.env_synced`는 **머신별 상태**이므로 `.gitignore`에 추가 권고:

```
# 하네스 — 머신별 동기화 마커
.claude/.env_synced
```

스킬은 .gitignore 존재 여부를 확인하고, 없으면 사용자에게 추가 제안(강제하지 않음).

## 주의

- 이 스킬은 **환경을 건드리는** 스킬이다. 확인 없이 설치 명령을 실행하지 않는다.
- `sudo`가 필요한 작업은 절대 시도하지 않는다. 사용자에게 수동 실행을 요청.
- 3회 시도해도 해결 안 되는 문제는 사용자에게 보고. 추측 금지.
- 이 스킬은 `CLAUDE.md ## 환경`이 소스 오브 트루스라는 전제 위에 작동한다. 파싱 실패 시 harness-init 재실행을 권고.
