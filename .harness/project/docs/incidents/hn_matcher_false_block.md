---

title: 광역 매처 오탐으로 무관한 명령 차단 + harness-upgrade가 README 덮어쓸 위험
domain: harness
tags: [hook, matcher, false-positive, harness-upgrade, readme, downstream]
problem: P3
s: [S3]
symptom-keywords:
  - "PreToolUse:Bash hook error"
  - "git commit -n 금지"
  - "merge-file 차단"
  - "README 덮어씌우면 안되잖아"
  - "harness-upstream main:.claude 차단"
  - "다운스트림 README 사라짐"
relates-to:
  - path: ./hn_bash_n_flag_overblock.md
    rel: extends
status: completed
created: 2026-04-19
updated: 2026-04-19
---

# 광역 매처 오탐 + README 덮어쓰기 위험

## 증상 1 — 3-way merge 명령이 `git commit -n` 매처에 오탐 차단

다운스트림 프로젝트 v0.7.0 업그레이드 중 다음 명령이 차단됨:

```bash
TMPDIR=$(mktemp -d)
MSYS_NO_PATHCONV=1 git show 3468fb5:.claude/settings.json > "$TMPDIR/base"
MSYS_NO_PATHCONV=1 git show harness-upstream/main:.claude/settings.json > "$TMPDIR/theirs"
cp .claude/settings.json "$TMPDIR/ours"
git merge-file "$TMPDIR/ours" "$TMPDIR/base" "$TMPDIR/theirs"
echo "merge exit: $?"
cp "$TMPDIR/ours" .claude/settings.json
rm -rf "$TMPDIR"
node -e "JSON.parse(require('fs').readFileSync('.claude/settings.json','utf8')); console.log('JSON OK')"
```

차단 메시지:
```
PreToolUse:Bash hook error: [echo '❌ git commit -n 금지.' && exit 2]: No stderr output
```

**명령에 `git commit -n`이 없는데 차단됨.** 매칭된 구버전 매처 후보:
```json
{ "if": "Bash(git commit -n)" }
{ "if": "Bash(git commit -n *)" }
{ "if": "Bash(git commit -m * -n*)" }
```

추정 원인 (공식 문서 경고 "argument constraint는 fragile"):
- 매처 `*` 와일드카드가 공백 포함 모든 문자 매칭
- compound 명령(`;` 나 multi-line)에서 일부 토큰이 매칭되는 것으로 추정
- 실제 어느 매처가 hit했는지 stderr가 비어 확인 불가

## 증상 2 — harness-upgrade가 README를 덮어쓸 수 있음

사용자 지적: "다운스트림에서 Readme를 덮어씌우면 안되잖아?"

확인 결과:
- `harness-upgrade` SKILL.md의 "사용자 전용" 리스트에 `README.md` 빠져 있었음
- "기타" 카테고리가 3-way merge로 들어가 README도 병합 시도 가능

## 근본 원인 (공통)

**광역 매처 패턴이 근본적으로 fragile.**

공식 문서 (https://code.claude.com/docs/en/permissions) 명시 경고:
> "Bash permission patterns that try to constrain command arguments are
>  fragile."

`Bash(... -X ...)` 같은 argument constraint 매처는:
- 단일 `*`가 공백 포함 모든 문자 매칭 → 의도 외 매칭
- compound 명령·multi-line·인용 안 내용 모두 우연 매칭 가능
- stderr 비어 있어 디버깅 불가

사용자 전용 파일 리스트도 같은 패턴의 실수 — "대부분 괜찮을 것"으로
빠뜨리면 침해 발생.

## 해결 (v0.7.0 — 본 커밋에 반영)

### 증상 1 해결

단일 PreToolUse hook 스크립트 `bash-guard.sh`로 통합. settings.json의
`Bash(... -X ...)` 매처 8개 → **Bash tool 전체 matcher 1개**:

```json
{
  "matcher": "Bash",
  "hooks": [{ "type": "command", "command": "bash .claude/scripts/bash-guard.sh" }]
}
```

`bash-guard.sh`는 stdin으로 명령 JSON을 받아 jq로 파싱 후 토큰 단위
검증:
- `git commit`으로 시작하는 경우에만 `-n` 단독 인자 차단
- `--no-verify`도 토큰 경계 체크 (substring 매칭 X)
- 다른 명령의 `-n`·`bash -n`·`head -n` 등 완전 통과

격리 검증: 13/13 통과 (`test-bash-guard.sh`).

### 증상 2 해결

`harness-upgrade/SKILL.md`의 "사용자 전용" 리스트 확장:
- `README.md`, `CHANGELOG.md`, `.gitignore`
- `docs/decisions/*`, `docs/incidents/*`, `docs/WIP/*`
- `docs/guides/*` (단 `project_kickoff_sample.md` 제외)

추가 "사용자 전용 파일 처리 규칙 (강행)" 섹션 — 금지 행동 명시:
- "starter 버전 추가" X
- "diff 있으니 3-way merge 제안" X
- "사용자 confirm 받고 덮어쓰기" X (confirm 자체 안 띄움)

## 재발 방지

1. **argument-constraint 매처 전면 금지** — `rules/staging.md` 또는
   `docs/guides/` 가이드로 승격 검토.
2. 새 hook 차단 로직은 반드시 jq + 토큰 분리로 (공식 권장 패턴).
3. "사용자 전용" 리스트는 starter 관리 파일의 **화이트리스트**, 그 외
   전부 건드리지 않는 쪽이 안전 (현재는 블랙리스트 방식 — 역전 검토).
4. harness-upgrade는 업그레이드 대상 파일을 git diff로 검출할 때
   반드시 화이트리스트에 있는 파일만 처리.

## 미해결

- 증상 1 차단된 정확한 매처를 stderr 부재로 확정 못 함. v0.7.0 적용
  후 재발 없으므로 원인 규명 가치 낮음.
- Claude Code matcher 엔진의 내부 동작(substring vs glob vs regex)은
  공식 문서가 "prefix + glob" 명시하지만 실측 오탐 패턴이 이와 다르게
  보임. Anthropic 이슈 등록 검토 가능.

## 다운스트림 조치

v0.7.0으로 업그레이드하면 자동 해결. 현재 다운스트림 프로젝트에서
이미 settings.json + bash-guard.sh 병합 완료. 다음 Bash 명령부터는
본 오탐 재발 없음 (사용자 보고).
