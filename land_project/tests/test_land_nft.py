import ape
import pytest

def test_metadata(land_nft, land_registry):
    assert land_nft.name() == "LandNFT"
    assert land_nft.symbol() == "LAND"
    assert land_nft.minter() == land_registry.address

def test_mint_access_control(land_nft,land_registry, owner, seller):
    with ape.reverts("Only minter can mint"):
        land_nft.mint(seller, 1, "CCCD", "uri", sender=owner)

def test_burn_logic(land_nft, land_registry, owner, seller, minted_token_id):
    token_id = minted_token_id
    
    with ape.reverts("Not owner or approved"):
        land_nft.burn(token_id, sender=owner) 
        
    land_nft.burn(token_id, sender=seller)
    
    with ape.reverts("Token does not exist"):
        land_nft.ownerOf(token_id)

def test_transfer_with_cccd(land_nft, seller, buyer, minted_token_id):
    token_id = minted_token_id
    
    land_nft.transferWithCCCD(seller, buyer, token_id, "CCCD_BUYER_NEW", sender=seller)
    
    assert land_nft.ownerOf(token_id) == buyer
    assert land_nft.get_land_data(token_id).owner_cccd == "CCCD_BUYER_NEW"

def test_approve_and_transfer_from(land_nft, seller, buyer, minted_token_id):
    token_id = minted_token_id
    
    land_nft.approve(buyer, token_id, sender=seller)
    assert land_nft.getApproved(token_id) == buyer
    
    land_nft.transferFrom(seller, buyer, token_id, sender=buyer)
    assert land_nft.ownerOf(token_id) == buyer