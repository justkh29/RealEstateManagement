from ape.exceptions import ContractLogicError
import pytest

def test_init(erc721_contract, deployer):
    assert "Hello NFT" == erc721_contract.name()
    assert "HEL" == erc721_contract.symbol()

def test_balanceOf(erc721_contract, deployer, mint_nfts):
    assert 5 == erc721_contract.balanceOf(deployer)

def test_ownerOf(erc721_contract, deployer, mint_nfts):
    for i in range(5):
        assert deployer == erc721_contract.ownerOf(i)

def test_transfer(erc721_contract, deployer, mint_nfts, accounts):
    user = accounts[1]
    # Your code

def test_approve(erc721_contract, deployer, mint_nfts, accounts):
    user1 = accounts[1]
    # Your code

def test_setApprovalForAll(erc721_contract, deployer, mint_nfts, accounts):
    user1 = accounts[1]
    # Your code