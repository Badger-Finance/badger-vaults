import pytest
import brownie 
import json
from brownie import ZERO_ADDRESS, chain, web3, accounts


@pytest.fixture
def vault(gov, token, Vault):
    # NOTE: Overriding the one in conftest because it has values already
    vault = gov.deploy(Vault)
    vault.initialize(
        token, gov, gov, "", "", gov
    )
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    yield vault

def test_guestlist_permissions(gov, rando, guestlist):
    # Check that gov is owner (deployer of guestlist):
    assert gov.address == guestlist.owner()

    # Only owner can set guests
    with brownie.reverts():
        guestlist.setGuests([rando.address], [True], {"from": rando})
    
    guestlist.setGuests([rando.address], [True], {"from": gov})
    assert guestlist.guests(rando.address) == True

    # Only owner can set guestRoot
    with brownie.reverts():
        guestlist.setGuestRoot(
            "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a", 
            {"from": rando}
        )
    
    guestlist.setGuestRoot(
        "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a", 
        {"from": gov}
    )
    assert guestlist.guestRoot() == "0x1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a"

    # Only owner can set userDepositCap
    with brownie.reverts():
        guestlist.setUserDepositCap(1e18, {"from": rando})
    
    guestlist.setUserDepositCap(1e18, {"from": gov})
    assert guestlist.userDepositCap() == 1e18

    # Only owner can set totalDepositCap
    with brownie.reverts():
        guestlist.setTotalDepositCap(100e18, {"from": rando})
    
    guestlist.setTotalDepositCap(100e18, {"from": gov})
    assert guestlist.totalDepositCap() == 100e18

def test_manual_guestlist_flow(gov, rando, vault, token, guestlist):
    # guestList is the address zero by default
    assert vault.guestList() == ZERO_ADDRESS

    # User can deposit while guestlist == Address Zero
    balance = token.balanceOf(gov)
    token.transfer(rando.address, balance, {"from": gov})
    token.approve(vault, balance, {"from": rando})
    vault.deposit(balance // 2, {"from": rando})

    assert token.balanceOf(vault) == balance // 2
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price
    assert vault.balanceOf(rando.address) == balance // 2

    chain.sleep(10)
    chain.mine()

    # Only vault's governance can set guestslist
    with brownie.reverts():
        vault.setGuestList(guestlist.address, {"from": rando})
    
    vault.setGuestList(guestlist.address, {"from": gov})
    assert vault.guestList() == guestlist.address

    # Set userDepositCap
    guestlist.setUserDepositCap(balance, {"from": gov})
    assert guestlist.userDepositCap() == balance

    # Set totalDepositCap
    guestlist.setTotalDepositCap(2 ** 256 - 1, {"from": gov})
    assert guestlist.totalDepositCap() == 2 ** 256 - 1
    
    chain.sleep(10)
    chain.mine()

    # User, not in guestlist, can't deposit
    with brownie.reverts():
        vault.deposit(balance // 2, {"from": rando})

    # User, not in guestlist, can withdraw
    vault.withdraw(balance // 2, {"from": rando})
    assert vault.balanceOf(rando.address) == 0
    assert token.balanceOf(rando.address) == balance

    chain.sleep(10)
    chain.mine()

    # User is added to guestlist manually
    guestlist.setGuests([rando.address], [True], {"from": gov})
    assert guestlist.guests(rando.address) == True

    chain.sleep(10)
    chain.mine()

    print(guestlist.remainingUserDepositAllowed(rando.address))
    print(guestlist.remainingTotalDepositAllowed())
    print(balance // 2)

    # User, manually added to the guestlist, can deposit
    vault.deposit(balance // 2, rando.address, ["0x0"], {"from": rando})

    assert token.balanceOf(vault) == balance // 2
    assert vault.pricePerShare() == 10 ** token.decimals()  # 1:1 price
    assert vault.balanceOf(rando.address) == balance // 2

# For Badger Merkle Guestlist update:

# def test_merkle_guestlist_flow(gov, rando, vault, token, guestlist):
#     with open("./merkle/merkle_guestlist_test.json") as f:
#         testDistribution = json.load(f)

#     balance = token.balanceOf(gov)

#     # Set guestRoot equal to merkleRoot
#     merkleRoot = testDistribution["merkleRoot"]
#     guestlist.setGuestRoot(merkleRoot, {"from": gov})

#     guestlist.setUserDepositCap(balance, {"from": gov})
#     assert guestlist.userDepositCap() == balance

    
#     # Test merkle verification upon deposit
#     users = [
#         web3.toChecksumAddress("0x8107b00171a02f83D7a17f62941841C29c3ae60F"),
#         web3.toChecksumAddress("0x716722C80757FFF31DA3F3C392A1736b7cfa3A3e"),
#         web3.toChecksumAddress("0xE2e4F2A725E42D0F0EF6291F46c430F963482001"),
#     ]

#     for user in users:
#         accounts.at(user, force=True)

#         claim = testDistribution["claims"][user]
#         proof = claim["proof"]

#         # Gov transfers tokens to user
#         token.transfer(user.address, balance // 6, {"from": gov})
#         token.approve(vault, balance, {"from": user})

#         vault.deposit(balance // 6, proof, {"from": user})
#         assert vault.balanceOf(user.address) == balance // 6 # Since 1:1 price


#     # Test depositing after proveInvitation of a few users
#     users = [
#         web3.toChecksumAddress("0x1fafb618033Fb07d3a99704a47451971976CB586"),
#         web3.toChecksumAddress("0xCf7760E00327f608543c88526427b35049b58984"),
#         web3.toChecksumAddress("0xb43b8B43dE2e59A2B44caa2910E31a4E835d4068"),
#     ]

#     for user in users:
#         accounts.at(user, force=True)

#         claim = testDistribution["claims"][user]
#         proof = claim["proof"]

#         # Gov transfers tokens to user
#         token.transfer(user.address, balance // 6, {"from": gov})
#         token.approve(vault, balance, {"from": user})

#         tx = guestlist.proveInvitation(user, proof)
#         assert tx.events[0]["guestRoot"] == merkleRoot
#         assert tx.events[0]["account"] == user

#         # User deposits 1 token through wrapper (without proof)
#         vault.deposit(balance // 6, [], {"from": user})
#         assert vault.balanceOf(user.address) == balance // 6 # Since 1:1 price


    




    
