import ape
import pytest

def test_register_land_validation(land_registry, seller):
    with ape.reverts("Land address cannot be empty"):
        land_registry.register_land("", 100, "C", "p", "i", sender=seller)
        
    with ape.reverts("Area must be greater than 0"):
        land_registry.register_land("A", 0, "C", "p", "i", sender=seller)

def test_full_approve(land_registry, land_nft, owner, seller):
    # 1. Register
    tx = land_registry.register_land("Addr", 500, "CCCD_S", "pdf", "img", sender=seller)
    logs = list(tx.decode_logs(land_registry.LandRegistered))
    land_id = logs[0].land_id
    
    assert land_registry.get_land_status(land_id) == 0 # Pending
    
    # 2. Approve (Mint)
    land_registry.approve_land(land_id, "meta", sender=owner)
    
    assert land_registry.is_land_approved(land_id) is True
    assert land_nft.ownerOf(land_id) == seller
    
    # 3. Cannot approve again
    with ape.reverts("Land is not in pending state"):
        land_registry.approve_land(land_id, "meta", sender=owner)

def test_reject_land(land_registry, owner, seller):
    land_registry.register_land("Bad Land", 100, "C", "p", "i", sender=seller)
    land_id = 1
    
    # User thường không thể reject
    with ape.reverts("Caller is not the admin"):
        land_registry.reject_land(land_id, sender=seller)
        
    land_registry.reject_land(land_id, sender=owner)
    assert land_registry.is_land_rejected(land_id) is True

def test_update_ownership(land_registry, owner, seller, buyer):
    """
    Test logic tráo đổi mảng khi xóa đất khỏi danh sách chủ cũ
    """
    land_registry.set_land_nft(owner, sender=owner)
    
    # Đăng ký 3 lô đất: ID 1, 2, 3
    for _ in range(3):
        land_registry.register_land("L", 100, "C", "p", "i", sender=seller)
        
    land_registry.update_ownership(2, buyer, "CCCD_B", sender=owner)
    
    seller_lands = land_registry.get_lands_by_owner(seller)
    assert len(seller_lands) == 2
    assert 2 not in seller_lands
    assert 1 in seller_lands and 3 in seller_lands
    
    buyer_lands = land_registry.get_lands_by_owner(buyer)
    assert buyer_lands == [2]
    
    assert land_registry.get_land(2).owner_cccd == "CCCD_B"