from pyskills import models


def test_models_public_exports() -> None:
    assert hasattr(models, "Skill")
    assert hasattr(models, "ParsedSource")
    assert hasattr(models, "InstallResult")
