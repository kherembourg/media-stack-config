# Service guide

All API keys, accounts, provider logins, and tokens mentioned below are configured **privately**. None are supplied by this repository. Prefer the settings UI when applying preference snapshots; file/API formats differ across versions.

## Jellyfin

**Role / why:** the playback server. It catalogs the final movie/series libraries and serves web, mobile, and TV clients. It is separate from the download-management stack and provides a playback option alongside an existing external Plex server.

**Runs:** native Jellyfin macOS application, HTTP port `8096`. It is intentionally absent from Compose.

**Storage:** native application-support directories on the Mac for configuration, databases, metadata, logs, and transcode cache; NAS `Films` and `Series` for libraries. Playback transcoding can create temporary local files even though NZBGet download/unpack files remain on the NAS.

**Setup:**

1. Install and start the macOS Jellyfin app; complete its administrator wizard.
2. Add a Movies library pointing to the absolute mounted `Films` path and a TV library pointing to the absolute mounted `Series` path.
3. Set metadata language to French and country to France if retaining the captured preferences.
4. Review the selected settings in `preferences/jellyfin/*.xml`. These XML files are **partial references**, not replacements for complete live files.
5. Check network access and authentication explicitly. Native Jellyfin does not inherit Compose's loopback restrictions.
6. Create playback users and configure clients privately. Accounts, watched status, device IDs, libraries, API keys, and plugins are not restored here.

**Usage:** browse libraries, play media, manage metadata, and inspect Dashboard → Active devices / playback information. Refresh a library after a successful import if automatic detection did not notice it.

**Preferences:** French UI/metadata, resume thresholds and grouping settings are included. The actual hardware acceleration selection is `none`; do not infer that it is already using VideoToolbox. Enabling hardware acceleration requires a separate compatibility/performance check.

**Troubleshooting:** if a library disappears, confirm the SMB mount before rescanning. If playback buffers, distinguish direct play from transcoding; inspect codec support, Mac CPU, client bandwidth, and transcode logs. A dashboard HTTP success only proves the server answers, not that playback works.

Official documentation: <https://jellyfin.org/docs/>

## Sonarr

**Role / why:** series library manager. It tracks monitored episodes, selects releases using profiles, sends downloads to NZBGet, and imports/renames completed episodes.

**Runs:** Docker, port `8989`. Local state: `runtime/sonarr`. NAS mounts: `/downloads`, `/series`.

**Setup:**

1. Complete authentication setup and retrieve the generated API key privately.
2. Add `/series` as the root folder. Never enter a macOS path inside the container UI.
3. Configure NZBGet at host `nzbget`, port `6789`, with its private control credentials and the series category from the snapshot.
4. Configure the Sonarr application in Prowlarr using `http://sonarr:8989` and the Sonarr API key; test and sync.
5. Recreate the naming and quality preferences from `preferences/sonarr.json`.
6. In Seerr, choose the matching profile **by name**. The captured default is `HD-1080p` with `/series` as root.

**Usage:** add a series, select its root/profile and monitoring policy, then search or let RSS monitoring find new episodes. Review Activity → Queue for download/import errors. Use Wanted for monitored missing episodes rather than repeatedly adding the same series.

**Preferences:** episode/season/folder naming, quality profiles, quality size definitions, custom formats if configured, media-management flags, and sanitized download-client settings. Existing shows, monitoring selections, download history, and per-show overrides are excluded.

**Troubleshooting:** an import path must resolve identically for Sonarr and NZBGet. Both use `/downloads`, so remote path mappings should not be needed for this topology. Check category matching, completed paths, permissions, and NAS free space before adding path mappings. A configured hardlink preference does not make cross-share hardlinks possible.

Official documentation: <https://wiki.servarr.com/sonarr>

## Radarr

**Role / why:** the movie equivalent of Sonarr: monitoring, release selection, download orchestration, naming, and library imports.

**Runs:** Docker, port `7878`. Local state: `runtime/radarr`. NAS mounts: `/downloads`, `/movies`.

**Setup:** configure authentication, add `/movies`, add NZBGet at `nzbget:6789` with the movie category, and connect Prowlarr using `http://radarr:7878` plus the private Radarr API key. Apply `preferences/radarr.json` through the UI.

**Usage:** add movies with an appropriate quality profile and availability policy, monitor them, search, and inspect Activity for progress. The captured Seerr default selects `HD-1080p`, `/movies`, and minimum availability `released`.

**Preferences:** naming formats, quality profiles and size definitions, language choices inside those profiles, custom formats if present, media management, and sanitized NZBGet settings. No movie catalog or watched/download history is included.

