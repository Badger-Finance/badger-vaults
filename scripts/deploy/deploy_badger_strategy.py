"""
Note: This script should not be used in badger-vaults
It should be used in badger-vaults-mix-v2
"""
from pathlib import Path
from scripts.connect_account import connect_account
from scripts.get_address import get_address

from scripts.deploy.deploy_badger_vault import deploy_vault
import yaml
import click

from brownie import TestStrategyUpgradeable, AdminUpgradeabilityProxy, web3, Vault

PACKAGE_VERSION = yaml.safe_load(
    (Path(__file__).parent.parent.parent / "ethpm-config.yaml").read_text()
)["version"]

defaults = {  # TODO: Use Badger on-chain Registry for all versions & defaults
    'stratLogic': web3.toChecksumAddress("0x0000000000000000000000000000000000000000"),
    'proxyAdmin': web3.toChecksumAddress("0xB10b3Af646Afadd9C62D663dd5d226B15C25CdFA"),
    'strategist': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
    'rewards': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
    'keeper': web3.toChecksumAddress("0xB65cef03b9B89f99517643226d76e286ee999e77"),
}

def deploy_strategy_logic(logic):
    """
    Deploy the strat logic
    """
    dev = connect_account()

    vault = Vault.at(get_address("Specify Vault Address for the Strategy"))

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

        return strat_proxy

def main():
    strat = deploy_strategy_logic(TestStrategyUpgradeable)
    return strat

