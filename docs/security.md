# Security and publication boundary

## Included

- Reviewed Docker Compose topology with generic local-path variables.
- Homepage layout, public service names, local ports, and secret-file **references**.
- Allowlisted preference snapshots: naming, quality/language choices, buffer sizes, and service-to-service URLs.
- Native macOS mounting helper that uses the login Keychain without reading or printing passwords.
- Documentation and offline validation checks.

## Excluded

- Usernames/passwords for real accounts, API keys, provider logins, tokens, session secrets, VAPID keys, certificates/private keys, and Keychain contents.
- Complete raw application configs, because many mix preferences with credentials.
- Databases, library inventories, watched history, requests, queue contents, media filenames, downloads, and NZBs.
- Personal hostnames, machine/account/client identifiers, actual NAS IP addresses, and personal absolute paths.
- Logs, backups, cache directories, analytics IDs, private indexer URLs, and provider configurations.

The GitHub account/repository name is intentionally public; it is not an application login. Generic environment-variable names and Homepage credential placeholders are not credentials.

## Credential locations

| Credential | Where to configure/store privately |
|---|---|
| NAS SMB account | macOS Keychain, matching the exact NAS endpoint |
| Usenet account | NZBGet's private live configuration |
| NZBGet UI/control login | NZBGet private configuration; peers receive it privately |
| Sonarr/Radarr/Prowlarr/Bazarr/Seerr API keys | Their private app state; copied into peer settings as needed |
| Homepage widget values | Ignored `secrets/homepage/` files with restrictive permissions |
| Jellyfin/Plex authentication | Native/external server and private integration settings |

Compose file-backed Homepage credentials are read-only bind-mounted files. They are **not encrypted Docker Swarm secrets**. Protect the Mac account, local files, and backups accordingly.

Do not disable an app's authentication to solve SMB authentication. These are independent boundaries.

## Network defaults

The public Compose template publishes web ports only on loopback. This protects against accidental LAN exposure while installing and configuring authentication, but it is not a substitute for strong app credentials.

Native Jellyfin has its own listener/firewall settings and may be reachable from other devices. Explicitly review remote access. Do not forward management ports to the internet. If remote access is needed, design an authenticated VPN or HTTPS reverse-proxy setup separately, including dashboard allowed hosts and trusted-proxy settings.

Retain provider TLS/certificate verification. Do not disable SMB signing, verification, or access controls just to chase performance.

## Safe Git workflow

1. Keep live state outside the tracked tree or in explicitly ignored directories.
2. Export settings by **allowlist**, not by deleting a few suspicious fields from a full dump.
3. Review nested objects as well as obvious top-level keys.
4. Run `scripts/check_public.py` and inspect staged changes before committing.
5. Never use `git add -f` on `.env`, runtime configs, backups, databases, or logs.

The checker detects common token formats, non-placeholder credential fields, personal paths/private IP addresses, and unexpected public file types. It cannot reliably identify every arbitrary password or secret embedded in prose/regexes. CI and `.gitignore` do not replace human review.

Initial publication was prepared from selected settings, not by copying the live configuration directory. Live secret values were additionally checked against the candidate files locally without printing those values. No live databases were copied into this repository.

## If a secret is committed

1. **Revoke/rotate it immediately.** Removing the file in a later commit is not enough.
2. Update private integrations that used the old credential.
3. Remove it from Git history using the appropriate history-rewrite process and coordinate any force-push.
4. Treat public forks, caches, and clones as potentially retaining it.
5. Review the export/validation path so the same class of data cannot recur.

Keeping an existing public repository private afterward does not undo disclosure. Prevention is the primary control.
