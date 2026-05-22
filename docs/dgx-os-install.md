# DGX OS install design notes

## Why autoinstall (NoCloud), not PXE

Per NVIDIA's DGX OS 6/7 user guides, the DGX OS ISO ships sample
autoinstall files (Ubuntu's subiquity / cloud-init format) containing
`CHANGE_*` placeholders. PXE boot is supported too, but it requires
TFTP + DHCP infrastructure on the Proxmox node. NoCloud seed ISO is
just an extra CD-ROM and works on any single-node Proxmox install with
no extra services.

## How the seed ISO is produced

`vm_template_build/build_seed_iso.yml` runs on the Proxmox node:

1. Renders `user-data`, `meta-data`, `network-config` from the
   operator's variables into `/tmp/zptv-seed-<vm_name>/`.
2. Runs `genisoimage -output ... -volid CIDATA -joliet -rock`
   to create the seed ISO at `/var/lib/vz/template/iso/<vm_name>-seed.iso`.
3. The template VM is created with two CD-ROMs attached:
   `ide2 = <dgx_os_iso>` and `ide3 = local:iso/<vm_name>-seed.iso`.
   The DGX OS installer detects the `CIDATA` volume and reads
   `user-data` automatically. No prompts.

## DGX OS 6 vs 7

`dgx_os_version: "7"` (default) targets DGX OS 7 / Ubuntu 24.04 noble.
`"6"` targets DGX OS 6 / Ubuntu 22.04 jammy. The `user-data.j2`
template branches off this variable for any version-specific knobs.
The ISO you upload must match: the role doesn't validate version
agreement against the ISO contents.

## Expected first-boot noise

DGX OS is designed for real DGX hardware. A handful of services
complain on a Proxmox VM, all harmlessly:

- **BMC / SBIOS health checks** report errors because there's no IPMI
  on a Proxmox VM. The driver, `nvidia-smi`, and CUDA still work
  against the passed-through A6000.
- **`nvidia-fabricmanager`** ships and starts on DGX OS but has nothing
  to manage on a single-GPU VM. It exits with "no NVSwitches found".
  `zelos.dgx` does not depend on it.

Document these in your zelos.dgx debugging notes so you don't chase
them when they reappear after every `zptv reset`.

## Entitlement requirement

The DGX OS ISO itself is entitlement-gated by NVIDIA Enterprise
Support. There is no fallback path in this collection -- if you don't
have the ISO, you can't run `zptv build-template`. The `dgx_os_iso`
role checks for the ISO and fails fast with an actionable error
message if no source is configured.

If you need to test the rest of the `zelos.dgx` flow without an
entitlement, you'll need to scaffold a parallel collection that
installs vanilla Ubuntu + the NVIDIA driver. That's out of scope here.

## What `late-commands` does

The autoinstall payload disables cloud-init on the installed disk so
the VM doesn't re-personalize on every boot. Without that, the
still-attached NoCloud seed ISO would be re-read each time and reset
hostname/users/keys.

After `zptv build-template` converts the VM to a template, the seed
ISO is detached anyway -- but disabling cloud-init in the image keeps
the snapshot semantics clean: `zptv reset` returns to exactly the
post-install state, no first-boot logic to worry about.
