import ape

def test_flow(land_registry, land_nft, marketplace, owner, seller, buyer):
    # 1. Register
    land_registry.register_land("Integration St", 200, "CCCD_S", "pdf", "img", sender=seller)
    land_id = 1
    
    # 2. Approve Land
    land_registry.approve_land(land_id, "meta", sender=owner)
    assert land_nft.ownerOf(land_id) == seller.address
    
    # 3. Create Listing
    land_nft.approve(marketplace.address, land_id, sender=seller)
    fee = marketplace.listing_fee()
    marketplace.create_listing(land_id, "CCCD_S", 5000, sender=seller, value=fee)
    
    # 4. Initiate Transaction
    marketplace.initiate_transaction(1, "CCCD_B", sender=buyer, value=5000)
    
    # 5. Approve Transaction
    marketplace.approve_transaction(1, sender=owner)
    
    # 6. Final Assertions
    assert land_nft.ownerOf(land_id) == buyer.address
    assert land_registry.get_land_owner(land_id) == buyer.address
    assert land_registry.get_land(land_id).owner_cccd == "CCCD_B"
    assert marketplace.get_listing(1).status == 2