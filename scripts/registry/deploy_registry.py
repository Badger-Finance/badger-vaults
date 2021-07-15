from scripts.connect_account import connect_account

from brownie import BadgerRegistry

governance: web3.toChecksumAddress("0x55949f769d0af7453881435612561d109fff07b8")


def deploy_registry():
    """
    Deploy the Registry logic
    """
    dev = connect_account()

    return BadgerRegistry.deploy(gov, {"from": dev})

    

def main():
    registry = deploy_registry()
    return registry

