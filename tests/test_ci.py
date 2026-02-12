def test_environment():
    """Verifierar att testmiljön fungerar."""
    assert True

def test_imports():
    """Verifierar att vi kan importera pandas (viktigaste beroendet)."""
    import pandas as pd
    assert pd.__version__ is not None
