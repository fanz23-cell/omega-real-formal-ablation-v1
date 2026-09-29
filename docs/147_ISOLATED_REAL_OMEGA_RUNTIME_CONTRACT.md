# 147. Isolated Real-Omega Runtime Contract

## Design

A second container, `omega_isolated_benchmark_20260928`, run from the **exact same image** as the live
production container (verified by image ID match, not just tag match — see doc 145), with every live
attachment point removed:

```
docker run -d --name omega_isolated_benchmark_20260928 \
  --network none \
  -v <scratch_dir>/scratch_chroma:/PeTTa/repos/OmegaClaw-Core/memory/chroma_db \
  --entrypoint sleep \
  mindchildren/omegaclaw-core:fan_omegaclaw_ai_bt \
  infinity
```

## Why the tag reference, not the digest reference

`docker run ...@sha256:...` attempted a registry pull (`pull access denied` — this environment has no
registry credentials for `mindchildren/omegaclaw-core`). Used the tag instead (already cached locally,
no pull needed) and independently verified post-creation that the resulting container's `Image` field
is the exact same digest as the live container's (`sha256:4b14c13ef5ea...`) — same guarantee, without
needing registry access.

## Why `--entrypoint sleep ... infinity` instead of the real command

The real compose command (`provider=Anthropic commchannel=robot memoryDirectory=...`) boots the full
conversational agent loop: nginx, provider connectivity, the TCP robot channel on port 8767. None of
that is needed for this benchmark — the real reasoning is invoked directly via `docker exec` running a
one-off `swipl`/`python3` process against the container's own installed plugin code, exactly as the
prior (`OVERNIGHT_GROUNDED_FORMAL_20260921_0334`) harness's own `abc_harness.py` already
established as a working pattern (its own docstring: *"MUST be called from inside the omegaclaw
container... docker exec -i bison_client-omegaclaw-1 python3 -"*) — this round applies the same
mechanic to a fresh, isolated instance instead of the live one. An inert `sleep infinity` entrypoint
means the container never attempts a provider connection, never opens the robot channel, and never
touches nginx at all.

## Isolation checklist (mechanically verified this session, not assumed)

| Requirement | Verified how | Result |
|---|---|---|
| No live robot ports | `docker inspect --format '{{.HostConfig.NetworkMode}}'` | `none` |
| No live ROS graph | same (`--network none` means no host networking, no DDS reachability at all) | confirmed |
| No live WorldState mount | `docker inspect --format '{{range .Mounts}}...'` | only mount is the scratch dir |
| No live Chroma mount | same | scratch dir only, confirmed empty before first write (`ls` showed 0 files pre-seed) |
| No production memory volume | same | live `omegaclaw-memory/` never referenced |
| No production observation log | same | container has its own fresh, empty log path |
| No production mission journal | same | `ai_bt_missions.jsonl` mount intentionally omitted |
| Same real code as production | `sha256sum` of 4 key plugin files, both inside this container and inside the live one | byte-identical (doc 145) |
| Removable without affecting production | container is entirely separate; scratch dir is a plain directory under this research folder | trivially true by construction |

## Memory/disk safety (standing project constraint: never crash the shared host)

Checked before creation: host disk 99% used (18G free — no new image layers needed, so this action
does not consume meaningful additional disk); host memory under pressure from other tenants, but every
one of this project's own containers individually uses well under 100MiB (`docker stats`), and the new
container measured 568KiB at idle. Judged a safe, bounded addition; monitored via `docker stats`
throughout the session; the container is stopped/removed once the confirmatory run and its
reproducibility validation are both complete (see final packaging docs).

## Explicit rejection of monkeypatching a live process

Per the governing directive: `grounded_reason.py` and `observation_memory.py` both cache a
module-level Chroma client (`_client`/collection handle) inside whatever process imports them; the
directive is correct that reassigning `CHROMA_PATH` inside an *already-running* live process would be
unsafe (the cached client would keep pointing at whatever path was active when it was first
constructed, and concurrent access from a real robot request during the reassignment window is a real
race). This design sidesteps that entirely by never touching the live process's memory at all — the
isolated container is a wholly separate process tree from the first `import`, so there is no cached
client to reassign.
