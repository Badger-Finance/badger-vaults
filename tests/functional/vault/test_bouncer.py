import pytest
import brownie 
import json
from brownie import ZERO_ADDRESS, chain, web3, accounts

# with open('merkle/merkle_guestlist_test.json') as f:
#     testDistribution = json.load(f)

@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Overriding the one in conftest because it has values already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, "", "", gov
    )
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    yield vault


def test_bouncer_permissions(gov, rando, badgerBouncer, vault):
    # Check that gov is owner (deployer of badgerBouncer):
    assert gov.address == badgerBouncer.owner()

    # Only owner can set guests
    with brownie.reverts():
        badgerBouncer.setVaultGuests(vault.address, [rando.address], [True], {"from": rando})

    badgerBouncer.setVaultGuests(vault.address, [rando.address], [True], {"from": gov})
    assert badgerBouncer.vaultGuests(vault.address, rando.address) == True

    # Only owner can set default guestRoot
    with brownie.reverts():
        badgerBouncer.setDefaultGuestListRoot(
            "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a", 
            {"from": rando}
        )

    badgerBouncer.setDefaultGuestListRoot(
        "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a", 
        {"from": gov}
    )
    assert badgerBouncer.defaultGuestListRoot() == "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a"


    # Only owner can set vault's guestRoot
    with brownie.reverts():
        badgerBouncer.setRootForVault(
            vault.address,
            "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a", 
            {"from": rando}
        )

    badgerBouncer.setRootForVault(
        vault.address,
        "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a", 
        {"from": gov}
    )
    assert badgerBouncer.guestListRootOverride(vault.address) == "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a"
    assert badgerBouncer.removedGuestList(vault.address) == False

    # Only owner can remove vault's guestRoot
    with brownie.reverts():
        badgerBouncer.removeRootForVault(vault.address, {"from": rando})

    badgerBouncer.removeRootForVault(vault.address, {"from": gov})

    assert badgerBouncer.guestListRootOverride(vault.address) == "0x0"
    assert badgerBouncer.removedGuestList(vault.address) == True

    # Only owner can ban an address
    with brownie.reverts():
        badgerBouncer.banAddress(rando.address, {"from": rando})

    badgerBouncer.banAddress(rando.address, {"from": gov})

    assert badgerBouncer.isBanned(rando.address) == True

    # Only owner can unban an address
    with brownie.reverts():
        badgerBouncer.unbanAddress(rando.address, {"from": rando})

    badgerBouncer.unbanAddress(rando.address, {"from": gov})

    assert badgerBouncer.isBanned(rando.address) == False

    # Only owner can set userDepositCap
    with brownie.reverts():
        badgerBouncer.setUserDepositCap(vault.address, 1e18, {"from": rando})

    badgerBouncer.setUserDepositCap(vault.address, 1e18, {"from": gov})
    assert badgerBouncer.userCaps(vault.address) == 1e18

    # Only owner can set totalDepositCap
    with brownie.reverts():
        badgerBouncer.setTotalDepositCap(vault.address, 100e18, {"from": rando})

    badgerBouncer.setTotalDepositCap(vault.address, 100e18, {"from": gov})
    assert badgerBouncer.totalCaps(vault.address) == 100e18



