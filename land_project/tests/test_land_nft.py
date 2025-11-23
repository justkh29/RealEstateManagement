import ape
from ape import accounts

def test_nft_deployment(land_nft, owner):
    """Test NFT contract deployment"""
    assert land_nft.name() == "LandNFT"
    assert land_nft.symbol() == "LAND"
    assert land_nft.minter() == owner.address
    print("✓ NFT deployment successful")

def test_nft_mint(land_nft, owner, seller):
    """Test NFT minting functionality"""
    # Mint NFT
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test1", sender=owner)
    
    # Verify NFT properties
    assert land_nft.ownerOf(1) == seller.address
    assert land_nft.balance_of(seller.address) == 1
    
    land_data = land_nft.get_land_data(1)
    assert land_data.owner_cccd == "CCCD123"
    assert land_nft.token_uri(1) == "metadata://test1"
    print("✓ NFT minting successful")

def test_nft_transfer(land_nft, owner, seller, buyer):
    """Test NFT transfer functionality"""
    # Mint NFT first
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test1", sender=owner)
    
    # Test transfer with CCCD
    land_nft.transferWithCCCD(seller.address, buyer.address, 1, "CCCD456", sender=seller)
    
    # Verify transfer
    assert land_nft.ownerOf(1) == buyer.address
    assert land_nft.balance_of(seller.address) == 0
    assert land_nft.balance_of(buyer.address) == 1
    
    # Verify CCCD updated
    land_data = land_nft.get_land_data(1)
    assert land_data.owner_cccd == "CCCD456"
    print("✓ NFT transfer with CCCD successful")

def test_nft_approval(land_nft, owner, seller, buyer):
    """Test NFT approval functionality"""
    # Mint NFT
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test1", sender=owner)
    
    # Approve buyer
    land_nft.approve(buyer.address, 1, sender=seller)
    assert land_nft.getApproved(1) == buyer.address
    
    # Buyer transfers using approval
    land_nft.transferFrom(seller.address, buyer.address, 1, sender=buyer)
    assert land_nft.ownerOf(1) == buyer.address
    print("✓ NFT approval and transfer successful")