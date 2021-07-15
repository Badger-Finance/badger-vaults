from scripts.connect_account import connect_account
from scripts.get_address import get_address
from brownie import BadgerRegistry, web3

defaults = {
    "governance": web3.toChecksumAddress("0x55949f769d0af7453881435612561d109fff07b8")
}

def deploy_registry():
    """
    Deploy the Registry logic
    """
    dev = connect_account()
    gov = get_address("Badger Governance for this network?", default=defaults['governance'])

    return BadgerRegistry.deploy(gov, {"from": dev})

    

def main():
    registry = deploy_registry()
    return registry