def test_manual_bouncer_flow(gov, rando, vault, token, badgerBouncer):
    # Approve access of badgerBouncer to vault
    vault.approveContractAccess(badgerBouncer.address, {"from": gov})

    # User can deposit while badgerBouncer == Address Zero
    balance = token.balanceOf(gov)
    token.transfer(rando.address, balance, {"from": gov})
    token.approve(badgerBouncer.address, balance * 100, {"from": rando})

    chain.sleep(10)
    chain.mine()

    # Set userDepositCap
    badgerBouncer.setUserDepositCap(vault.address, balance, {"from": gov})
    assert badgerBouncer.userCaps(vault.address) == balance

    # Set totalDepositCap
    badgerBouncer.setTotalDepositCap(vault.address, 2 ** 256 - 1, {"from": gov})
    assert badgerBouncer.totalCaps(vault.address) == 2 ** 256 - 1

    chain.sleep(10)
    chain.mine()

    # User, not in guestlist, can deposit since guestRoot == 0x0 and default guestRoot == 0x0
    assert badgerBouncer.vaultGuests(vault.address, rando.address) == False
    badgerBouncer.deposit(vault.address, balance // 4, {"from": rando})

    assert token.balanceOf(vault) == balance // 4
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price
    assert vault.balanceOf(rando.address) == balance // 4

    chain.sleep(10)
    chain.mine()

    # Set default guestRoot
    badgerBouncer.setDefaultGuestListRoot(
        "0xc8eb7b9a26b0681320a4f6db1c93891f573fa496b6a99653f11cba4616899027", 
        {"from": gov}
    )
    assert badgerBouncer.defaultGuestListRoot() == "0xc8eb7b9a26b0681320a4f6db1c93891f573fa496b6a99653f11cba4616899027"

    # User, not in guestlist, can't deposit since defaultGuestRoot is set
    assert badgerBouncer.vaultGuests(vault.address, rando.address) == False
    with brownie.reverts():
        badgerBouncer.deposit(vault.address, balance // 4, {"from": rando})

    # Set default guestRoot to 0x0
    badgerBouncer.setDefaultGuestListRoot("0x0", {"from": gov})

    # Set vault's guestRoot
    badgerBouncer.setRootForVault(
        vault.address,
        "0xc8eb7b9a26b0681320a4f6db1c93891f573fa496b6a99653f11cba4616899027", 
        {"from": gov}
    )
    assert badgerBouncer.guestListRootOverride(vault.address) == "0xc8eb7b9a26b0681320a4f6db1c93891f573fa496b6a99653f11cba4616899027"

    # Even if guestRoot is set to 0x0 user, not in guestlist, can't deposit since vault guestRoot is set
    assert badgerBouncer.vaultGuests(vault.address, rando.address) == False
    with brownie.reverts():
        badgerBouncer.deposit(vault.address, balance // 4, {"from": rando})

    # User, not in guestlist, can withdraw
    vault.withdraw(balance // 4, {"from": rando})
    assert vault.balanceOf(rando.address) == 0
    assert token.balanceOf(rando.address) == balance

    chain.sleep(10)
    chain.mine()

    # User is added to badgerBouncer manually
    badgerBouncer.setVaultGuests(vault.address, [rando.address], [True], {"from": gov})
    assert badgerBouncer.vaultGuests(vault.address, rando.address) == True

    chain.sleep(10)
    chain.mine()

    # User, manually added to the badgerBouncer, can deposit
    badgerBouncer.deposit(vault.address, balance // 4, {"from": rando})

    assert token.balanceOf(vault) == balance // 4
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price
    assert vault.balanceOf(rando.address) == balance // 4

    # User gets banned
    badgerBouncer.banAddress(rando.address, {"from": gov})

    # Banned user can't deposit
    with brownie.reverts():
        badgerBouncer.deposit(vault.address, balance // 4, {"from": rando})

    # User gets banned
    badgerBouncer.unbanAddress(rando.address, {"from": gov})

    # Unbanned user can deposit while on the guestlist
    badgerBouncer.deposit(vault.address, balance // 4, {"from": rando})

    assert token.balanceOf(vault) == balance // 2
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price
    assert vault.balanceOf(rando.address) == balance // 2

    # User is removed from badgerBouncer manually
    badgerBouncer.setVaultGuests(vault.address, [rando.address], [False], {"from": gov})
    assert badgerBouncer.vaultGuests(vault.address, rando.address) == False

    chain.sleep(10)
    chain.mine()

    # User removed from guestlist can't deposit
    with brownie.reverts():
        badgerBouncer.deposit(vault.address, balance // 4, {"from": rando})

    # Remove guestRoot for vault
    badgerBouncer.removeRootForVault(vault.address, {"from": gov})
    assert badgerBouncer.guestListRootOverride(vault.address) == "0x0"
    assert badgerBouncer.removedGuestList(vault.address) == True

    # User, not on guestlist, can deposit since guestRoot for vault is set to 0x0 and 
    # removedGuestList flag is set to True
    badgerBouncer.deposit(vault.address, balance // 2, {"from": rando})

    assert token.balanceOf(vault) == balance
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price
    assert vault.balanceOf(rando.address) == balance





# def test_merkle_guestlist_flow(gov, rando, vault, token, badgerBouncer):
#     balance = token.balanceOf(gov)

#     # Set guestRoot equal to merkleRoot
#     merkleRoot = testDistribution["merkleRoot"]
#     badgerBouncer.setGuestRoot(merkleRoot, {"from": gov})

#     badgerBouncer.setUserDepositCap(balance, {"from": gov})
#     assert badgerBouncer.userDepositCap() == balance


#     # Test merkle verification upon deposit
#     users = [
#         web3.toChecksumAddress("0x8107b00171a02f83D7a17f62941841C29c3ae60F"),
#         web3.toChecksumAddress("0x716722C80757FFF31DA3F3C392A1736b7cfa3A3e"),
#         web3.toChecksumAddress("0xE2e4F2A725E42D0F0EF6291F46c430F963482001"),
#     ]

#     for user in users:
#         user = accounts.at(user, force=True)

#         claim = testDistribution["claims"][user]
#         proof = claim["proof"]

#         # Gov transfers tokens to user
#         token.transfer(user.address, balance // 6, {"from": gov})
#         token.approve(vault, balance, {"from": user})

#         vault.deposit(balance // 6, user.address, proof, {"from": user})
#         assert vault.balanceOf(user.address) == balance // 6 # Since 1:1 price


#     # Test depositing after proveInvitation of a few users
#     users = [
#         web3.toChecksumAddress("0x1fafb618033Fb07d3a99704a47451971976CB586"),
#         web3.toChecksumAddress("0xCf7760E00327f608543c88526427b35049b58984"),
#         web3.toChecksumAddress("0xb43b8B43dE2e59A2B44caa2910E31a4E835d4068"),
#     ]

#     for user in users:
#         user = accounts.at(user, force=True)

#         claim = testDistribution["claims"][user]
#         proof = claim["proof"]

#         # Gov transfers tokens to user
#         token.transfer(user.address, balance // 6, {"from": gov})
#         token.approve(vault, balance, {"from": user})

#         tx = badgerBouncer.proveInvitation(user.address, proof)
#         assert tx.events[0]["guestRoot"] == merkleRoot
#         assert tx.events[0]["account"] == user.address

#         # User deposits 1 token through wrapper (without proof)
#         vault.deposit(balance // 6, {"from": user})
#         assert vault.balanceOf(user.address) == balance // 6 # Since 1:1 price