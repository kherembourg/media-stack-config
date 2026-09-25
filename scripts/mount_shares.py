#!/usr/bin/env python3
"""Mount NAS shares through macOS NetFS and the login Keychain; no stored passwords."""
import argparse
from pathlib import Path
import subprocess
from urllib.parse import quote

SHARES = ("Downloads", "Films", "Series")
NETFS = """
ObjC.import("NetFS");
ObjC.import("Foundation");
function run(args) {
    const result = $.NetFSMountURLSync(
        $.NSURL.URLWithString(args[0]), $.NSURL.fileURLWithPath(args[1]),
        null, null, $({UIOption: "NoUI"}), $({MountAtMountDir: true}), null);
    if (result !== 0) throw Error("SMB mount failed: " + result);
}
"""


def mounted(target):
    table = subprocess.check_output(["/sbin/mount"], text=True, timeout=10)
    return f" on {target} (smbfs," in table


def mount_shares(host, user, root):
    if not host or not user or not root.is_absolute() or any(c in host for c in "/@:\n\r"):
        raise ValueError("Use a hostname/IPv4 address, a NAS account, and an absolute mount root")
    for share in SHARES:
        target = root / share
        target.mkdir(parents=True, exist_ok=True)
        if mounted(target):
            continue
        if any(target.iterdir()):
            raise RuntimeError(f"Refusing to hide local files under unmounted {target}; preserve them first")
        url = f"smb://{quote(user, safe='')}@{host}/{share}"
        subprocess.run(["/usr/bin/osascript", "-l", "JavaScript", "-e", NETFS, url, str(target)], check=True, timeout=40)
        if not mounted(target):
            raise RuntimeError(f"Mount was not verified: {target}")
        print(f"Mounted {share}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("user")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    mount_shares(args.host, args.user, args.root)
