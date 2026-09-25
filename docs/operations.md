# Operations and recovery

## First deployment versus the existing installation

The repository is a **portable template**, not the running stack directory. Its `runtime/` and `.env` are private and initially absent. The real installation may use different absolute directories and already has its own health/startup automation.

Do not run this Compose project beside an existing project that publishes the same ports. Do not point both at the same databases. Work on one instance at a time.

Apply `preferences/` through the application UIs, following [the snapshot guide](../preferences/README.md). A preference snapshot cannot restore account IDs, queue entries, library contents, requests, or watched history.

## Mount the NAS safely

The required SMB shares are `Downloads`, `Films`, and `Series`. Mount them under the same `MEDIA_ROOT` used by Compose.

1. In Finder, connect to the exact NAS hostname/IP you will use, authenticate, and save the password in Keychain.
2. Disconnect any temporary Finder mounts of these shares before requesting the explicit mount paths.
3. Run `scripts/mount_shares.py` with the NAS host, account, and absolute mount root. It uses macOS NetFS with UI disabled, skips already-mounted SMB targets, and fails if authentication/mount verification fails.
4. Check `mount` for the actual `smbfs` mounts before starting containers.

The NAS login is not the NZBGet control login or the Usenet provider login. Changing one does not repair the others.

### Why not `mount_smbfs -N`?

The earlier unattended command failed to authenticate despite an available Keychain entry. The tested NetFS API uses macOS's native authentication machinery and the saved login. The helper never receives the password or stores it in its source.

A Keychain entry saved for a numeric IP may not be found when you connect using a different hostname. Keep the endpoint stable and reserve the address if needed. A locked/unavailable login Keychain can also prevent unattended mounts.

### Automatic remount at login and every five minutes

The helper can be scheduled using a **user LaunchAgent**, not a system daemon. It runs in the logged-in user's Keychain session. This optional setup only remounts shares; it is **not** a complete service watchdog.

After setting and exporting the trusted local variables as shown in the README, create the private LaunchAgent:

```sh
python3 - <<'PY'
import os, pathlib, plistlib, shutil
root = pathlib.Path.cwd().resolve()
python = shutil.which('python3')
assert python and (root / 'scripts/mount_shares.py').exists()
assert os.environ['NAS_USER'] and os.environ['NAS_HOST']
assert pathlib.Path(os.environ['MEDIA_ROOT']).is_absolute()
logs = root / 'runtime/mount-logs'
logs.mkdir(parents=True, exist_ok=True)
agent = {
    'Label': 'local.media-stack.mounts',
    'ProgramArguments': [python, str(root / 'scripts/mount_shares.py'),
                         os.environ['NAS_HOST'], os.environ['NAS_USER'], os.environ['MEDIA_ROOT']],
    'RunAtLoad': True,
    'StartInterval': 300,
    'StandardOutPath': str(logs / 'mounts.log'),
    'StandardErrorPath': str(logs / 'mounts.err'),
}
path = pathlib.Path.home() / 'Library/LaunchAgents/local.media-stack.mounts.plist'
path.parent.mkdir(parents=True, exist_ok=True)
with path.open('wb') as f:
    plistlib.dump(agent, f)
path.chmod(0o600)
print('Created private LaunchAgent:', path)
PY
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/local.media-stack.mounts.plist"
```

The generated file includes your local account/path, so it is deliberately created **outside the repository**. Do not enable this in addition to another supervisor mounting the same paths. The live reference installation already has a broader supervisor; this is the portable mounting component, not a verbatim export of private maintenance code.

To remove the optional job:

```sh
launchctl bootout "gui/$(id -u)/local.media-stack.mounts"
```

Its small diagnostic logs are not rotated by this helper; review/rotate them locally if retaining the job long-term.

## Start and stop

Start the Docker engine first. From the repository, with your trusted `.env` loaded:

```sh
python3 scripts/mount_shares.py "$NAS_HOST" "$NAS_USER" "$MEDIA_ROOT" &&
  docker compose up -d
```

The `&&` is intentional: a mount failure must block startup.

```sh
docker compose ps
docker compose logs --tail 100 nzbget
docker compose stop --timeout 120
```

Native Jellyfin starts/stops separately through its macOS application or your own LaunchAgent. Do not create a second Jellyfin server against its live data directory.

### If the NAS disappears

