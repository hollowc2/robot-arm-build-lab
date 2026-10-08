from copy import deepcopy

import pytest


@pytest.fixture(scope="session")
def _master_assembly():
    from models.master_assembly import build_model

    return build_model()


@pytest.fixture
def master_assembly(_master_assembly):
    """Build once, but isolate each test's shapes and assembly hierarchy."""
    return deepcopy(_master_assembly)
