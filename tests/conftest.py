import pytest

import config


@pytest.fixture(autouse=True)
def salida_temporal(tmp_path, monkeypatch):
    """Redirige output/ a un directorio temporal para que los tests no escriban en el proyecto."""
    salida = tmp_path / 'output'
    monkeypatch.setattr(config, 'OUTPUT_DIR', salida)
    return salida