Stop downloading/importing and stop the affected containers. Do not repeatedly restart them against empty local directories. The template does not include the live installation's full stop-on-unmounted-share supervisor; monitor mounts or retain your existing guard.

If files were written into an unmounted mountpoint:

1. Stop all writers.
2. Confirm the path is **not mounted**.
3. Preserve those local files in a separate private backup directory.
4. Recreate the empty mountpoint, remount the correct NAS share, and verify it.
5. Inspect the preserved files separately; do not blindly merge an old queue database into the active queue.

The helper refuses to cover a nonempty unmounted directory so these files are not silently hidden.

## Move NZBGet queue/logs off SMB

This migration has already been applied to the reference installation. For another existing instance:

1. Record queued job IDs/counts and current settings. Ensure you have a private backup.
2. Temporarily suspend any supervisor that would restart NZBGet during the migration.
3. Stop NZBGet gracefully, allowing enough time to flush its current state.
4. Copy the complete old queue directory to the persistent local config directory (`runtime/nzbget/queue` in this template). Verify the copy; preserve the original as rollback data.
5. In the full private configuration, set `QueueDir=/config/queue`, `LogFile=/config/logs/nzbget.log`, and `WriteLog=rotate`. Create writable log directories.
6. Keep `/downloads/intermediate`, `/downloads/completed`, and `/downloads/tmp` unchanged on the NAS.
7. Restart; verify queued IDs, history, effective paths, and fresh logs before declaring success.
8. Restore the supervisor. Keep the backup until resume/import behavior has been verified.

Do not select an empty new `QueueDir` and assume old jobs will automatically appear. Do not copy changing queue files while NZBGet is still writing them.

## Health checks

```sh
docker compose ps
curl -I http://localhost:3000/
curl -I http://localhost:6789/
curl -I http://localhost:8096/
mount | grep smbfs
```

A `401` can be a healthy authenticated web service. HTTP availability alone is not application health: check Sonarr/Radarr System → Status, client/indexer tests, NZBGet queue progress, and an actual Jellyfin playback session.

After a restart, give apps time to initialize before forcing another restart. API calls can briefly stall during heavy storage operations; avoid aggressive restart loops.

## Slow downloads / switching to Ethernet

1. Connect Ethernet and confirm the NAS route uses that interface rather than Wi-Fi. On macOS, `route -n get "$NAS_HOST"` displays the interface; `networksetup -listallhardwareports` maps it to hardware.
2. Verify the negotiated Ethernet speed and NAS link; a slow switch/adapter/cable can remain the bottleneck.
3. Keep the NAS shares mounted and test a sustained download after the RAM cache fills.
4. Distinguish provider throughput, NAS sequential writes, the container/shared-folder path, repair, unpacking, and cross-share imports.
5. Keep TLS and certificate validation; do not trade security for speculative speed gains.

An initial RAM-cache burst is not a sustained disk result. Performance figures vary with hardware and workload; this repository makes no throughput guarantee.

## Backups

The public repository backs up **intent**, not private state. Keep separate encrypted/private backups of:

- app databases and complete live configurations;
- NZBGet queue/history and original NZBs if resume/history matters;
- Jellyfin account/library/watched-state data;
- Seerr users/requests/integration secrets;
- local credential files and recovery information, using an appropriate secret store;
- media itself under a separate NAS backup policy.

Stop applications or use their supported backup mechanisms to obtain consistent databases. Never copy live SQLite files casually and assume they are consistent. Store backups outside the public repository; `.gitignore` is a safety aid, not encryption.

## Updates and rollback

The template currently uses moving `latest` tags. For reproducibility, record/pin tested image digests locally and update deliberately.

1. Take an application-consistent private backup.
2. Review upstream release/migration notes.
3. Update one service at a time:
   ```sh
   docker compose pull sonarr
   docker compose up -d --no-deps sonarr
   docker compose logs --tail 100 sonarr
   ```
4. Test its UI, peer connections, and a representative workflow.
5. Repeat for other services. Update native Jellyfin separately.

Rollback may require **both** the previous image and the matching pre-migration database/configuration. Reverting a container alone may not undo a database migration.

## Publishing configuration changes

Edit curated templates/preferences, never export a whole runtime directory. Before commit:

```sh
python3 scripts/test_mount_shares.py
python3 scripts/check_public.py
docker compose --env-file .env.example config --quiet
git status --short
git diff --cached
```

Only then push. See [Security](security.md) for the publication boundary and credential-rotation procedure.
