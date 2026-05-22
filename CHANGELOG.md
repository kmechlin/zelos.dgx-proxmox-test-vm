# Changelog

All notable changes to the `zelos.dgx_proxmox_test_vm` Ansible collection are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this collection adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Released versions are tagged in the source repository as `v<major>.<minor>.<patch>` and published as GitHub Releases with auto-generated notes; this file is the curated human-readable summary.

## [Unreleased]

### Added
- Initial scaffold of the collection. Five operator commands via the `zptv` Typer CLI: `preflight`, `build-template`, `provision`, `reset`, `destroy`, plus the `deps`/`lint`/`syntax`/`ping` hygiene set.
- Roles:
  - `proxmox_preflight` — Proxmox API reachability check; invokes `proxmox_host_vfio`; verifies the target GPU is bound to vfio-pci.
  - `proxmox_host_vfio` — Configures IOMMU on the kernel cmdline (systemd-boot or GRUB), loads vfio modules at boot, binds target PCI IDs to vfio-pci, blacklists nouveau/nvidia/nvidiafb. Opt-in host reboot via `proxmox_host_vfio_allow_reboot`.
  - `dgx_os_iso` — Resolves the DGX OS ISO onto the Proxmox node. Priority order: already present → upload from control node → fetch via `get_url` with custom headers (NVIDIA Enterprise Support auth) → fail fast.
  - `vm_template_build` — Renders Ubuntu autoinstall payload, builds a NoCloud seed ISO via `genisoimage`, creates a q35/OVMF/virtio-scsi template VM, waits 30-60 min for autoinstall, detaches install media, converts to a Proxmox template.
  - `vm_provision` — Clones the template into the active test VM, attaches GPU passthrough, snapshots it as `fresh`.
  - `vm_reset` — Stops the active VM, rolls back to `fresh`, restarts.
  - `vm_destroy` — Stops and deletes the active test VM.
- Containerised control node: `Dockerfile` (python:3.12-slim + ansible 9.5.1 + ansible-lint 24.2.1 + yamllint 1.35.1 + proxmoxer + zptv via `pip install -e`), `Makefile` (build/run-shell/dev-shell), `.yamllint.yml` and `ansible.cfg` mirrored from `zelos.dgx`.
- CI: `.github/workflows/lint.yml` (yamllint + ansible-lint + per-playbook --syntax-check), `release-tag.yml` (auto-tags `v<X.Y.Z>` from `galaxy.yml` on each `main` push), `release.yml` (multi-arch GHCR image at `ghcr.io/zelosai/zelos.dgx-proxmox-test-vm`).
- Operator documentation: `docs/runbook.md`, `docs/dgx-os-install.md`.

## [0.1.0] - Initial scaffold

- First scaffold of the collection. Not yet validated against real hardware.
