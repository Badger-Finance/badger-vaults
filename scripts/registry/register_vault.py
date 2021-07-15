from scripts.connect_account import connect_account
from brownie import BadgerRegistry, web3
import click
from eth_utils import is_checksum_address



def get_address(msg: str, default: str = None) -> str:
    val = click.prompt(msg, default=default)

    # Keep asking user for click.prompt until it passes
    while True:

        if is_checksum_address(val):
            return val
        elif addr := web3.ens.address(val):
            click.echo(f"Found ENS '{val}' [{addr}]")
            return addr

        click.echo(
            f"I'm sorry, but '{val}' is not a checksummed address or valid ENS record"
        )
        # NOTE: Only display default once
        val = click.prompt(msg)

def register_vault():
    """
    Register a vault in the registry
    """
    dev = connect_account()

    registry_address = get_address("Register Address")
    vault_address = get_address("Vault Address")

    registry = BadgerRegistry.at(registry_address)
    registry.add(vault_address, {"from": dev})
    
    click.echo("Added vault '{vault_address}' to registry!")
    

def main():
    tx = register_vault()
    return tx

