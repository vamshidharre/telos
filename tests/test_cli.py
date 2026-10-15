"""
Tests for Telos CLI commands.
"""

import os
import tempfile
from pathlib import Path
from telos.cli import cmd_init, cmd_status, cmd_history
import argparse


def test_cli_init_and_status():
    old_cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    try:
        os.chdir(tmpdir)

        # 1. Init
        args_init = argparse.Namespace(force=False)
        code = cmd_init(args_init)
        assert code == 0
        assert (Path(tmpdir) / "telos.yaml").exists()

        # 2. Status
        args_status = argparse.Namespace(contract="telos.yaml")
        code = cmd_status(args_status)
        assert code == 0

        # 3. History (empty)
        args_history = argparse.Namespace()
        code = cmd_history(args_history)
        assert code == 0
    finally:
        os.chdir(old_cwd)
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
