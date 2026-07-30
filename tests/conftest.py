def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "contract_fixture: contract-only fixture evidence; never native runtime evidence",
    )
