---
name: Windows 환경에서 Write tool에 POSIX 경로 금지
description: Git Bash `/tmp` 같은 POSIX 경로를 Write/Edit/Read tool에 넘기면 실패하거나 엉뚱한 위치에 쓰인다. Bash tool만 POSIX 경로 해석.
type: feedback
---

Windows 환경(Git Bash)에서 Claude Code의 파일 tool(Write/Edit/Read)은
**Windows 네이티브 경로만** 수용한다. `/tmp/foo.sh` 같은 POSIX 경로를
넘기면 `No such file or directory` 실패 또는 예상치 못한 위치에 파일
생성.

**Why**: Bash tool은 Git Bash shim을 거쳐 `/tmp` → `C:\Users\<user>\AppData\Local\Temp`
로 자동 치환되지만, Write/Edit/Read tool은 Windows 네이티브 FS API를
직접 호출해 POSIX 경로를 해석 못 함. 2026-04-21 memory 재설계 벤치
작업에서 `/tmp/cache-bench/bench.sh`를 Write tool로 생성 시도 →
`No such file or directory` 발생. `cygpath -w /tmp` 확인 결과 실제
경로는 `C:\Users\Kann\AppData\Local\Temp`였음. Bash tool의 heredoc으로
우회 성공.

**How to apply**:
- Windows + Git Bash 환경에서 임시 파일을 만들 때
  - ❌ Write tool에 `/tmp/foo.sh` 금지
  - ✅ Write tool에는 `C:\Users\...\AppData\Local\Temp\foo.sh` 같은 네이티브
    경로, 또는 프로젝트 내부 경로 사용
  - ✅ 임시 파일이 shell 스크립트라면 Bash tool heredoc (`cat > /tmp/foo.sh << 'EOF'`)
    사용 — Bash 내부에서는 POSIX 경로 정상 동작
- 경로 문제를 "재시도"로 넘어가지 말 것. 원인(환경) 확인 → 규약 교정 →
  이후 재발 차단.
- 이 규칙은 Windows 전용. Linux/macOS에서는 `/tmp`가 네이티브이므로 모든
  tool에서 그대로 사용 가능.
