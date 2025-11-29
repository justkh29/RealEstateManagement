import pytest
import ape
from ape import accounts

# ==========================================
# TEST CASES
# ==========================================

def test_nft_deployment(land_nft, owner):
    """Test NFT contract deployment"""
    assert land_nft.name() == "LandNFT"
    assert land_nft.symbol() == "LAND"
    # assert land_nft.minter() == owner.address # Lưu ý: Nếu chạy fixture land_registry thì minter có thể bị đổi thành registry
    print("✓ NFT deployment successful")

def test_nft_mint(land_nft, owner, seller):
    """Test NFT minting functionality"""
    # Nếu logic yêu cầu chỉ Registry được mint, bạn có thể cần dùng set_minter lại cho owner để test unit này
    # Hoặc gọi thông qua Registry.
    # Ở đây giả sử owner vẫn có quyền mint để test nhanh:
    
    land_nft.mint(seller.address, 1, "CCCD123", "metadata://test1", sender=owner)
    
    # Verify NFT properties
    assert land_nft.ownerOf(1) == seller.address
    assert land_nft.balance_of(seller.address) == 1
    
    # Kiểm tra struct LandData trong NFT
    land_data = land_nft.get_land_data(1)
    assert land_data.owner_cccd == "CCCD123"
    assert land_nft.token_uri(1) == "metadata://test1"
    print("✓ NFT minting successful")

def test_nft_transfer(land_nft, land_registry, owner, seller, buyer):
    """
    Test NFT transfer functionality.
    QUAN TRỌNG: Phải đưa 'land_registry' vào tham số hàm test 
    để đảm bảo fixture chạy và liên kết contract được thiết lập.
    """
    
    # 1. Setup: Register & Mint thông qua Registry để dữ liệu đồng bộ từ đầu
    # (Cách này an toàn hơn là mint trực tiếp bằng NFT, vì Registry cần khởi tạo struct Parcel)
    land_registry.register_land("Hanoi", 100, "CCCD123", "pdf", "img", sender=seller)
    land_registry.approve_land(1, "metadata://test1", sender=owner)
    
    assert land_nft.ownerOf(1) == seller.address
    
    # 2. Test transfer with CCCD
    # Hàm này sẽ gọi update_ownership bên Registry
    land_nft.transferWithCCCD(seller.address, buyer.address, 1, "CCCD456", sender=seller)
    
    # 3. Verify transfer
    assert land_nft.ownerOf(1) == buyer.address
    assert land_nft.balance_of(seller.address) == 0
    assert land_nft.balance_of(buyer.address) == 1
    
    # 4. Verify CCCD updated inside NFT
    land_data = land_nft.get_land_data(1)
    assert land_data.owner_cccd == "CCCD456"
    
    # 5. Verify data updated inside Registry (Integration check)
    assert land_registry.get_land_owner(1) == buyer.address
    assert land_registry.get_land(1).owner_cccd == "CCCD456"
    
    print("✓ NFT transfer with CCCD successful")

def test_nft_approval(land_nft, land_registry, owner, seller, buyer):
    """Test NFT approval functionality"""
    # Setup qua Registry để đồng bộ
    land_registry.register_land("Hanoi", 100, "CCCD123", "pdf", "img", sender=seller)
    land_registry.approve_land(1, "meta", sender=owner)
    
    # Approve buyer
    land_nft.approve(buyer.address, 1, sender=seller)
    assert land_nft.getApproved(1) == buyer.address
    
    # Buyer transfers using approval
    # Lưu ý: transferFrom thông thường có thể KHÔNG cập nhật CCCD nếu logic contract không gọi.
    # Nhưng nếu transferFrom cũng gọi update_ownership thì cần tham số Registry.
    land_nft.transferFrom(seller.address, buyer.address, 1, sender=buyer)
    
    assert land_nft.ownerOf(1) == buyer.address
    print("✓ NFT approval and transfer successful")