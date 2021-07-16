import brownie
from brownie import ZERO_ADDRESS, accounts

def test_user_can_add_remove_vault(badgerRegistry, vault, rando, gov):
    # Author adds vault to their list
    tx = badgerRegistry.add(vault.address, {"from": rando})
    assert badgerRegistry.fromAuthor(rando.address) == [vault.address]

    event = tx.events["NewVault"][0]
    assert event["vault"] == vault.address

    # Same vault cannot be added twice (nothing happens)
    tx = badgerRegistry.add(vault.address, {"from": rando})
    assert len(tx.events) == 0

    # Only author can remove vault from their list (nothing happens)
    tx = badgerRegistry.remove(vault.address, {"from": gov})
    assert len(tx.events) == 0
    

    # Author attempts to remove vault with address not on list (nothing happens)
    tx = badgerRegistry.remove(ZERO_ADDRESS, {"from": gov})
    assert len(tx.events) == 0

    # Author can remove their own vault from list
    tx = badgerRegistry.remove(vault.address, {"from": rando})
    assert badgerRegistry.fromAuthor(rando.address) == []

    event = tx.events["RemoveVault"][0]
    assert event["vault"] == vault.address



def test_user_can_add_remove_multiple_vaults(badgerRegistry, create_vault, create_token, rando):
    # Author creates and adds vault1 to registry
    token1 = create_token()
    vault1 = create_vault(token1, version="1.0.0")

    badgerRegistry.add(vault1.address, {"from": rando})
    assert badgerRegistry.fromAuthor(rando.address) == [vault1.address]

    # Author creates and adds vault2 to registry
    token2 = create_token()
    vault2 = create_vault(token2, version="1.0.0")

    badgerRegistry.add(vault2.address, {"from": rando})
    assert badgerRegistry.fromAuthor(rando.address) == [vault1.address, vault2.address]

    # Author creates and adds vault3 to registry
    token3 = create_token()
    vault3 = create_vault(token3, version="1.0.0")

    badgerRegistry.add(vault3.address, {"from": rando})
    assert badgerRegistry.fromAuthor(rando.address) == [vault1.address, vault2.address, vault3.address]

    # Author can remove their own vault from list
    tx = badgerRegistry.remove(vault1.address, {"from": rando})
    event = tx.events["RemoveVault"][0]
    assert event["vault"] == vault1.address
    
    # NOTE: Order of entries change when vaults are removed from sets
    assert badgerRegistry.fromAuthor(rando.address) == [vault3.address, vault2.address]



def test_view_functions(badgerRegistry, vault, strategy, rando):
    badgerRegistry.add(vault.address, {"from": rando})
    assert badgerRegistry.fromAuthor(rando.address) == [vault.address]

    assert badgerRegistry.fromAuthorVaults(rando.address) == [
        [
            vault.address, 
            vault.name(), 
            vault.symbol(), 
            vault.token(), 
            vault.pendingGovernance(),
            vault.governance(),
            vault.rewards(),
            vault.guardian(),
            vault.management(),
            [],
        ],
    ]

    
    # The return value matches the expected but Brownie cannot handle parsing the Strategy name
    # due to the float values contained on it. To test, remove the appended apiVersion() from 
    # TestStrategy's name() function.

    # TODO: Adapt assertion to support comparison of strings containing floats

    # params = vault.strategies(strategy.address)

    # assert badgerRegistry.fromAuthorWithDetails(rando.address) == [
    #     [
    #         vault.address, 
    #         vault.name(), 
    #         vault.symbol(), 
    #         vault.token(), 
    #         vault.pendingGovernance(),
    #         vault.governance(),
    #         vault.rewards(),
    #         vault.guardian(),
    #         vault.management(),
    #         [
    #             [
    #                 strategy.address,
    #                 strategy.name(),
    #                 strategy.strategist(),
    #                 strategy.rewards(),
    #                 strategy.keeper(),
    #                 params[0], # performanceFee,
    #                 params[1], # activation,
    #                 params[2], # debtRatio,
    #                 params[3], # minDebtPerHarvest,
    #                 params[4], # maxDebtPerHarvest,
    #                 params[5], # lastReport,
    #                 params[6], # totalDebt,
    #                 params[7], # totalGain,
    #                 params[8], # totalLoss,
    #                 params[9], # enforceChangeLimit,
    #                 params[10], # profitLimitRatio,
    #                 params[11], # lossLimitRatio,
    #                 params[12], # customCheck
    #             ],
    #         ],
    #     ],
    # ]


def test_vault_promotion(badgerRegistry, vault, rando, gov):

    # Author adds vault to their list
    badgerRegistry.add(vault.address, {"from": rando})
    assert badgerRegistry.fromAuthor(rando.address) == [vault.address]

    # Random user attempts to promote vault and reverts
    with brownie.reverts():
        badgerRegistry.promote(vault.address, {"from": rando})

    # Governance is able to promote vault
    tx = badgerRegistry.promote(vault.address, {"from": gov})
    assert badgerRegistry.fromAuthor(gov) == [vault.address]

    event = tx.events["PromoteVault"][0]
    assert event["vault"] == vault.address

    # Same vault cannot be promoted twice (nothing happens)
    tx = badgerRegistry.promote(vault.address, {"from": gov})
    assert len(tx.events) == 0