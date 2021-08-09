// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.6.0 <0.7.0;
pragma experimental ABIEncoderV2;

import "@openzeppelin/contracts/utils/EnumerableSet.sol";

// Data from Vault
struct StrategyParams {
  uint256 performanceFee;
  uint256 activation;
  uint256 debtRatio;
  uint256 minDebtPerHarvest;
  uint256 maxDebtPerHarvest;
  uint256 lastReport;
  uint256 totalDebt;
  uint256 totalGain;
  uint256 totalLoss;
}

interface VaultView {
  function name() external view returns (string memory);
  function symbol() external view returns (string memory);

  function token() external view returns (address);

  function strategies(address _strategy) external view returns (StrategyParams memory);


  function pendingGovernance() external view returns (address);
  function governance() external view returns (address);
  function management() external view returns (address);
  function guardian() external view returns (address);

  function rewards() external view returns (address);

  function withdrawalQueue(uint256 index) external view returns (address);
}

interface StratView {
    function name() external view returns (string memory);

    function strategist() external view returns (address);
    function rewards() external view returns (address);
    function keeper() external view returns (address);

}


contract BadgerRegistryV2 {
  using EnumerableSet for EnumerableSet.AddressSet;


  //@dev Multisig. Vaults from here are considered Production ready
  address public governance;

  //@dev Given an Author Address, and Token, Return the Vault
  mapping(address => mapping(string => EnumerableSet.AddressSet)) private vaults;

  mapping(string => address) public addresses;

  event NewVault(address author, string version, address vault);
  event RemoveVault(address author, string version, address vault);
  event PromoteVault(address author, string version, address vault);

  event Set(string key, address at);
  event AddKey(string key);

  // Known constants you can use
  string[] public keys; // Notice, you don't have a guarantee of the key being there, it's just a utility


  //@dev View Data for each strat we will return
  struct StratInfo {
    address at;
    string name;

    address strategist;
    address rewards;
    address keeper;

    uint256 performanceFee;
    uint256 activation;
    uint256 debtRatio;
    uint256 minDebtPerHarvest;
    uint256 maxDebtPerHarvest;
    uint256 lastReport;
    uint256 totalDebt;
    uint256 totalGain;
    uint256 totalLoss;
  }

  /// Vault data we will return for each Vault
  struct VaultInfo {
    address at;
    string name;
    string symbol;

    address token;

    address pendingGovernance; // If this is non zero, this is an attack from the deployer
    address governance;
    address rewards;
    address guardian;
    address management;

    StratInfo[] strategies;
  }

  constructor (address _governance) public {
    governance = _governance;

    keys.push("v1"); //For v1
    keys.push("v2"); //For v2
  }

  function setGovernance(address _newGov) public {
    require(msg.sender == governance, "!gov");
    governance = _newGov;
  }


  /// Anyone can add a vault to here, it will be indexed by their address
  function add(string memory key, address vault) public {
    bool added = vaults[msg.sender][key].add(vault);
    if (added) { 
      emit NewVault(msg.sender, key, vault);
    }
  }

  /// Remove the vault from your index
  function remove(string memory key, address vault) public {
    bool removed = vaults[msg.sender][key].remove(vault);
    if (removed) { 
      emit RemoveVault(msg.sender, key, vault); 
     }
  }

  function set(string memory key, address at) public {
    require(msg.sender == governance, "!gov");
    addresses[key] = at;
    emit Set(key, at);
  }

  function get(string memory key) public returns (address){
    return addresses[key];
  }

  // Utility function to add keys, NOTE: No guarantee that it will be properly used
  function addKey(string memory key) public {
    require(msg.sender == governance, "!gov");
    keys.push(key);

    emit AddKey(key);
  }

  //@dev Retrieve a list of all Vault Addresses from the given author
  function fromAuthor(address author, string memory key) public view returns (address[] memory) {
    uint256 length = vaults[author][key].length();

    address[] memory list = new address[](length);
    for (uint256 i = 0; i < length; i++) {
      list[i] = vaults[author][key].at(i);
    }
    return list;
  }

  //@dev Retrieve a list of all Vaults and the basic Vault info
  function fromAuthorVaults(address author, string memory key) public view returns (VaultInfo[] memory) {
    uint256 length = vaults[author][key].length();

    VaultInfo[] memory vaultData = new VaultInfo[](length);
    for(uint x = 0; x < length; x++){
      VaultView vault = VaultView(vaults[author][key].at(x));
      StratInfo[] memory allStrats = new StratInfo[](0);

      VaultInfo memory data = VaultInfo({
        at: vaults[author][key].at(x),
        name: vault.name(),
        symbol: vault.symbol(),
        token: vault.token(),
        pendingGovernance: vault.pendingGovernance(),
        governance: vault.governance(),
        rewards: vault.rewards(),
        guardian: vault.guardian(),
        management: vault.management(),
        strategies: allStrats
      });

      vaultData[x] = data;
    }
    return vaultData;
  }


  //@dev Given the Vault, retrieve all the data as well as all data related to the strategies
  function fromAuthorWithDetails(address author, string memory key) public view returns (VaultInfo[] memory) {
    uint256 length = vaults[author][key].length();
    VaultInfo[] memory vaultData = new VaultInfo[](length);
    
    for(uint x = 0; x < length; x++){
      VaultView vault = VaultView(vaults[author][key].at(x));

      // TODO: Strat Info with real data
      uint stratCount = 0;
      for(uint y = 0; y < 20; y++){
        if(vault.withdrawalQueue(y) != address(0)){
          stratCount++;
        }
      }
      StratInfo[] memory allStrats = new StratInfo[](stratCount);

      for(uint z = 0; z < stratCount; z++){
        StratView strat = StratView(vault.withdrawalQueue(z));
        StrategyParams memory params = vault.strategies(vault.withdrawalQueue(z));
        StratInfo memory stratData = StratInfo({
          at: vault.withdrawalQueue(z),
          name: strat.name(),
          strategist: strat.strategist(),
          rewards: strat.rewards(),
          keeper: strat.keeper(),

          performanceFee: params.performanceFee,
          activation: params.activation,
          debtRatio: params.debtRatio,
          minDebtPerHarvest: params.minDebtPerHarvest,
          maxDebtPerHarvest: params.maxDebtPerHarvest,
          lastReport: params.lastReport,
          totalDebt: params.totalDebt,
          totalGain: params.totalGain,
          totalLoss: params.totalLoss
        });
        allStrats[z] = stratData;
      }

      VaultInfo memory data = VaultInfo({
        at: vaults[author][key].at(x),
        name: vault.name(),
        symbol: vault.symbol(),
        token: vault.token(),
        pendingGovernance: vault.pendingGovernance(),
        governance: vault.governance(),
        rewards: vault.rewards(),
        guardian: vault.guardian(),
        management: vault.management(),
        strategies: allStrats
      });

      vaultData[x] = data;
    }

    return vaultData;
  }

  //@dev Promote a vault to Production
  //@dev Promote just means indexed by the Governance Address
  function promote(string memory key, address vault) public {
    require(msg.sender == governance, "!gov");
    bool promoted = vaults[msg.sender][key].add(vault);

    if (promoted) { 
      emit PromoteVault(msg.sender, key, vault);
    }
  }
}