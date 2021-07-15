from scripts.connect_account import connect_account

from brownie import BadgerRegistry


def deploy_registry():
    """
    Deploy the Registry logic
    """
    dev = connect_account()

    return BadgerRegistry.deploy({"from": dev})

    

def main():
    registry = deploy_registry()
    return registry

