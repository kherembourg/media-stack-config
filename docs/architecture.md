# Architecture

## Design goals

1. Use the Mac for application compute and small, latency-sensitive state.
2. Keep large media files on the NAS throughout downloading and unpacking.
3. Keep identical container paths where applications exchange file locations.
4. Centralize indexer configuration and provide one dashboard/request interface.
5. Keep deployable public configuration separate from private state and credentials.

This is a practical single-user/home-network design, not a highly available cluster. A sleeping Mac, unavailable NAS, or broken network connection interrupts the workflow.

## Runtime boundaries

```mermaid
flowchart TB
    subgraph Mac[macOS host]
        Local[(Local disk: configs / databases / logs / queue)]
        Keychain[macOS login Keychain]
        Mounts[macOS NetFS / SMB mounts]
        Native[Native Jellyfin]
        subgraph Engine[OrbStack / Docker Compose network]
            Homepage
            Seerr
            Sonarr
            Radarr
            Prowlarr
            NZBGet
            Bazarr
        end
        Engine --> Local
        Engine --> Mounts
        Native --> Mounts
        Keychain --> Mounts
        Homepage -. host.docker.internal .-> Native
    end
    Mounts <-- SMB --> NAS[(NAS shares: Downloads / Films / Series)]
```

The NAS stores files; **NZBGet on the Mac performs decompression and repair** against those files over SMB. Saying “unpack on the NAS” here means the input/output files live there, not that the NAS CPU runs the unpacker.

The Docker services use a default project network. Host-side browser access goes through published ports. Container-to-container traffic uses Compose DNS and does not need those host port bindings.

## Storage contract

| Data | Container path | Host location | Reason |
|---|---|---|---|
| Sonarr/Radarr/Prowlarr/Bazarr state | `/config` | `./runtime/<service>` | Local databases and logs avoid SMB latency/locking issues |
| NZBGet configuration | `/config/nzbget.conf` | `./runtime/nzbget/nzbget.conf` | Private live configuration; excluded from Git |
| NZBGet queue/history | `/config/queue` | `./runtime/nzbget/queue` | Small files updated frequently; local directory syncing |
| NZBGet logs | `/config/logs` | `./runtime/nzbget/logs` | Rotation without constant NAS writes |
| NZBGet active downloads | `/downloads/intermediate` | NAS `Downloads/intermediate` | Large files remain off the Mac |
| NZBGet completed downloads | `/downloads/completed` | NAS `Downloads/completed` | Shared import location |
| NZBGet temporary articles | `/downloads/tmp` | NAS `Downloads/tmp` | Avoid accidental large temporary disk use on the Mac |
| NZB descriptors | `/downloads/nzb` | NAS `Downloads/nzb` | Existing path retained; not exported |
| Final movies | `/movies` | NAS `Films` | Radarr and Bazarr share the same path |
| Final series | `/series` | NAS `Series` | Sonarr and Bazarr share the same path |
| Seerr configuration/database | `/app/config` | `./runtime/overseer` | The legacy directory name is retained for compatibility |
| Homepage configuration | `/app/config` | `./config/homepage` | Reviewed YAML templates; generated logs ignored |
| Homepage credentials | `/run/secrets/homepage` | `./secrets/homepage` | Read-only bind mount; never public |
| Jellyfin state/cache | Native app paths | Mac application-support directory | Native service, not a Docker volume |
| Jellyfin libraries | Native absolute paths | `${MEDIA_ROOT}/Films`, `${MEDIA_ROOT}/Series` | Jellyfin sees macOS paths, not `/movies` or `/series` |

`MEDIA_ROOT` is a local directory containing **three actual mounted shares**. A directory with the right name is not enough. Compose's `create_host_path: false` prevents creating missing bind sources, but it cannot distinguish an existing empty directory from a mounted NAS share.

### Import costs and hardlinks

`Downloads`, `Films`, and `Series` are separate SMB shares/mounts in this layout. Do **not** assume atomic renames or hardlinks work across them, even if they live on the same NAS volume. Imports can become a copy followed by cleanup, consuming bandwidth and temporary extra NAS space.

