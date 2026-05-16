"""docs_ops.py tag-normalize 회귀 가드 (v0.47.6 — FR-X2).

검증:
- normalize_tag: 결정적 변환 (camelCase·언더바·대문자)
- normalize_tag: 한글 포함 시 None 반환 (자동 변환 거부)
- cmd_tag_normalize: dry-run 모드 (--apply 없으면 파일 미수정)
- cmd_tag_normalize: --apply 모드 frontmatter 갱신
- cmd_tag_normalize: 한글 포함 파일은 적용 skip
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _load_docs_ops():
    spec = importlib.util.spec_from_file_location("docs_ops", SCRIPTS_DIR / "docs_ops.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def docs_ops():
    return _load_docs_ops()


@pytest.mark.tag
class TestNormalizeTag:
    def test_already_valid(self, docs_ops):
        assert docs_ops.normalize_tag("harness-upgrade") == ("harness-upgrade", "이미 정합")

    def test_camelcase_split(self, docs_ops):
        new, _ = docs_ops.normalize_tag("ArtistMatcher")
        assert new == "artist-matcher"

    def test_camelcase_with_lowercase_start(self, docs_ops):
        new, _ = docs_ops.normalize_tag("csoonId")
        assert new == "csoon-id"

    def test_underscore_to_hyphen(self, docs_ops):
        new, _ = docs_ops.normalize_tag("task_groups")
        assert new == "task-groups"

    def test_uppercase_only(self, docs_ops):
        new, _ = docs_ops.normalize_tag("REVIEW")
        assert new == "review"

    def test_hangul_rejected(self, docs_ops):
        new, reason = docs_ops.normalize_tag("가격재수집")
        assert new is None
        assert "한글" in reason

    def test_hangul_mixed_rejected(self, docs_ops):
        new, _ = docs_ops.normalize_tag("melon_가격")
        assert new is None

    def test_consecutive_separators(self, docs_ops):
        new, _ = docs_ops.normalize_tag("a__b--c")
        assert new == "a-b-c"

    def test_leading_trailing_hyphen_strip(self, docs_ops):
        new, _ = docs_ops.normalize_tag("_review_")
        assert new == "review"

    def test_dot_to_hyphen(self, docs_ops):
        new, _ = docs_ops.normalize_tag("v1.2")
        assert new == "v1-2"


@pytest.mark.tag
class TestCmdTagNormalize:
    def _write_doc(self, dir_path: Path, name: str, tags: str) -> Path:
        p = dir_path / name
        p.write_text(
            "---\n"
            "title: 테스트\n"
            "domain: harness\n"
            "problem: P7\n"
            "s: [S7]\n"
            f"tags: {tags}\n"
            "status: in-progress\n"
            "created: 2026-05-15\n"
            "---\n\n"
            "본문\n",
            encoding="utf-8",
        )
        return p

    def test_dry_run_no_modification(self, docs_ops, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        docs = tmp_path / "docs" / "decisions"
        docs.mkdir(parents=True)
        p = self._write_doc(docs, "hn_x.md", "[ArtistMatcher, task_groups]")
        before = p.read_text(encoding="utf-8")
        rc = docs_ops.cmd_tag_normalize([str(p)])
        assert rc == 0
        assert p.read_text(encoding="utf-8") == before  # dry-run = 변경 없음

    def test_apply_modifies_file(self, docs_ops, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        docs = tmp_path / "docs" / "decisions"
        docs.mkdir(parents=True)
        p = self._write_doc(docs, "hn_x.md", "[ArtistMatcher, task_groups]")
        rc = docs_ops.cmd_tag_normalize([str(p), "--apply"])
        assert rc == 0
        new_text = p.read_text(encoding="utf-8")
        assert "tags: [artist-matcher, task-groups]" in new_text
        assert "updated:" in new_text

    def test_hangul_file_skipped_on_apply(self, docs_ops, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        docs = tmp_path / "docs" / "decisions"
        docs.mkdir(parents=True)
        p = self._write_doc(docs, "hn_x.md", "[melon, 가격재수집]")
        before = p.read_text(encoding="utf-8")
        rc = docs_ops.cmd_tag_normalize([str(p), "--apply"])
        assert rc == 0
        # 한글 포함이라 자동 적용 skip — 본문 보존
        assert p.read_text(encoding="utf-8") == before

    def test_no_violation_noop(self, docs_ops, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        docs = tmp_path / "docs" / "decisions"
        docs.mkdir(parents=True)
        p = self._write_doc(docs, "hn_x.md", "[clean, valid-tag]")
        before = p.read_text(encoding="utf-8")
        rc = docs_ops.cmd_tag_normalize([str(p), "--apply"])
        assert rc == 0
        assert p.read_text(encoding="utf-8") == before  # 정합 tag = 변경 없음

    def test_duplicate_normalize_dedup(self, docs_ops, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        docs = tmp_path / "docs" / "decisions"
        docs.mkdir(parents=True)
        # Review·REVIEW·review가 동일 'review'로 정규화 — 중복 제거 확인
        p = self._write_doc(docs, "hn_x.md", "[Review, REVIEW, commit]")
        rc = docs_ops.cmd_tag_normalize([str(p), "--apply"])
        assert rc == 0
        new_text = p.read_text(encoding="utf-8")
        assert "tags: [review, commit]" in new_text
