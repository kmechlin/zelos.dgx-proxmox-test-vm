"""`zptv` Typer CLI -- operator entrypoint for the zelos.dgx-proxmox-test-vm collection."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from zptv.runner import (
    RunnerState,
    run_ansible_module,
    run_galaxy_install,
    run_playbook,
)

app = typer.Typer(
    name="zptv",
    help="Operator CLI for the zelos.dgx-proxmox-test-vm Ansible collection.",
    no_args_is_help=True,
    add_completion=True,
)

_state = RunnerState()


@app.callback()
def _root(
    ctx: typer.Context,
    inventory: Path = typer.Option(
        Path("inventory/hosts.yml"),
        "-i",
        "--inventory",
        help="Ansible inventory file.",
    ),
    vault_password_file: Optional[Path] = typer.Option(
        None,
        "--vault-password-file",
        help="Path to a file containing the vault password (non-interactive).",
    ),
    ask_vault_pass: bool = typer.Option(
        False,
        "--ask-vault-pass",
        help="Prompt for the vault password (default if no file is given).",
    ),
    limit: Optional[str] = typer.Option(
        None,
        "--limit",
        help="Limit execution to a host/group pattern.",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Dry run (ansible --check).",
    ),
    verbose: int = typer.Option(
        0,
        "-v",
        "--verbose",
        count=True,
        help="Increase ansible verbosity (-v / -vv / -vvv / -vvvv).",
    ),
    extra_var: list[str] = typer.Option(
        [],
        "-e",
        "--extra-vars",
        help='Extra vars passed to ansible-playbook (repeatable). e.g. -e "key=value".',
    ),
) -> None:
    """Shared options for every subcommand."""
    _state.inventory = inventory
    _state.vault_password_file = vault_password_file
    _state.ask_vault_pass = ask_vault_pass
    _state.limit = limit
    _state.check = check
    _state.verbose = verbose
    _state.extra_vars = list(extra_var)


# --- VM lifecycle ----------------------------------------------------------


@app.command(help="Verify Proxmox API reachability and configure host vfio-pci.")
def preflight() -> None:
    run_playbook(_state, "preflight.yml")


@app.command("build-template", help="Build the DGX OS VM template (autoinstall, ~30-60 min).")
def build_template() -> None:
    run_playbook(_state, "build_template.yml")


@app.command(help="Clone the template into the active test VM and snapshot it as 'fresh'.")
def provision() -> None:
    run_playbook(_state, "provision.yml")


@app.command(help="Roll the active test VM back to the 'fresh' snapshot.")
def reset() -> None:
    run_playbook(_state, "reset.yml")


@app.command(help="Stop and delete the active test VM.")
def destroy() -> None:
    run_playbook(_state, "destroy.yml")


# --- Hygiene ---------------------------------------------------------------


@app.command(help="ansible -m ping against every host in inventory.")
def ping() -> None:
    run_ansible_module(_state, "ping", pattern="all", become=False)


@app.command(help="Install required Ansible collections from requirements.yml.")
def deps(
    requirements: Path = typer.Option(
        Path("requirements.yml"),
        "--requirements",
        help="Path to the requirements.yml.",
    ),
) -> None:
    run_galaxy_install(requirements)


@app.command(help="Run yamllint and ansible-lint over the collection.")
def lint() -> None:
    yl = subprocess.run(["yamllint", "."])
    al = subprocess.run(["ansible-lint"])
    sys.exit(yl.returncode or al.returncode)


@app.command(help="ansible-playbook --syntax-check every playbook in playbooks/.")
def syntax() -> None:
    playbooks_dir = Path("playbooks")
    rc = 0
    for pb in sorted(playbooks_dir.glob("*.yml")):
        print(f"syntax: {pb}", flush=True)
        result = subprocess.run(
            ["ansible-playbook", "-i", str(_state.inventory), str(pb), "--syntax-check"]
        )
        if result.returncode != 0:
            rc = result.returncode
            break
    sys.exit(rc)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
