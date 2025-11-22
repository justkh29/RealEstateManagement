import ape
from ape import accounts

def test_full_integration_flow(land_registry, marketplace, land_nft, owner, seller, buyer):
    """Test complete integration flow from land registration to sale"""
    print("=== STARTING FULL INTEGRATION TEST ===")
    
    # Step 1: Register land
    print("1. Registering land...")
    land_registry.register_land(
        "123 Integration Street",
        1000,
        "CCCDINT001",
        "ipfs://pdf_int",
        "ipfs://img_int",
        sender=seller
    )
    land_id = 1
    assert land_registry.get_land_status(land_id) == 0  # Pending
    print("✓ Land registered")
    
    # Step 2: Approve land (mint NFT)
    print("2. Approving land and minting NFT...")
    land_registry.approve_land(land_id, "ipfs://metadata_int", sender=owner)
    assert land_registry.get_land_status(land_id) == 1  # Approved
    assert land_nft.ownerOf(land_id) == seller.address
    print("✓ Land approved, NFT minted")
    
    # Step 3: Seller approves marketplace
    print("3. Seller approving marketplace...")
    land_nft.approve(marketplace.address, land_id, sender=seller)
    assert land_nft.getApproved(land_id) == marketplace.address
    print("✓ Marketplace approved")
    
    # Step 4: Create listing
    print("4. Creating marketplace listing...")
    listing_fee = marketplace.listing_fee()
    marketplace.create_listing(
        land_id,
        "CCCDINT001",
        10000,  # 10,000 wei price
        sender=seller,
        value=listing_fee
    )
    listing_id = 1
    listing = marketplace.get_listing(listing_id)
    assert listing.status == 0  # Active
    assert listing.price == 10000
    print("✓ Listing created")
    
    # Step 5: Buyer initiates transaction
    print("5. Buyer initiating transaction...")
    buyer_balance_before = buyer.balance
    marketplace.initiate_transaction(
        listing_id,
        "CCCDINT002",  # buyer's CCCD
        sender=buyer,
        value=10000  # exact price
    )
    tx_id = 1
    transaction = marketplace.get_transaction(tx_id)
    assert transaction.status == 0  # Pending
    assert marketplace.get_escrow_balance(buyer.address) == 10000
    print("✓ Transaction initiated")
    
    # Step 6: Admin approves transaction
    print("6. Admin approving transaction...")
    seller_balance_before = seller.balance
    marketplace.approve_transaction(tx_id, sender=owner)
    
    # Verify final states
    assert marketplace.get_transaction(tx_id).status == 1  # Approved
    assert land_nft.ownerOf(land_id) == buyer.address  # NFT transferred
    assert seller.balance > seller_balance_before  # Seller got paid
    assert marketplace.get_escrow_balance(buyer.address) == 0  # Escrow cleared
    assert marketplace.get_listing(listing_id).status == 2  # Listing completed
    
    print("✓ Transaction approved and completed")
    print("🎉 FULL INTEGRATION TEST PASSED!")