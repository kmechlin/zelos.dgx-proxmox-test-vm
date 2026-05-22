# zelos.dgx-proxmox-test-vm

Proxmox VM test target for the
[`zelos.dgx`](https://github.com/kmechlin/zelos.dgx) Ansible collection.
Builds, snapshots, resets, and destroys a single DGX OS VM with GPU
passthrough as a repeatable baseline for `zelos.dgx` iteration.

This is sister tooling, **not** part of the `zelos.<hosttype>`
provisioner series. It exists so each `zdgx site` development cycle
starts from the same disposable baseline.

## What it does

Five operator commands (via the `zptv` CLI baked into the container):

```
zptv preflight       # Configure vfio-pci on the Proxmox host; verify API
zptv build-template  # One-time. Resolves DGX OS ISO, autoinstalls a VM,
                     # converts to a Proxmox template. ~30-60 min.
zptv provision       # Clone the template to the active test VM, attach
                     # GPU passthrough, snapshot it as 'fresh'.
zptv reset           # Roll the active VM back to 'fresh' in <30s.
zptv destroy         # Stop and delete the active VM.
```

The produced VM is reachable at `ubuntu@10.0.0.10`, which matches the
default `inventory/bootstrap.example.yml` that ships with `zelos.dgx`.
No inventory emission is needed -- `zdgx bootstrap` works out of the
box against the VM `zptv provision` builds.

## Requirements

- Proxmox 8.x node with an NVIDIA GPU physically installed.
- Root SSH access from the control node + a Proxmox API token.
- DGX OS ISO (entitlement-gated via NVIDIA Enterprise Support). Supply
  it pre-staged on the node, via a local path on the control node, or
  via a signed URL with auth headers. See `docs/runbook.md`.

## Layout

```
zelos.dgx-proxmox-test-vm/
├── ansible.cfg                # standard zelos.dgx ansible.cfg
├── galaxy.yml                 # namespace=zelos, name=dgx_proxmox_test_vm
├── pyproject.toml             # zptv CLI package
├── Dockerfile                 # python:3.12-slim + ansible + zptv ENTRYPOINT
├── Makefile                   # make build / run-shell / dev-shell
├── cli/zptv/                  # Typer CLI source (app.py, runner.py)
├── playbooks/                 # 5 playbooks, one per zptv subcommand
├── roles/
│   ├── proxmox_preflight/     # API check + invokes proxmox_host_vfio
│   ├── proxmox_host_vfio/     # IOMMU cmdline + vfio modules + binding
│   ├── dgx_os_iso/            # Ensure ISO on node (resolve/upload/download)
│   ├── vm_template_build/     # Autoinstall seed ISO + template creation
│   ├── vm_provision/          # Clone template + snapshot 'fresh'
│   ├── vm_reset/              # Rollback to 'fresh'
│   └── vm_destroy/            # Delete active VM
├── inventory/
│   ├── hosts.yml              # Proxmox node entry
│   ├── vault.example.yml      # API token, ISO sources, SSH pubkey
│   └── group_vars/all/main.yml
├── docs/
│   ├── runbook.md             # operator one-time prep + cycle
│   └── dgx-os-install.md      # autoinstall + DGX OS noise notes
└── .github/workflows/         # lint + release-tag + multi-arch release
```

## How to run

The recommended workflow is the container (it pins Ansible and ships
`zptv` as the ENTRYPOINT):

```
git clone https://github.com/kmechlin/zelos.dgx-proxmox-test-vm.git
cd zelos.dgx-proxmox-test-vm
cp inventory/vault.example.yml inventory/group_vars/all/vault.yml
$EDITOR inventory/group_vars/all/vault.yml          # api token, iso source, ssh key
ansible-vault encrypt inventory/group_vars/all/vault.yml
$EDITOR inventory/hosts.yml                         # set ansible_host to the proxmox node
make build
make run-shell
# inside the container:
zptv --help
zptv preflight -e proxmox_host_vfio_allow_reboot=true
zptv build-template
zptv provision
```

Full operator docs in [`docs/runbook.md`](docs/runbook.md). Design
notes for the DGX OS install in
[`docs/dgx-os-install.md`](docs/dgx-os-install.md).

## State

v0.1.0 scaffold. **Not yet validated against real hardware.** Expect
to iterate on the first `zptv preflight` / `zptv build-template`
against a live Proxmox node.

## License

Apache-2.0.
