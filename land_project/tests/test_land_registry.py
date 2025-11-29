import ape
from ape import accounts
def test_registry_deployment(land_registry, owner, land_nft):
    """Test trạng thái ban đầu của contract"""
    assert land_registry.admin() == owner.address
    assert land_registry.land_nft() == land_nft.address
    assert land_registry.next_land_id() == 1
    print("✓ Deployment verified")

def test_register_land(land_registry, seller):
    """Test đăng ký đất và kiểm tra dữ liệu struct"""
    tx = land_registry.register_land(
        "123 Main Street",
        1000,
        "CCCD123456",
        "ipfs://pdf123",
        "ipfs://image123",
        sender=seller
    )
    
    # 1. Kiểm tra Event
    events = list(tx.decode_logs(land_registry.LandRegistered))
    assert len(events) == 1
    assert events[0].land_id == 1
    assert events[0].owner == seller.address
    assert events[0].owner_cccd == "CCCD123456"
    
    # 2. Kiểm tra dữ liệu Parcel
    land = land_registry.get_land(1)
    assert land.id == 1
    assert land.land_address == "123 Main Street"
    assert land.area == 1000
    assert land.owner_cccd == "CCCD123456"
    assert land.status == 0  # Pending
    assert land.pdf_uri == "ipfs://pdf123"
    
    # 3. Kiểm tra Mapping chủ sở hữu
    owner_lands = land_registry.get_lands_by_owner(seller.address)
    assert len(owner_lands) == 1
    assert owner_lands[0] == 1
    assert land_registry.get_lands_count_by_owner(seller.address) == 1
    
    print("✓ Land registration verified")

def test_approve_land(land_registry, land_nft, owner, seller):
    """Test duyệt đất và mint NFT"""
    # Đăng ký trước
    land_registry.register_land(
        "456 Oak Avenue", 500, "CCCD789012", "pdf", "img", sender=seller
    )
    land_id = 1

    # Duyệt (Approve) bởi Admin
    tx = land_registry.approve_land(land_id, "ipfs://meta456", sender=owner)
    
    # Kiểm tra Event
    events = list(tx.decode_logs(land_registry.LandApproved))
    assert len(events) == 1
    assert events[0].land_id == land_id
    
    # Kiểm tra Status trên Registry
    assert land_registry.is_land_approved(land_id) == True
    assert land_registry.get_land_status(land_id) == 1
    
    # Kiểm tra NFT đã được mint (Gọi sang contract NFT)
    assert land_nft.ownerOf(land_id) == seller.address
    # Kiểm tra URI của NFT (Giả sử LandNFT có hàm tokenURI hoặc token_uri)
    # assert land_nft.tokenURI(land_id) == "ipfs://meta456" 
    
    print("✓ Land approval and Minting verified")

def test_reject_land(land_registry, owner, seller):
    """Test từ chối đất"""
    land_registry.register_land(
        "789 Pine Road", 750, "CCCD_REJECT", "pdf", "img", sender=seller
    )
    land_id = 1

    # Từ chối bởi Admin
    tx = land_registry.reject_land(land_id, sender=owner)
    
    # Kiểm tra Event
    events = list(tx.decode_logs(land_registry.LandRejected))
    assert len(events) == 1
    
    # Kiểm tra Status
    assert land_registry.is_land_rejected(land_id) == True
    assert land_registry.get_land_status(land_id) == 2
    
    print("✓ Land rejection verified")

def test_update_ownership_logic(land_registry, owner, seller, buyer):
    """
    Test logic update_ownership (chuyển nhượng).
    Đây là test quan trọng để kiểm tra thuật toán xóa mảng (swap & pop).
    """
    # 1. Đăng ký 3 lô đất cho Seller để tạo mảng [1, 2, 3]
    for i in range(3):
        land_registry.register_land(
            f"Land {i}", 100, "CCCD_SELLER", "pdf", "img", sender=seller
        )
    
    # Seller đang sở hữu: [1, 2, 3]
    assert land_registry.get_lands_count_by_owner(seller.address) == 3
    
    # 2. Hack: Tạm thời set Admin là "LandNFT" để gọi hàm update_ownership
    # Vì hàm này yêu cầu msg.sender == self.land_nft
    land_registry.set_land_nft(owner.address, sender=owner)
    
    # 3. Chuyển Land ID 2 (ở giữa mảng) từ Seller sang Buyer
    # Gọi hàm update_ownership trực tiếp từ owner (đang đóng vai NFT contract)
    land_registry.update_ownership(2, buyer.address, "CCCD_BUYER", sender=owner)
    
    # 4. Kiểm tra danh sách đất của Seller (Cũ)
    # Logic swap & pop: [1, 2, 3] -> xóa 2 -> lấy 3 đè vào 2 -> [1, 3] (thứ tự có thể thay đổi tùy logic pop)
    seller_lands = land_registry.get_lands_by_owner(seller.address)
    assert len(seller_lands) == 2
    assert 2 not in seller_lands
    assert 1 in seller_lands
    assert 3 in seller_lands
    assert land_registry.get_lands_count_by_owner(seller.address) == 2
    
    # 5. Kiểm tra danh sách đất của Buyer (Mới)
    buyer_lands = land_registry.get_lands_by_owner(buyer.address)
    assert len(buyer_lands) == 1
    assert buyer_lands[0] == 2
    assert land_registry.get_lands_count_by_owner(buyer.address) == 1
    
    # 6. Kiểm tra thông tin cập nhật trong Struct Parcel
    parcel = land_registry.get_land(2)
    assert parcel.owner_cccd == "CCCD_BUYER"
    assert land_registry.get_land_owner(2) == buyer.address

    print("✓ Ownership update (Array swap/pop) logic verified")

def test_admin_permissions(land_registry, owner, seller):
    """Test quyền admin"""
    # Seller (không phải admin) không thể approve
    land_registry.register_land("Test", 100, "C", "p", "i", sender=seller)
    
    with ape.reverts("Caller is not the admin"):
        land_registry.approve_land(1, "meta", sender=seller)
        
    with ape.reverts("Caller is not the admin"):
        land_registry.change_admin(seller.address, sender=seller)

    print("✓ Admin permissions verified")

def test_multiple_registrations(land_registry, seller):
    """Test id tăng dần"""
    land_registry.register_land("Land 1", 100, "C1", "p", "i", sender=seller)
    land_registry.register_land("Land 2", 100, "C1", "p", "i", sender=seller)
    
    assert land_registry.next_land_id() == 3 # Bắt đầu từ 1, sau 2 lần đk thành 3
    assert land_registry.get_land(1).land_address == "Land 1"
    assert land_registry.get_land(2).land_address == "Land 2"
    
    print("✓ ID increment verified")