Some exported application preferences request hardlinks. That preference cannot override filesystem boundaries. A future single-share layout such as `/data/downloads` and `/data/media` could improve imports, but it is a migration—not a hidden change made by this repository.

## Service connections

| Caller | Target / configured URL | Authentication entered privately |
|---|---|---|
| Sonarr | `nzbget:6789` | NZBGet control username/password |
| Radarr | `nzbget:6789` | NZBGet control username/password |
| Prowlarr | `http://sonarr:8989` | Sonarr API key |
| Prowlarr | `http://radarr:7878` | Radarr API key |
| Sonarr/Radarr indexer integration | `http://prowlarr:9696` | Prowlarr-generated indexer credentials |
| Bazarr | `sonarr:8989`, `radarr:7878` | Respective API keys |
| Seerr | `sonarr:8989`, `radarr:7878` | Respective API keys |
| Homepage widgets | Compose service names | Private file-backed API keys / NZBGet login |
| Homepage native Jellyfin monitor | `http://host.docker.internal:8096/` | HTTP availability check only, no API key |
| Seerr, if using native Jellyfin | `http://host.docker.internal:8096` | Complete Seerr's media-server setup privately |
| Seerr/Bazarr, if using external Plex | Your private Plex address | Plex authorization configured privately |
| NZBGet | Configured Astraweb endpoint over TLS | Usenet provider account, separate from web UI login |
| macOS mount helper | NAS SMB endpoint | NAS account stored in macOS Keychain |

A browser link and a widget URL are different:

- `href: http://127.0.0.1:8989` is opened by the browser **on the Mac**.
- `widget.url: http://sonarr:8989` is fetched **inside the Docker network**.
- `localhost` inside a container refers to that container, not the Mac or another service.

For another device, localhost links are wrong. A LAN/reverse-proxy deployment needs deliberate changes to port bindings, dashboard links, allowed hosts, authentication, and firewall rules. It is not enabled by this public template.

## Download and playback lifecycle

1. A request is added in Seerr, or a movie/series is added directly to Radarr/Sonarr.
2. Radarr/Sonarr search their configured indexers; Prowlarr maintains those integrations.
3. An NZB is sent to NZBGet with the matching category.
4. NZBGet downloads articles, repairs when needed, and unpacks into NAS-backed working paths.
5. The completed-download API reports the final path to Sonarr/Radarr.
6. Sonarr/Radarr import and rename files into their NAS library roots.
7. Bazarr discovers imported media through their APIs and writes requested subtitles alongside the files.
8. Jellyfin scans its NAS library paths and serves playback to clients.
9. Seerr updates availability; Homepage displays status from its configured widgets.

The request front end is not the downloader. Prowlarr is not an indexer subscription. Jellyfin is not responsible for Sonarr/Radarr imports.

## Why keep Jellyfin native?

The existing installation uses the macOS application while the management apps use Docker. This separates native playback/transcoding integration from Linux containers. It also leaves the option of using Apple's VideoToolbox where supported.

**Current snapshot:** hardware acceleration is `none`; hardware encoding being permitted does not itself enable VideoToolbox. Benchmark playback and verify encoder support before changing this setting. The repo does not install Jellyfin or modify its account database.

## Performance and availability

- SMB directory sync is not necessarily supported. Keeping NZBGet's queue local avoids the observed queue-flush warnings without disabling `FlushQueue`.
- Tiny writes and metadata operations are expensive over SMB. Article caching and larger write buffers reduce this cost, but do not remove network limits.
- Article cache is RAM, not a local download directory. It can mask storage bottlenecks briefly; measure speed after the cache fills.
- Container → macOS shared filesystem → SMB is an extra I/O layer compared with a native app or NAS-local downloader.
- Ethernet removes a common Wi-Fi bottleneck, but does not guarantee line-rate downloads. NAS disks, link speed, imports, unpacking, CPU, provider limits, and article availability still matter.
- Queue/log files are small; Jellyfin metadata and the other application databases can grow. Monitor local disk space too.
- Reserve a stable NAS address or use reliable local DNS. The Keychain entry must match the hostname/address used by the mount helper.

Do not use the public repository as a replacement for private, application-consistent backups.
