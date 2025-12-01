import ape
from ape import accounts

def test_marketplace_deployment(marketplace, owner):
    """Test Marketplace deployment"""
    assert marketplace.admin() == owner.address
    assert marketplace.listing_fee() == 1000
    assert marketplace.cancel_penalty() == 100
    print("✓ Marketplace deployment successful")

def test_create_listing(marketplace, land_nft, owner, seller):
    """Test creating a listing"""
    # Mint NFT to seller first
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test", sender=owner)
    
    # Approve marketplace
    land_nft.approve(marketplace.address, 1, sender=seller)
    
    # Create listing with exact fee
    listing_fee = marketplace.listing_fee()
    tx = marketplace.create_listing(
        1,  # token_id
        "CCCD123",
        5000,  # price
        sender=seller,
        value=listing_fee
    )
    
    # Check event
    events = list(tx.decode_logs(marketplace.ListingCreated))
    assert len(events) == 1
    assert events[0].listing_id == 1
    assert events[0].price == 5000
    
    # Check listing data
    listing = marketplace.get_listing(1)
    assert listing.token_id == 1
    assert listing.seller_cccd == "CCCD123"
    assert listing.price == 5000
    assert listing.status == 0  # Active
    print("✓ Listing creation successful")

def test_initiate_transaction(marketplace, land_nft, owner, seller, buyer):
    """Test initiating a transaction"""
    # Setup: mint NFT and create listing
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test", sender=owner)
    land_nft.approve(marketplace.address, 1, sender=seller)
    
    listing_fee = marketplace.listing_fee()
    marketplace.create_listing(1, "CCCD123", 5000, sender=seller, value=listing_fee)
    
    # Initiate transaction with exact price
    tx = marketplace.initiate_transaction(
        1,  # listing_id
        "CCCD456",  # buyer_cccd
        sender=buyer,
        value=5000  # exact price
    )
    
    # Check event
    events = list(tx.decode_logs(marketplace.TransactionInitiated))
    assert len(events) == 1
    assert events[0].listing_id == 1
    assert events[0].amount == 5000
    
    # Check transaction data
    transaction = marketplace.get_transaction(1)
    assert transaction.listing_id == 1
    assert transaction.buyer_cccd == "CCCD456"
    assert transaction.amount == 5000
    assert transaction.status == 0  # Pending
    
    # Check listing status updated
    listing = marketplace.get_listing(1)
    assert listing.status == 1  # In transaction
    
    # Check escrow balance
    assert marketplace.get_escrow_balance(buyer.address) == 5000
    print("✓ Transaction initiation successful")

def test_approve_transaction(marketplace, land_nft, owner, seller, buyer):
    """Test approving a transaction"""
    # Setup complete flow
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test", sender=owner)
    land_nft.approve(marketplace.address, 1, sender=seller)
    
    listing_fee = marketplace.listing_fee()
    marketplace.create_listing(1, "CCCD123", 5000, sender=seller, value=listing_fee)
    marketplace.initiate_transaction(1, "CCCD456", sender=buyer, value=5000)
    
    # Store balances for verification
    seller_balance_before = seller.balance
    nft_owner_before = land_nft.ownerOf(1)
    
    # Approve transaction
    tx = marketplace.approve_transaction(1, sender=owner)
    
    # Check event
    events = list(tx.decode_logs(marketplace.TransactionApproved))
    assert len(events) == 1
    
    # Check transaction status
    transaction = marketplace.get_transaction(1)
    assert transaction.status == 1, "Transaction still not approved"  # Approved
    
    # Check NFT transferred
    assert land_nft.ownerOf(1) == buyer.address
    
    # Check seller received payment (approximately, due to gas)
    assert seller.balance > seller_balance_before
    
    # Check listing completed
    listing = marketplace.get_listing(1)
    assert listing.status == 2  # Completed
    
    # Check escrow cleared
    assert marketplace.get_escrow_balance(buyer.address) == 0
    print("✓ Transaction approval successful")


