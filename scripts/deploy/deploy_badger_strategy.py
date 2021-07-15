from pathlib import Path
from scripts.connect_account import connect_account
from scripts.deploy.deploy_badger_vault import deploy_vault
import yaml
import click

from brownie import TestStrategyUpgradeable, AdminUpgradeabilityProxy, web3, Vault
from eth_utils import is_checksum_address

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent / "ethpm-config.yaml").read_text()
)["version"]

defaults = {  # TODO: Use Badger on-chain Registry for all versions & defaults
    'stratLogic': web3.toChecksumAddress("0x0000000000000000000000000000000000000000"),
    'proxyAdmin': web3.toChecksumAddress("0xB10b3Af646Afadd9C62D663dd5d226B15C25CdFA"),
    'strategist': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
    'rewards': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
    'keeper': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
}


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

def deploy_strategy_logic(logic):
    """
    Deploy the strat logic
    """
    dev = connect_account()

    click.echo(
        f"""
        Release Information

         local package version: {PACKAGE_VERSION}
        """
    )

    if click.confirm("Deploy Logic Contracts", default="Y"):
        use_existing_logic = False
    else:
        # use_existing_logic = True
        # strat_logic_address = get_address("Strat Logic Address", default=defaults['stratLogic'])
        use_existing_logic = False
        click.echo(
            "Existing Vault Logic not supported, defaulting Deploy Logic Contracts to 'Yes'")
    if click.confirm("Deploy New Vault", default="Y"):
        vault = deploy_vault(dev)
        click.echo(f"Using new Vault {vault.name()} at {vault.address}")
    else: 
        vault = Vault.at(get_address("Strat Vault"))

    proxyAdmin = get_address("Proxy Admin", default=defaults['proxyAdmin'])
    rewards = get_address("Rewards contract", default=defaults['rewards'])
    strategist = get_address("Strategist Address",
                             default=defaults['strategist'])
    keeper = get_address("Keeper Address", default=defaults['keeper'])

    click.echo(
        f"""
    Strat Deployment Parameters

         use proxy: {True}
    target release: {PACKAGE_VERSION} # TODO: Use Badger Registry for all versions & defaults
              vault: '{vault}'
            proxyAdmin: '{proxyAdmin}'

            rewards: '{rewards}'
            strategist: '{strategist}'
            keeper: '{keeper}'
    """
    )

    if click.confirm("Deploy New Strategy"):
        args = [
            vault,
            strategist,
            rewards,
            keeper
        ]

        strat_logic = logic.deploy({'from': dev})
        strat_proxy = AdminUpgradeabilityProxy.deploy(strat_logic, proxyAdmin, strat_logic.initialize.encode_input(*args), {'from': dev})
        ## We delete from deploy and then fetch again so we can interact
        AdminUpgradeabilityProxy.remove(strat_proxy)
        strat_proxy = logic.at(strat_proxy.address)

        print(strat_proxy)
        print(dir(strat_proxy))
        print("Strat Args", args)
        click.echo(f"New Strategy Release deployed [{strat_proxy.address}]")
        click.echo(
            "    NOTE: Strategy is not registered in Registry, please register!"
        )

        return strat_proxy

def main():
    strat = deploy_strategy_logic(TestStrategyUpgradeable)
    return strat

