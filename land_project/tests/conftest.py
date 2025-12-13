import pytest
import ape

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
def stranger(accounts):
    return accounts[3]

@pytest.fixture
def land_nft(project, owner):
    return project.LandNFT.deploy("LandNFT", "LAND", owner.address, sender=owner)

@pytest.fixture
def land_registry(project, land_nft, owner):
    registry = project.LandRegistry.deploy(land_nft.address, sender=owner)
    land_nft.set_minter(registry.address, sender=owner)
    
    return registry

@pytest.fixture
def marketplace(project, land_nft, owner):
    return project.Marketplace.deploy(land_nft.address, 1000, 100, sender=owner)

@pytest.fixture
def minted_token_id(land_registry, land_nft, owner, seller):
    land_registry.register_land("Addr", 100, "CCCD_SELLER", "pdf", "img", sender=seller)
    land_registry.approve_land(1, "meta_uri", sender=owner)
    return 1