"""pytest 설정 — marker 등록."""


def pytest_configure(config):
    for m in ("secret", "gate", "stage", "enoent", "docs_ops"):
        config.addinivalue_line("markers", f"{m}: {m} 영역 테스트")