def test_reject_transaction_simple(marketplace, land_nft, owner, seller, buyer):
    """Test rejecting a transaction - SIMPLIFIED BALANCE CHECK"""
    # Setup
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test", sender=owner)
    land_nft.approve(marketplace.address, 1, sender=seller)
    
    listing_fee = marketplace.listing_fee()
    marketplace.create_listing(1, "CCCD123", 5000, sender=seller, value=listing_fee)
    
    buyer_balance_before = buyer.balance
    marketplace.initiate_transaction(1, "CCCD456", sender=buyer, value=5000)
    
    # Balance after deposit should be lower
    balance_after_deposit = buyer.balance
    assert balance_after_deposit < buyer_balance_before
    
    # Reject transaction
    marketplace.reject_transaction(1, "Invalid buyer information", sender=owner)
    
    # Balance after refund should be higher than after deposit (due to refund)
    balance_after_refund = buyer.balance
    assert balance_after_refund > balance_after_deposit
    
    # Check transaction status
    transaction = marketplace.get_transaction(1)
    assert transaction.status == 2  # Rejected
    
    # Check listing reactivated
    listing = marketplace.get_listing(1)
    assert listing.status == 0  # Active again
    print("✓ Transaction rejection successful")

def test_buyer_cancel_simple(marketplace, land_nft, owner, seller, buyer):
    """Test buyer canceling transaction - STATE CHECK ONLY"""
    # Setup
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test", sender=owner)
    land_nft.approve(marketplace.address, 1, sender=seller)
    
    listing_fee = marketplace.listing_fee()
    marketplace.create_listing(1, "CCCD123", 5000, sender=seller, value=listing_fee)
    
    # Initiate transaction
    marketplace.initiate_transaction(1, "CCCD456", sender=buyer, value=5000)
    
    # Check escrow before cancel
    escrow_before = marketplace.get_escrow_balance(buyer.address)
    assert escrow_before == 5000
    
    # Buyer cancels
    marketplace.buyer_cancel(1, sender=buyer)
    
    # Check transaction status
    transaction = marketplace.get_transaction(1)
    assert transaction.status == 3  # Cancelled
    
    # Check listing reactivated
    listing = marketplace.get_listing(1)
    assert listing.status == 0  # Active again
    
    # Check escrow cleared
    escrow_after = marketplace.get_escrow_balance(buyer.address)
    assert escrow_after == 0, f"Escrow should be 0, got {escrow_after}"
    
    print("✓ Buyer cancellation successful - states correct")

def test_marketplace_admin_functions(marketplace, owner, accounts):
    """Test marketplace admin functions"""
    new_land_nft = accounts[3].address
    
    # Set new land NFT
    marketplace.set_land_nft(new_land_nft, sender=owner)
    assert marketplace.land_nft() == new_land_nft
    
    # Set fees
    marketplace.set_fees(2000, 200, sender=owner)
    assert marketplace.listing_fee() == 2000
    assert marketplace.cancel_penalty() == 200
    
    # Reset to original for other tests
    marketplace.set_fees(1000, 100, sender=owner)
    marketplace.set_land_nft(marketplace.land_nft(), sender=owner)  # Keep original
    
    print("✓ Marketplace admin functions successful")
    
def test_debug_approve_transaction(marketplace, land_nft, owner, seller, buyer):
    """Debug function for approve_transaction"""
    print("=== DEBUG APPROVE TRANSACTION ===")
    
    # Setup
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test", sender=owner)
    print(f"1. NFT minted to: {seller.address}")
    
    land_nft.approve(marketplace.address, 1, sender=seller)
    approved = land_nft.getApproved(1)
    print(f"2. NFT approved for: {approved}")
    print(f"3. Marketplace address: {marketplace.address}")
    
    listing_fee = marketplace.listing_fee()
    marketplace.create_listing(1, "CCCD123", 5000, sender=seller, value=listing_fee)
    print("4. Listing created")
    
    marketplace.initiate_transaction(1, "CCCD456", sender=buyer, value=5000)
    print("5. Transaction initiated")
    
    # Check states before approval
    nft_owner_before = land_nft.ownerOf(1)
    listing_before = marketplace.get_listing(1)
    tx_before = marketplace.get_transaction(1)
    
    print(f"6. NFT owner before: {nft_owner_before}")
    print(f"7. Listing status before: {listing_before.status}")
    print(f"8. Transaction status before: {tx_before.status}")
    
    try:
        marketplace.approve_transaction(1, sender=owner)
        print("9. ✓ Transaction approved successfully")
        
        # Check states after
        nft_owner_after = land_nft.ownerOf(1)
        listing_after = marketplace.get_listing(1)
        tx_after = marketplace.get_transaction(1)
        
        print(f"10. NFT owner after: {nft_owner_after}")
        print(f"11. Listing status after: {listing_after.status}")
        print(f"12. Transaction status after: {tx_after.status}")
        
    except Exception as e:
        print(f"9. ❌ Error: {e}")

