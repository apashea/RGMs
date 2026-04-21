from tests.helpers.matlab_engine import eng


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: longer DEM integration oracles (larger GDP.T / PDP.O window)",
    )


__all__ = ["eng"]
