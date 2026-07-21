# harness-starter

공유 Harness runtime을 프로젝트에 연결하기 위한 얇은 binding 진입점과 독립 실행 계약을 제공한다.

- 구현 기준: Git `99b72ab`, package `0.1.1`
- Python: 정확히 `3.11`
- runtime dependencies: 없음

## 권한 경계

프로젝트의 지속 가능한 결정, 운영 지식, 문서 체계의 canonical authority는 `harness-brain`이다. 이 저장소는 실행 코드와 기계 검증 가능한 runtime·binding·receipt 계약을 유지한다. 프로젝트별 adapter는 `adapters/`에 둘 수 있지만 독립 runtime은 Hermes core, live gateway, 저장소 내부 실행 state에 의존하지 않는다.

이 저장소 자체는 live deployment, 전체 C1 closure, provider mutation 실행, 특정 profile orchestration이 준비되었다고 주장하지 않는다.

## 현재 제공 범위

### Minimal project binding

`h-setup.sh`는 Python 3.11을 확인한 뒤 `harness-project-binding` CLI를 실행한다.

- `inspect`: 현재 binding 상태와 drift를 읽는다.
- `plan`: 변경 없이 desired-state 작업을 계산한다.
- `apply`: tool-managed 파일만 생성·갱신하고 unmanaged 충돌은 덮어쓰지 않는다.
- `reconcile`: ownership manifest와 digest가 일치하는 legacy 파일만 제거 후보로 다룬다.

`apply`의 관리 범위는 다음 네 파일이다.

- `.harness/project-binding.json`
- `.harness/runtime.lock.json`
- `.harness/bin/harness-binding`
- `.harness/bin/harness-sandbox-run`

Binding에는 Git source snapshot, provider target, typed capability graph, clean-worktree·external-state 요구사항이 기록된다. 비밀 값은 binding 입력으로 다루지 않는다.

### Typed guided capabilities

`harness-guided-capability`는 임의 shell command가 아니라 binding에 선언된 capability ID만 받는다.

- `discovery`·`status`: 완전한 target identity와 외부 `--state-dir`를 요구하며, 허용된 provider read-only 조회만 sandbox에서 실행한다.
- `plan`: source snapshot과 binding scope를 묶은 digest를 만든다.
- `apply`: runtime contract를 거부하고, scope·plan digest가 일치하는 approval receipt와 capability별 executor 및 유효한 execution receipt가 모두 있어야 성공한다.

현재 bundled CLI는 apply executor를 제공하지 않으므로 mutation은 fail closed된다. 따라서 deploy, migration, privileged data mutation, workflow publish를 수행한다고 해석하면 안 된다.

### Isolated receipt runtime

`harness-runtime`은 표준 라이브러리만 사용하는 독립 package다.

- `run`: 명시한 clean Git worktree에서 제한된 환경으로 한 명령을 실행한다.
- `readback`: terminal projection, 2-event journal, execution metadata와 artifact digest를 재검증한다.
- `analysis-input`: 같은 검증 뒤 bounded stdout·stderr만 제공한다.
- `schema`: versioned execution-receipt schema를 출력한다.

모든 producer·consumer state에는 저장소와 겹치지 않는 명시적 `HARNESS_STATE_DIR`가 필요하다. Hermes home, gateway state, caller 환경, 저장소 내부 state로 fallback하지 않는다. 상세 계약은 `docs/build-and-state-contract.md`에 있다.

### Gateway ingress

`.hermes/plugins/harness-gateway`는 Hermes의 project-bound Gateway event에만 ingress 계약을 적용한다. 현재 plugin hook은 다음을 수행한다.

1. Gateway project binding으로 project cwd를 해석한다.
2. Git worktree root와 `manifest.yml` 경계를 검증한다.
3. event·manifest hash·baseline worktree evidence를 canonical ingress packet으로 만든다.
4. receipt를 `received → intake-ready → route → running → terminal`로 연결한다.
5. binding 또는 intake가 hold이면 agent 호출 전에 중단하고, unbound event는 변경 없이 통과시킨다.

이는 저장소에 구현된 ingress transport 계약 설명이며 live gateway 배포 상태를 의미하지 않는다.

## 빠른 시작

요구사항은 Python `3.11`과 `uv`다. package metadata의 `requires-python`은 `==3.11.*`이며 runtime dependency 목록은 비어 있다.

```bash
uv sync --locked --extra test

# 읽기 전용 상태 확인
bash h-setup.sh inspect /path/to/project

# minimal binding 변경 계획
bash h-setup.sh plan \
  --project-id example \
  --protected-branch main \
  --railway-service app \
  /path/to/project

# schema 확인
uv run --locked harness-runtime schema
```

계획을 검토한 뒤에만 같은 인자로 `plan`을 `apply`로 바꾼다. Binding이 생성된 프로젝트에서는 capability plan을 읽을 수 있다.

```bash
uv run --locked harness-guided-capability plan railway.deploy /path/to/project
```

Receipt runtime의 실제 실행에는 외부 state와 clean worktree root가 필요하다.

```bash
state_dir="$(mktemp -d)"
body_file="$(mktemp)"
python_311="$(command -v python3.11)"
printf 'smoke\n' > "$body_file"

HARNESS_STATE_DIR="$state_dir" uv run --locked harness-runtime run \
  --case smoke-001 \
  --consumer local-check \
  --body-file "$body_file" \
  --worktree-cwd /path/to/clean/git/worktree \
  -- "$python_311" -c 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())'

HARNESS_STATE_DIR="$state_dir" uv run --locked harness-runtime readback \
  --case smoke-001 \
  --consumer local-check
```

## 소스 안내

- `manifest.yml`: project entry와 CPS routing boundary
- `runtime/harness_runtime/project_binding.py`: binding desired state와 capability graph
- `runtime/harness_runtime/guided_capability.py`: typed discovery·plan·status·apply gate
- `runtime/harness_runtime/runtime.py`: isolated execution receipt producer·consumer
- `runtime/harness_runtime/ingress.py`: bound event intake, canonical packet, lifecycle receipt
- `.hermes/plugins/harness-gateway/`: Gateway hook adapter
- `contracts/`: versioned machine-readable contracts
- `adapters/`: project-facing adapter boundary

## 검증

독립 runtime test extra로 실행되는 focused 계약 검증:

```bash
uv run --locked pytest \
  tests/runtime/test_ingress_transport.py \
  tests/runtime/test_project_binding.py \
  tests/runtime/test_guided_capability.py \
  tests/runtime/test_runtime_contract.py
```

Gateway plugin integration은 Hermes core checkout과 그 test environment를 사용한다. 현재 fixture 기준 경로와 실행 명령은 다음과 같다.

```bash
HERMES_AGENT_ROOT=/Users/kann/.hermes/hermes-agent
PYTHONPATH="$PWD/runtime:$PWD:$HERMES_AGENT_ROOT" \
  "$HERMES_AGENT_ROOT/.venv/bin/python" -m pytest -q \
  tests/runtime/test_gateway_plugin_integration.py
```