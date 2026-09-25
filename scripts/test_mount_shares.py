"""Offline check: python3 scripts/test_mount_shares.py"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import mount_shares as m

with TemporaryDirectory() as directory:
    root = Path(directory)
    with patch.object(m, "mounted", return_value=True), patch.object(m.subprocess, "run") as run:
        m.mount_shares("nas.example", "example-user", root)
        run.assert_not_called()
    with patch.object(m, "mounted", side_effect=[False, True] * 3), patch.object(m.subprocess, "run") as run:
        m.mount_shares("nas.example", "example-user", root)
        assert run.call_count == 3
        assert run.call_args.args[0][-2:] == ["smb://example-user@nas.example/Series", str(root / "Series")]
    with patch.object(m, "mounted", return_value=False), patch.object(m.subprocess, "run"):
        try:
            m.mount_shares("nas.example", "example-user", root)
        except RuntimeError:
            pass
        else:
            raise AssertionError("An unverified mount must fail")
    (root / "Downloads" / "local-file").write_text("preserve me")
    with patch.object(m, "mounted", return_value=False), patch.object(m.subprocess, "run") as run:
        try:
            m.mount_shares("nas.example", "example-user", root)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Never hide local downloads under a mount")
        run.assert_not_called()
print("Mount safety checks passed")