def test_check_addresses(land_registry, marketplace, land_nft, owner):
    """Check that all contracts have different addresses"""
    print("=== CONTRACT ADDRESSES ===")
    print(f"LandNFT: {land_nft.address}")
    print(f"LandRegistry: {land_registry.address}") 
    print(f"Marketplace: {marketplace.address}")
    
    # Check for address collisions
    addresses = {
        "LandNFT": land_nft.address,
        "LandRegistry": land_registry.address,
        "Marketplace": marketplace.address
    }
    
    unique_addresses = set(addresses.values())
    if len(unique_addresses) != 3:
        print("❌ ADDRESS COLLISION DETECTED!")
        for name, addr in addresses.items():
            print(f"   {name}: {addr}")
    else:
        print("✓ All addresses are unique")
    
    # Check minter setup
    minter = land_nft.minter()
    print(f"LandNFT minter: {minter}")
    print(f"Minter is LandRegistry: {minter == land_registry.address}")
    
    # Check marketplace land_nft reference
    market_land_nft = marketplace.land_nft()
    print(f"Marketplace land_nft: {market_land_nft}")
    print(f"Matches actual LandNFT: {market_land_nft == land_nft.address}")
    
def test_manual_deployment(project, accounts):
    """Manual deployment to avoid fixture issues"""
    owner = accounts[0]
    seller = accounts[1]
    buyer = accounts[2]
    
    print("=== MANUAL DEPLOYMENT ===")
    
    # Deploy LandNFT
    land_nft = project.LandNFT.deploy("LandNFT", "LAND", owner.address, sender=owner)
    print(f"LandNFT: {land_nft.address}")
    
    # Deploy LandRegistry
    land_registry = project.LandRegistry.deploy(land_nft.address, sender=owner)
    print(f"LandRegistry: {land_registry.address}")
    
    # Set minter
    land_nft.set_minter(land_registry.address, sender=owner)
    print(f"Minter set to: {land_registry.address}")
    
    # Deploy Marketplace
    marketplace = project.Marketplace.deploy(land_nft.address, 1000, 100, sender=owner)
    print(f"Marketplace: {marketplace.address}")
    
    # Verify all addresses are different
    addresses = [land_nft.address, land_registry.address, marketplace.address]
    assert len(set(addresses)) == 3, "Address collision detected!"
    
    # Test basic functionality
    print("Testing basic functionality...")
    
    # Test LandNFT mint via LandRegistry
    land_registry.register_land("Test St", 100, "CCCD123", "pdf://test", "img://test", sender=seller)
    land_registry.approve_land(1, "metadata://test", sender=owner)
    
    assert land_nft.ownerOf(1) == seller.address
    print("✓ Land registration and NFT minting works")
    
    # Test Marketplace listing
    land_nft.approve(marketplace.address, 1, sender=seller)
    marketplace.create_listing(1, "CCCD123", 5000, sender=seller, value=1000)
    
    listing = marketplace.get_listing(1)
    assert listing.status == 0
    print("✓ Marketplace listing works")
    
    # Test transaction initiation
    marketplace.initiate_transaction(1, "CCCD456", sender=buyer, value=5000)
    
    transaction = marketplace.get_transaction(1)
    assert transaction.status == 0
    print("✓ Transaction initiation works")
    
    # Test transaction approval
    marketplace.approve_transaction(1, sender=owner)
    
    transaction_after = marketplace.get_transaction(1)
    assert transaction_after.status == 1
    assert land_nft.ownerOf(1) == buyer.address
    print("✓ Transaction approval works")
    
    print("🎉 MANUAL DEPLOYMENT TEST PASSED!")