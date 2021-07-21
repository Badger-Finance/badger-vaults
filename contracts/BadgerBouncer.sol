// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/cryptography/MerkleProofUpgradeable.sol";
import {VaultAPI} from "./BaseStrategy.sol";

contract BadgerBouncer is OwnableUpgradeable {
    using SafeMathUpgradeable for uint256;

    mapping (address => uint256) public userCaps;
    mapping (address => uint256) public totalCaps;
    mapping (address => bytes32) public guestListRootOverride;
    mapping (address => bool) public removedGuestList;
    mapping (address => bool) public isBanned;

    bytes32 public defaultGuestListRoot;

    event SetDefaultGuestListRoot(bytes32 indexed defaultGuestListRoot);
    event Deposit(address vault, uint256 amount, address user);
    event DepositFor(address vault, uint256 amount, address recipient);
    event Banned(address account);
    event Unbanned(address account);
    event SetRootForVault(address vault, bytes32 guestListRoot);
    event RemoveRootForVault(address vault);

    uint256 constant MAX_INT256 = 2**256 - 1;

    /**
     * @notice Create the Badger Bouncer, setting the message sender as
     * `owner`.
     */
    function initialize(bytes32 defaultGuestListRoot_) public initializer {
        __Ownable_init();
        defaultGuestListRoot = defaultGuestListRoot_;
    }

    function remainingTotalDepositAllowed(address vault) public view returns (uint256) {
        uint256 totalDepositCap = userCaps[vault];
        // If total cap is set to 0, treat as no cap
        if (totalDepositCap == 0) {
            return MAX_INT256;
        } else {
            return totalDepositCap.sub(VaultAPI(vault).totalSupply()); // Only holds for PPS 1:1, must adapt.
        }
    }

    function remainingUserDepositAllowed(address user, address vault) public view returns (uint256) {
        uint256 userDepositCap = userCaps[vault];
        // If user cap is set to 0, treat as no cap
        if (userDepositCap == 0) {
            return MAX_INT256;
        } else {
            return userDepositCap.sub(VaultAPI(vault).balanceOf(user));
        }
    }

    /**
     * @notice Sets the default GuestList merkle root to a new value
     */
    function setDefaultGuestListRoot(bytes32 defaultGuestListRoot_) external onlyOwner {
        defaultGuestListRoot = defaultGuestListRoot_;

        emit SetDefaultGuestListRoot(defaultGuestListRoot);
    }

    /**
     * @notice Sets an specified Merkle root for a certain vault
     */
    function setRootForVault(address vault, bytes32 guestListRoot) external onlyOwner {
        guestListRootOverride[vault] = guestListRoot;
        removedGuestList[vault] = false;

        emit SetRootForVault(vault, guestListRoot);
    }

    /**
     * @notice Sets a vault's Merkle root to 0x0
     */
    function removeRootForVault(address vault) external onlyOwner {
        guestListRootOverride[vault] = bytes32(0);
        removedGuestList[vault] = true;

        emit RemoveRootForVault(vault);
    }

    /**
     * @notice Adds given address to the blacklist
     */
    function banAddress(address account) external onlyOwner {
        isBanned[account] = true;

        emit Banned(account);
    }

    /**
     * @notice Removed given address from the blacklist
     */
    function unbanAddress(address account) external onlyOwner {
        isBanned[account] = false;

        emit Unbanned(account);
    }

    /**
     * @notice Verifies permission criteria and redirects deposit to designated vault if authorized
     */
    function deposit(address vault, uint256 amount, bytes32[] calldata merkleProof) external {
        require(authorized(msg.sender, vault, amount, merkleProof), "Unauthorized user for given vault");
        require(isBanned[msg.sender] == false, "Blacklisted user");

        VaultAPI(vault).deposit(amount, msg.sender);

        emit Deposit(vault, amount, msg.sender);
    }

    /**
     * @notice Verifies permission criteria for a specificed user and redirects deposit to designated vault if authorized
     */
    function depositFor(address vault, address recipient, uint256 amount, bytes32[] calldata merkleProof) external {
        require(authorized(recipient, vault, amount, merkleProof), "Unauthorized user for given vault");
        require(isBanned[recipient] == false, "Blacklisted user");

        VaultAPI(vault).deposit(amount, recipient);

        emit DepositFor(vault, amount, recipient);
    }

    /**
     * @notice Check if a guest with a bag of a certain size is allowed into
     * the party.
     * @param guest The guest's address to check.
     * @param vault The vault's whose access to authorize.
     * @param amount The amount intended to deposit, to be verified against deposit bounds.
     * @param merkleProof The Merkle proof used to verify access.
     */
    function authorized(
        address guest,
        address vault,
        uint256 amount,
        bytes32[] calldata merkleProof
    ) public view returns (bool)
    {
        bool invited = verifyInvitation(guest, vault, merkleProof);

        // If the guest proved invitiation via list, verify if the amount to deposit keeps them under the cap
        if (invited && remainingUserDepositAllowed(guest, vault) >= amount && remainingTotalDepositAllowed(vault) >= amount) {
            return true;
        } else {
            return false;
        }
    }

    /**
     * @notice Permissionly prove an address is included in a given vault's merkle root, thereby granting access
     */
    function verifyInvitation(address account, address vault, bytes32[] calldata merkleProof) public view returns (bool) {
        // If vault's root is 0x0 and it has been removed: guestlist has been removed -> return true
        if (guestListRootOverride[vault] == bytes32(0) && removedGuestList[vault] == true) {
            return true;
        }

        bytes32 guestRoot;
        // If vault's root is 0x0 and but it hasn't been removed -> use default Merkle root
        if (guestListRootOverride[vault] == bytes32(0) && removedGuestList[vault] == false) {
            guestRoot = defaultGuestListRoot;
        } else {
            guestRoot = guestListRootOverride[vault];
        }
        // Verify Merkle Proof
        return _verifyInvitationProof(account, guestRoot, merkleProof);
    }

    function _verifyInvitationProof(address account, bytes32 guestRoot, bytes32[] calldata merkleProof) internal pure returns (bool) {
        bytes32 node = keccak256(abi.encodePacked(account));
        return MerkleProofUpgradeable.verify(merkleProof, guestRoot, node);
    }
}