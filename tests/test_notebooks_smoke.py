"""Execute pedagogical notebooks with nbclient (offline, FakeClient path)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))


@pytest.fixture(scope="session")
def jupyter_data_dir(tmp_path_factory):
    """Register a kernelspec that points at this interpreter (no user install)."""
    data = tmp_path_factory.mktemp("jupyter_data")
    spec_dir = data / "kernels" / "python3"
    spec_dir.mkdir(parents=True)
    (spec_dir / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "Python 3 (multilogue tests)",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )
    os.environ["JUPYTER_DATA_DIR"] = str(data)
    return data


@pytest.mark.parametrize("nb_path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_executes(nb_path: Path, tmp_path, monkeypatch, jupyter_data_dir):
    pytest.importorskip("matplotlib")
    pytest.importorskip("ipykernel")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MULTILOGUE_ACCESS_YES", "1")
    monkeypatch.setenv("MULTILOGUE_DATAPATH", str(tmp_path / "cache"))
    monkeypatch.setenv("JUPYTER_DATA_DIR", str(jupyter_data_dir))
    # CIP-0009: force Layer A scripted subject-grain path (no widget frontend)
    monkeypatch.setenv("MULTILOGUE_SUBJECT_GRAIN_WIDGETS", "0")
    sys.path.insert(0, str(ROOT))
    nb = nbformat.read(nb_path, as_version=4)
    # Bind kernel to loopback so jupyter_client does not call psutil.net_if_addrs
    # (that syscall aborts under some sandboxes).
    from jupyter_client import KernelManager

    km = KernelManager(kernel_name="python3")
    km.ip = "127.0.0.1"
    client = NotebookClient(
        nb,
        timeout=180,
        kernel_name="python3",
        km=km,
        resources={"metadata": {"path": str(tmp_path)}},
    )
    client.execute()
