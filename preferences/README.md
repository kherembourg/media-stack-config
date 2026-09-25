# Preference snapshots

These are **allowlisted references**, not raw backups or complete application configuration files. Use them to reconstruct preferences in the settings UI of a compatible version.

## Inventory

| File | Included | Deliberately absent |
|---|---|---|
| `sonarr.json` | Naming, media management, quality profiles/definitions, custom formats, root path, NZBGet client options | Series catalog, history, API key, auth, per-series selections |
| `radarr.json` | Movie naming, media management, quality/language profiles and definitions, custom formats, root path, NZBGet options | Movie catalog, history, API key, auth, per-movie overrides |
| `prowlarr.json` | Sonarr/Radarr application sync levels, categories, internal URLs | Indexer accounts/endpoints/keys, app keys |
| `bazarr.json` | Search/scoring/sync preferences, embedded subtitle handling, language profiles, peer addresses | Provider credentials, API keys, media rows, profile assignments per title |
| `seerr.json` | Locale/region/request preferences, profile names, roots, target service settings | Users, requests, session/VAPID secrets, keys, server/library/account IDs |
| `nzbget.conf` | Paths, buffering/caching, logs, repair/unpack preferences, categories, public server endpoint | Full live config, UI/provider login, queue contents, download history |
| `jellyfin/system.xml` | Selected metadata, language, resume, grouping and retention preferences | Server identity, accounts, repositories, credentials, library inventory |
| `jellyfin/encoding.xml` | Selected codec/transcode/tone-mapping preferences | Personal executable/device paths and full encoder configuration |
| `jellyfin/network.xml` | Selected listener/discovery/remote-access preferences | Certificates/passwords, private addresses, proxies and public hostnames |

## Applying settings

1. Start a fresh service and complete its first-run wizard and authentication setup.
2. Configure actual storage roots and private peer/provider credentials.
3. Recreate naming and quality/language preferences using the snapshot as reference.
4. Reconnect applications and run their connection tests.
5. Test a small authorized download/import/subtitle/playback workflow before enabling a large queue.

Do not POST these files blindly to an API. Some nested IDs identify built-in qualities or custom-format/language-profile items; they may be version-specific. Top-level profile IDs were removed where practical. Re-select profiles by **name** and recreate mappings in the fresh installation.

Seerr's `mediaServerType` and permission flags are captured values, not portable advice. Choose the actual media-server mode and review permissions in the UI. Bazarr's profile-item IDs support cutoff relationships within each snapshot; recreate profiles and choose defaults by name, rather than assuming fresh profile IDs match.

The Jellyfin XML files omit important live fields by design. **Do not replace complete live XML files with them.** Set matching options in the dashboard; if offline editing is necessary, stop Jellyfin and merge only the selected elements into a privately backed-up full configuration.

Likewise, `nzbget.conf` is a **partial overlay**. Use the settings UI or merge its entries into the image-generated private full configuration while NZBGet is stopped. Set strong control credentials and provider credentials separately before use.

## Updating snapshots

Export only the settings needed to describe preferences. Keep new fields out until reviewed, particularly nested `fields` arrays in downloader/indexer definitions. Never serialize an entire root-folder response: it can contain actual media directory names. Never export full Seerr settings, raw Bazarr YAML, or app XML containing API keys.

Provider accounts, per-title decisions, libraries, and application identities belong in private backups, not this directory.
