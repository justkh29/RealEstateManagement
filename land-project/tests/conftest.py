import pytest
from ape import accounts

@pytest.fixture
def owner(accounts):
    return accounts[0]

@pytest.fixture
def seller(accounts):
    return accounts[1]

@pytest.fixture
def buyer(accounts):
    return accounts[2]

@pytest.fixture
def land_nft(project, owner):
    # Deploy LandNFT với owner là minter
    nft = project.LandNFT.deploy("LandNFT", "LAND", owner.address, sender=owner)
    print(f"LandNFT deployed at: {nft.address}")
    return nft

@pytest.fixture
def land_registry(project, land_nft, owner):
    # Deploy LandRegistry
    registry = project.LandRegistry.deploy(land_nft.address, sender=owner)
    print(f"LandRegistry deployed at: {registry.address}")
    
    # Set LandRegistry làm minter cho LandNFT
    land_nft.set_minter(registry.address, sender=owner)
    print(f"LandNFT minter set to: {registry.address}")
    
    return registry

@pytest.fixture
def marketplace(project, land_nft, owner):
    # Deploy Marketplace với listing_fee = 1000 wei, cancel_penalty = 100 wei
    market = project.Marketplace.deploy(land_nft.address, 1000, 100, sender=owner)
    print(f"Marketplace deployed at: {market.address}")
    return market

