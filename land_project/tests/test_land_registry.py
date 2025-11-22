import ape
from ape import accounts

def test_registry_deployment(land_registry, owner):
    """Test LandRegistry deployment"""
    assert land_registry.admin() == owner.address
    assert land_registry.land_nft() != ape.utils.ZERO_ADDRESS
    print("✓ Registry deployment successful")

def test_register_land(land_registry, seller):
    """Test land registration"""
    tx = land_registry.register_land(
        "123 Main Street",
        1000,
        "CCCD123456",
        "ipfs://pdf123",
        "ipfs://image123",
        sender=seller
    )
    
    # Check event
    events = list(tx.decode_logs(land_registry.LandRegistered))
    assert len(events) == 1
    assert events[0].land_id == 1
    assert events[0].owner == seller.address
    
    # Check land data
    land = land_registry.get_land(1)
    assert land.id == 1
    assert land.land_address == "123 Main Street"
    assert land.area == 1000
    assert land.owner_cccd == "CCCD123456"
    assert land.status == 0  # Pending
    print("✓ Land registration successful")

def test_approve_land(land_registry, land_nft, owner, seller):
    """Test land approval and NFT minting"""
    # First register land
    land_registry.register_land(
        "456 Oak Avenue",
        500,
        "CCCD789012",
        "ipfs://pdf456",
        "ipfs://image456",
        sender=seller
    )
    
    # Approve land
    tx = land_registry.approve_land(1, "ipfs://metadata456", sender=owner)
    
    # Check event
    events = list(tx.decode_logs(land_registry.LandApproved))
    assert len(events) == 1
    assert events[0].land_id == 1
    
    # Check land status updated
    land = land_registry.get_land(1)
    assert land.status == 1  # Approved
    
    # Check NFT minted
    assert land_nft.ownerOf(1) == seller.address
    
    # Check NFT data
    land_data = land_nft.get_land_data(1)
    assert land_data.owner_cccd == "CCCD789012"
    assert land_data.metadata_uri == "ipfs://metadata456"
    print("✓ Land approval and NFT minting successful")

def test_reject_land(land_registry, owner, seller):
    """Test land rejection"""
    # Register land
    land_registry.register_land(
        "789 Pine Road",
        750,
        "CCCD345678",
        "ipfs://pdf789",
        "ipfs://image789",
        sender=seller
    )
    
    # Reject land
    tx = land_registry.reject_land(1, sender=owner)
    
    # Check event
    events = list(tx.decode_logs(land_registry.LandRejected))
    assert len(events) == 1
    
    # Check land status updated
    land = land_registry.get_land(1)
    assert land.status == 2  # Rejected
    print("✓ Land rejection successful")

def test_admin_functions(land_registry, owner, accounts):
    """Test admin functions"""
    new_admin = accounts[3]
    
    # Change admin
    land_registry.change_admin(new_admin.address, sender=owner)
    assert land_registry.admin() == new_admin.address
    
    # Change back
    land_registry.change_admin(owner.address, sender=new_admin)
    assert land_registry.admin() == owner.address
    print("✓ Admin functions successful")