**Troubleshooting:** check root folder availability, matching categories, and the NZBGet completion path. Collection/root-folder warnings can come from private existing database entries; copying a root-folder configuration does not migrate those entries. Review upgrade/cutoff settings if releases are repeatedly replaced.

Official documentation: <https://wiki.servarr.com/radarr>

## Prowlarr

**Role / why:** centralized indexer management. Configure an indexer once, then synchronize compatible settings to Sonarr and Radarr instead of maintaining duplicate accounts manually.

**Runs:** Docker, port `9696`. Local state: `runtime/prowlarr`. Its existing share mappings are retained for topology compatibility; normal indexer synchronization does not require reading the media libraries.

**Setup:**

1. Set authentication and add your indexers privately. Subscription URLs, API keys, and accounts are intentionally absent.
2. Add Sonarr: target `http://sonarr:8989`, Prowlarr URL `http://prowlarr:9696`, Sonarr API key.
3. Add Radarr similarly at `http://radarr:7878` with its API key.
4. Review `preferences/prowlarr.json` for sync level and category choices, then test and sync.

**Usage:** monitor indexer health, correct expired credentials, review rate limits, and synchronize application definitions. Search/download decisions and movie/episode monitoring remain primarily with Radarr/Sonarr.

**Troubleshooting:** successful communication with Prowlarr does not prove an upstream indexer is healthy. Check application tests, indexer tests, categories, account limits, DNS, and TLS separately. Avoid manually editing synchronized indexer settings in downstream apps if full sync will overwrite them.

Official documentation: <https://wiki.servarr.com/prowlarr>

## NZBGet

**Role / why:** the Usenet downloader. Retrieves articles, verifies/repairs files, unpacks archives, and exposes completion status to Sonarr/Radarr.

**Runs:** Docker, port `6789`. Private live configuration and queue/log state: `runtime/nzbget`. All download/unpack file paths: NAS `/downloads`.

**Setup:**

1. Let the image generate a full configuration, then configure strong control/UI credentials privately.
2. Add the Usenet account. The snapshot retains the public Astraweb EU endpoint, TLS setting, port, and connection count, but **not** its login. The public overlay strengthens certificate verification to `Strict` with `CertCheck=yes`; the live configuration is not modified by publishing it.
3. Apply `preferences/nzbget.conf` as a small settings overlay via the UI or careful offline editing. Keep the full vendor configuration.
4. Set `QueueDir=/config/queue`, `LogFile=/config/logs/nzbget.log`, and create writable local directories if needed.
5. Leave `InterDir`, `DestDir`, and `TempDir` on `/downloads`. Match categories with Sonarr/Radarr.
6. Update Sonarr/Radarr and Homepage with the private NZBGet control login.

**Captured performance settings:**

| Setting | Value | Purpose |
|---|---|---|
| `ArticleCache` | `256` MB | Batch article data in RAM |
| `WriteBuffer` | `1024` KB | Larger per-connection write buffer |
| `DirectWrite` | `yes` | Write into destination files where supported |
| `FlushQueue` | `yes` | Preserve queue-state flushing on local storage |
| `WriteLog` | `rotate` | Avoid a single indefinitely growing log |
| `RotateLog` | `3` days | Bound log retention by age, not a hard byte limit |
| `DownloadRate` | `0` | No configured speed limit |
| `NzbDirInterval` | `0` | No folder polling; API/web submissions still work |

**Usage:** most jobs arrive through Sonarr/Radarr. Use the web UI to inspect speed, provider failures, repair/unpack progress, and history. Compare MB/s with Mbps correctly; divide Mbps by eight before allowing for overhead.

**Important distinction:** queue/history metadata on the Mac is not the downloaded media. The 256 MB cache is RAM. NZBGet still performs repair/unpacking on the Mac CPU, reading and writing NAS files.

**Troubleshooting:**

- `Could not flush directory buffers`: verify `QueueDir` is really local, not SMB. Do not silence it by disabling durability before fixing the path.
- Slow speed after a fast burst: the RAM cache may have filled; measure sustained network and disk throughput.
- Provider connected but no useful download: examine article availability, retries, quota, and account limits.
- Automatic scanning disabled: expected when using API submissions; enable only if you actually drop NZBs into a watched folder.
- No import: inspect category, unpack result, permissions, and the path reported to Sonarr/Radarr.

The control login, Usenet account, and NAS SMB login are **three unrelated credentials**.

Official documentation: <https://nzbget.com/documentation/>

## Bazarr

**Role / why:** subtitle management for existing Sonarr/Radarr libraries. It identifies missing subtitles, queries configured providers, scores candidates, and writes subtitle files alongside media.

**Runs:** Docker, port `6767`. Local state: `runtime/bazarr`. NAS mounts: `/series`, `/movies`.

