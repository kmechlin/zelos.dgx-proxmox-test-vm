# Runbook

End-to-end operator flow for `zelos.dgx-proxmox-test-vm`.

## One-time setup

### 1. Proxmox node

You need a Proxmox 8.x host with:

- An NVIDIA GPU (e.g. RTX A6000) physically installed.
- Root SSH access from your control node.
- A Proxmox API token (Datacenter -> Permissions -> API Tokens, give it
  `PVEVMAdmin` on `/` and `Datastore.Allocate`/`Datastore.AllocateSpace`
  on the storage you'll use).

Identify the GPU's PCI IDs:

```
lspci -nn | grep -i nvidia
# Example:
#   01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA102GL [RTX A6000] [10de:2230]
#   01:00.1 Audio device [0403]: NVIDIA Corporation GA102 HDMI Audio Controller [10de:1aef]
```

Record the BDF addresses (`0000:01:00.0`, `0000:01:00.1`) and the
vendor:device IDs (`10de:2230`, `10de:1aef`).

### 2. Control node

You need a host that can reach the Proxmox API and SSH to the Proxmox
node. Use the container shipped with this collection:

```
git clone https://github.com/kmechlin/zelos.dgx-proxmox-test-vm.git
cd zelos.dgx-proxmox-test-vm
cp inventory/vault.example.yml inventory/group_vars/all/vault.yml
$EDITOR inventory/group_vars/all/vault.yml          # fill in the API token, ISO source, SSH pubkey, etc.
ansible-vault encrypt inventory/group_vars/all/vault.yml
$EDITOR inventory/hosts.yml                         # set ansible_host to your Proxmox node IP
make build
make run-shell                                      # or `make dev-shell` for live edits
```

### 3. DGX OS ISO

The DGX OS ISO is entitlement-gated. You can supply it via any of
these (in priority order):

1. **Pre-stage:** drop the ISO into `local:iso/` on the Proxmox node
   yourself (e.g. via the Proxmox web UI's "Upload" button).
2. **Local source:** set `vault_dgx_os_iso_local_source` to an absolute
   path on the control node. `zptv build-template` will upload it.
3. **Signed URL:** set `vault_dgx_os_iso_url` and
   `vault_dgx_os_iso_url_headers` (e.g. `Authorization: Bearer ...`).
   `zptv build-template` will fetch it directly to the node.

Always set `vault_dgx_os_iso_sha256` if you know the published hash --
it gates the upload / download.

## Each session

```
# One-time per Proxmox node. Configures host vfio-pci; reboots if you allow it.
zptv preflight -e proxmox_host_vfio_allow_reboot=true

# One-time per DGX OS release. ~30-60 minutes (autoinstall).
zptv build-template

# Each zdgx iteration:
zptv provision          # clone template -> dgx-test, snapshot 'fresh'
# ... run `zdgx bootstrap` then `zdgx site` against ubuntu@10.0.0.10 ...
zptv reset              # roll back to 'fresh' between runs (~30s)

# When done with the test cycle:
zptv destroy            # active VM goes away; template is left intact
```

## Integration with `zelos.dgx`

The VM `zptv provision` produces is reachable at `ubuntu@10.0.0.10`
with the SSH key from `vault_vm_ssh_pubkey`. That matches the contract
in `kmechlin/zelos.dgx`'s `inventory/bootstrap.example.yml`, so:

```
cd ../zelos.dgx
cp inventory/bootstrap.example.yml inventory/bootstrap.yml
zdgx bootstrap                                      # creates `ansible` user
zdgx site                                           # full provision
```

Iterate: `zptv reset` -> `zdgx site` -> debug -> `zptv reset` -> `zdgx
site` -> ...

## Recovery

- VM stuck after `zdgx site`: `zptv reset`.
- VM gone weird below the snapshot (e.g. corrupted): `zptv destroy`
  then `zptv provision`.
- DGX OS upgrade or template corruption: delete VMID 9000 from Proxmox
  manually, then `zptv build-template` again.
