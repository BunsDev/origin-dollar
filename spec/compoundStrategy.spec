using MockCToken as cToken
using DummyERC20A as assetInstance

methods {
    assetToPToken(address) returns (address) envfree
    checkBalance(address) returns uint256 envfree
    deposit(address, uint256) envfree
    governor() returns address envfree
    isListedAsPlatformToken(address, uint256) returns (bool) envfree
    lengthOfPlatformTokensList() returns (uint256) envfree
    removePToken(uint256)
    underlyingBalance(address) returns (uint256) envfree
    withdraw(address, address, uint256) envfree
    cToken.underlyingToken() returns (address) envfree
    assetInstance.balanceOf(address) returns (uint256)

    // dispatch summaries
    approve(address,uint256) => DISPATCHER(true)
    balanceOf(address) => DISPATCHER(true)
    exchangeRateStored() => ALWAYS(1000000000000000000) // 1e18
    mint(uint256) => DISPATCHER(true)
    redeem(uint256) => DISPATCHER(true)
    redeemUnderlying(uint256) => DISPATCHER(true)
    transfer(address, uint256) => DISPATCHER(true)

    // NONDET
    deposit(address, uint256, uint16) => NONDET
}

// consts and simple macro definitions
definition MAX_UINT256() returns uint256 = 115792089237316195423570985008687907853269984665640564039457584007913129639935
    ;

definition MAX_UINT160() returns uint256 = 1461501637330902918203684832716283019655932542975
    ;

definition IS_ADDRESS(address x) returns bool = 0 <= x && x <= MAX_UINT160()
    ;

/*
    The deposit operation of an asset transfers amount of underlying tokens to
    the platform, and gets in return an amount of platform tokens that have a value
    equal to the deposited amount.
*/
rule integrityOfDeposit(address asset) {
    uint256 amount;
    env e;
    require assetToPToken(asset) == cToken;
    require assetInstance == asset;
    //require cToken.underlyingToken() == assetInstance;

    uint256 underlyingBalanceBefore = underlyingBalance(asset);
    uint256 platformBalanceBefore = checkBalance(asset);

    deposit@withrevert(asset, amount); // TODO with no revert ?
    bool depositReverted = lastReverted;

    uint256 platformBalanceAfter = checkBalance(asset);
    uint256 underlyingBalanceAfter = underlyingBalance(asset);
    assert !depositReverted => ( platformBalanceAfter + underlyingBalanceAfter ==
                                 platformBalanceBefore + underlyingBalanceBefore), "deposit resulted in unexpected balances change";
}


rule checkBalanceRule(address asset, method f) {
    env e;
    calldataarg arg;
    require assetToPToken(asset) == cToken;
    require assetInstance == asset;

    uint256 underlyingBalanceBefore = underlyingBalance(asset);
    uint256 platformBalanceBefore = checkBalance(asset);
    f(e, arg);
    uint256 platformBalanceAfter = checkBalance(asset);
    uint256 underlyingBalanceAfter = underlyingBalance(asset);

    assert (platformBalanceAfter +  underlyingBalanceAfter == platformBalanceBefore + underlyingBalanceBefore), "resulted in unexpected balances change";
}


rule checkRemoveTokenRule(address asset, uint256 _assetIndex){
    require assetToPToken(asset) == cToken;
    env e;
    bool isPrivileged = e.msg.sender == governor();
    require isPrivileged;

    uint256 platformBalanceBefore;
    if (assetToPToken(asset) != 0) {
        platformBalanceBefore = checkBalance(asset);
    } else {
        platformBalanceBefore = 0;
    }

    removePToken(e, _assetIndex);

    uint256 platformBalanceAfter;
    if (assetToPToken(asset) != 0) {
        platformBalanceAfter = checkBalance(asset);
    } else {
        platformBalanceAfter = 0;
    }

    assert platformBalanceAfter == platformBalanceBefore, "removePToken resulted in unexpected balances change";
}


rule reversibilityOfDeposit(address asset) {
    // A deposit operation can be inverted, and the funds can be restored.

    uint256 amount;
    require assetToPToken(asset) != 0; // pToken is set

    uint256 platformBalanceBefore = checkBalance(asset);

    deposit@withrevert(asset, amount);
    bool depositReverted = lastReverted;

    withdraw@withrevert(currentContract, asset, amount);
    bool withdrawReverted = lastReverted;

    uint256 platformBalanceAfter = checkBalance(asset);

    assert !depositReverted => ( !withdrawReverted =>
                                 platformBalanceAfter == platformBalanceBefore ),
                                 "withdraw deposited amount resulted in unexpected balances change";
}


// Total asset value is monotonically increasing
rule totalValueIncreasing(address asset, method f) {
    env e;
    calldataarg arg;

    require assetToPToken(asset) == cToken;
    require assetInstance == asset;

    uint256 underlyingBalanceBefore = underlyingBalance(asset);
    uint256 platformBalanceBefore = checkBalance(asset);
    uint256 totalBefore = underlyingBalanceBefore + platformBalanceBefore;

    f(e, arg);

    uint256 platformBalanceAfter = checkBalance(asset);
    uint256 underlyingBalanceAfter = underlyingBalance(asset);
    uint256 totalAfter = underlyingBalanceAfter + platformBalanceAfter;

    assert totalBefore <= totalAfter, "Total asset value has decreased";
}