**Setup:** connect Sonarr and Radarr using their Compose hostnames and private API keys. Because media paths match, the base topology does not need path mappings. Configure subtitle providers/accounts privately, recreate the language profiles, and assign defaults before starting wanted searches.

**Preferences:** `preferences/bazarr.json` contains search/upgrade settings, embedded subtitle behavior, sync thresholds, and language profiles. The captured `Basic` profile requests French and is the default for series/movies; an additional English profile is retained. Existing media-to-profile assignments are not exported.

**Usage:** inspect wanted subtitles, run searches, review language/forced/hearing-impaired requirements, and use manual selection when automatic matching is wrong. Current embedded-subtitle settings allow using embedded subtitles; synchronization is not globally enabled in the snapshot.

**Troubleshooting:** check provider credentials/quotas, profile assignments, score thresholds, write permissions, and missing/incorrect languages. The captured `use_plex` choice needs a private Plex integration if retained; otherwise disable it or configure Jellyfin deliberately. Provider credentials and library IDs are not supplied.

Official documentation: <https://wiki.bazarr.media/>

## Seerr

**Role / why:** a user-friendly discovery/request front end. Users request media here instead of operating the download-management tools directly.

**Runs:** Docker, port `5055`. Local state: `runtime/overseer` (legacy folder name, current Seerr image).

**Setup:** complete the first-run media-server/account wizard privately. The reference installation integrates an existing external Plex server; it is not provisioned by Compose. If choosing Jellyfin instead, use the native host endpoint and complete Seerr's supported Jellyfin setup rather than copying the old server-type value blindly.

Add Sonarr and Radarr with Compose hostnames and their private API keys. Select quality profiles by name, root folders `/series` and `/movies`, and the desired default/non-4K server entries. Apply the captured request preferences from `preferences/seerr.json`.

**Usage:** discover movies/series, submit and approve requests according to permissions, and monitor availability. Sonarr/Radarr carry out searches/imports; Seerr coordinates requests and status, not the file transfers.

**Preferences:** French locale; US streaming-region preference; HD-1080p default target profiles; released movie availability; no season folders requested by the captured Sonarr connection. Numeric permission bitmasks and unlimited-by-zero quotas are snapshots—review their meaning in the running version before granting access.

**Troubleshooting:** wrong availability can reflect stale library synchronization or an incorrect media-server selection. Check server connectivity, library selections, profile names, and API keys. Session secrets, VAPID keys, user data, server IDs, and request history are deliberately absent.

Official project and documentation links: <https://github.com/seerr-team/seerr>

## Homepage

**Role / why:** one landing page for links, health indicators, and widgets. It observes and links services; it does not replace their management interfaces or authentication.

**Runs:** Docker, port `3000`, bound to loopback. YAML is under `config/homepage/`; private widget credentials are mounted read-only from `secrets/homepage/`.

**Setup:** retain the provided layout or edit it. Populate these private files with the appropriate values (no shell quoting inside the file):

| File | Value |
|---|---|
| `sonarr_key` | Sonarr API key |
| `radarr_key` | Radarr API key |
| `prowlarr_key` | Prowlarr API key |
| `bazarr_key` | Bazarr API key |
| `seerr_key` | Seerr API key |
| `nzbget_user` | NZBGet control username |
| `nzbget_pass` | NZBGet control password |

Files stay local; YAML uses `{{HOMEPAGE_FILE_...}}` placeholders. Restart Homepage after changing credentials. Jellyfin currently has a link and HTTP monitor, not an authenticated API widget.

**Usage:** open `http://localhost:3000` **on the Mac**. The French layout groups media-library tools, download tools, and requests. Theme: dark/slate, equal-height cards, dot-style status.

**Troubleshooting:** a working link with a broken widget usually means its internal URL/key is wrong. A blank/incomplete widget on a fresh deployment is expected until keys are supplied. Check `HOMEPAGE_ALLOWED_HOSTS` if using a new hostname. Another device's localhost is not this Mac; remote access needs the deliberate changes described in Architecture.

Official documentation: <https://gethomepage.dev/>

## Inactive / intentionally not deployed

The old Compose inventory also contained disabled entries for:

- **Recyclarr:** optional synchronization of Sonarr/Radarr profiles with curated quality guidance. Not enabled here; running it later may overwrite manually captured preferences. <https://recyclarr.dev/>
- **Dashdot:** optional machine-resource dashboard. Homepage already covers the immediate landing-page need; no additional host-monitoring service is enabled. <https://getdashdot.com/>
- **Plex Meta Manager / Kometa:** optional Plex collection/metadata automation. It requires its own private Plex integration and is outside the active download/playback setup. <https://kometa.wiki/>

Their dormant runtime folders and empty legacy dashboard experiments are not public configuration artifacts. Add an optional service only when its specific job is needed.
