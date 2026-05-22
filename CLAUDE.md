# CLAUDE.md

## Repository

- **Repo:** `kmechlin/zelos.dgx-proxmox-test-vm`
- **Collection FQCN:** `zelos.dgx_proxmox_test_vm`
- **Purpose:** Build, snapshot, reset, and destroy a single Proxmox VM
  running DGX OS, as a repeatable disposable target for iterating on
  the [`zelos.dgx`](https://github.com/kmechlin/zelos.dgx) collection.
- **State:** v0.1.0 scaffold. **Not yet validated against real hardware.**

This repo is **sister tooling** to `zelos.dgx`, not a member of the
`zelos.<hosttype>` provisioner series. It does not provision the host
that will run AI workloads -- it provisions the *test target* the
provisioner is iterated against.

## Layout

```
zelos.dgx-proxmox-test-vm/
├── ansible.cfg
├── galaxy.yml                 # namespace=zelos, name=dgx_proxmox_test_vm, version=0.1.0
├── pyproject.toml             # zptv CLI package
├── Dockerfile                 # python:3.12-slim + ansible + zptv ENTRYPOINT
├── Makefile                   # make build / run-shell / dev-shell (container only)
├── cli/zptv/                  # Typer CLI (app.py, runner.py)
├── meta/runtime.yml           # requires_ansible >=2.15
├── requirements.yml           # community.general (proxmoxer is pip-only)
├── .yamllint.yml
├── .github/workflows/         # lint.yml + release-tag.yml + release.yml
├── playbooks/                 # 5 playbooks: preflight, build_template, provision, reset, destroy
├── inventory/
│   ├── hosts.yml              # single proxmox host
│   ├── vault.example.yml      # API token, ISO sources, SSH pubkey
│   └── group_vars/all/main.yml
├── docs/
│   ├── runbook.md
│   └── dgx-os-install.md
└── roles/
    ├── proxmox_preflight/     # API check + invokes proxmox_host_vfio + GPU vfio check
    ├── proxmox_host_vfio/     # IOMMU cmdline + vfio modules + binding + blacklist
    ├── dgx_os_iso/            # Ensure ISO on node (resolve / upload / download)
    ├── vm_template_build/     # Autoinstall seed ISO + q35/OVMF template VM
    ├── vm_provision/          # Clone template -> active VM, snapshot 'fresh'
    ├── vm_reset/              # Rollback to 'fresh' snapshot
    └── vm_destroy/            # Stop + delete active VM
```

## Operator flow

All operator actions go through the `zptv` CLI (Typer, baked into the
container as ENTRYPOINT, also `pip install -e .`-able on the host).
The Makefile only manages the container.

```
zptv preflight       # one-time per node; vfio + GPU binding
zptv build-template  # one-time per DGX OS release; ~30-60 min
zptv provision       # each zdgx iteration; clone + snapshot 'fresh'
zptv reset           # roll back between zdgx site runs (~30s)
zptv destroy         # tear the active VM down
```

`zptv --help` lists every subcommand. Common global options:
`-i/--inventory`, `--vault-password-file`, `--limit`, `--check`, `-v`,
`-e/--extra-vars`.

## Relation to zelos.dgx

The VM `zptv provision` produces is reachable at `ubuntu@10.0.0.10`
with the SSH key from `vault_vm_ssh_pubkey`. That is exactly the
contract codified in `kmechlin/zelos.dgx`'s
`inventory/bootstrap.example.yml`, so:

```
cd zelos.dgx
cp inventory/bootstrap.example.yml inventory/bootstrap.yml
zdgx bootstrap
zdgx site
```

No inventory emission step is needed. The integration touchpoint lives
in the operator workflow, not in this collection's CI.

## Git / Workflow

### Branch model

- `main` is the protected release line. Every merge to `main` is a
  release and gets tagged `v<major>.<minor>.<patch>` automatically by
  `.github/workflows/release-tag.yml`, which reads the version from
  `galaxy.yml`. **`galaxy.yml` is the source of truth.**
- `develop` is the integration line. Features land here continuously.
- Feature branches are named `feature/<plan-name>` (or session-specific
  `claude/...` branches) and cut from the live tip of `origin/develop`.
  Never reuse a feature branch from a previous plan.

### Starting a plan

```
git fetch origin
git checkout -b feature/<plan-name> origin/develop
```

Never start work directly on `develop` or `main`.

### Completing a plan (feature -> develop)

1. Commit with clear, descriptive messages.
2. Push: `git push -u origin feature/<plan-name>`.
3. Open a PR into `develop` with a Summary + Test plan body. Do this
   without waiting to be asked.
4. Enable auto-merge with squash. The required `lint` check
   (yamllint + ansible-lint + syntax-check) gates the merge.
5. If CI fails, fix on the same branch and let auto-merge retry.
   Never force-merge.

### Cutting a release (develop -> main)

Only when the user explicitly asks.

1. Inspect what's landed: `git log v<last-tag>..origin/develop`.
2. Propose a semver bump from `galaxy.yml`'s `version:`:
   - **patch** — bug fixes, doc updates, internal cleanup.
   - **minor** — new roles, new playbooks, new configuration knobs.
   - **major** — breaking changes to inventory variables, role
     interfaces, or operator-facing commands.
3. Branch `release/v<X.Y.Z>` from `origin/develop`, bump `galaxy.yml`'s
   `version:`, PR into `develop`, auto-merge.
4. Then PR `develop` -> `main`. Title: `Release v<X.Y.Z>`. **Never
   auto-merge.** Use a *merge commit* (not squash) so the release
   boundary is a single visible merge on main.
5. `release-tag.yml` then auto-tags and publishes the GitHub Release.

### Hard rules

- Never PR a feature branch directly into `main`.
- Never push directly to `develop` or `main`.
- Never auto-merge anything into `main`.

### Container builds

`.github/workflows/release.yml` builds multi-arch images (linux/amd64
+ linux/arm64) and pushes to `ghcr.io/zelosai/zelos.dgx-proxmox-test-vm`
on every push to `develop`, `main`, and every `v*` tag. Tags applied:

- **develop push** → `:v<X.Y.Z>-dev` · `:latest` · `:sha-<short>`
- **main push** → `:v<X.Y.Z>` · `:latest` · `:stable` · `:sha-<short>`
- **`v<X.Y.Z>` tag push** → same as main + validates tag matches
  `galaxy.yml`'s version (build fails if they diverge).

The GHCR org `zelosai` is hardcoded in the workflow regardless of the
GitHub repo owner. This is the house brand.

## Notes / Blockers

- Repo MCP scope is restricted to `kmechlin/zelos.dgx-proxmox-test-vm`.
- This collection is at `0.1.0`. Bump in `galaxy.yml` on each material
  change; tag releases as `v0.1.0`, `v0.2.0`, etc.
- DGX OS ISO requires an NVIDIA Enterprise Support entitlement. There
  is no Ubuntu-overlay fallback in this collection by design.
