from ape import accounts, project, convert

def main():
    # 1. KHỞI TẠO TÀI KHOẢN
    # accounts.test_accounts tự động tạo 10 ví có sẵn ETH trên mạng local
    admin = accounts.load("myacc")
    admin.set_autosign(True, passphrase="test123456")
    
    seller = accounts.load("voter1")
    seller.set_autosign(True, passphrase="test1")
    
    buyer = accounts.load("voter2")
    buyer.set_autosign(True, passphrase="test2")

    
    print("-> Đã bơm xong 10-100 ETH cho mỗi tài khoản.")
    print(f"--- Bắt đầu Deploy với Admin: {admin.address} ---")

    # 2. DEPLOY CONTRACTS
    # Lưu ý: LandNFT và LandRegistry phụ thuộc lẫn nhau. 
    # Chiến thuật: Deploy NFT trước với admin làm minter tạm thời, sau đó set lại minter là Registry.
    
    # Deploy LandNFT
    # Tham số: name, symbol, minter (tạm thời là admin)
    land_nft = project.LandNFT.deploy("VietLand", "VLAND", admin, sender=admin)
    print(f"1. LandNFT deployed tại: {land_nft.address}")

    # Deploy LandRegistry
    # Tham số: land_nft_address
    land_registry = project.LandRegistry.deploy(land_nft.address, sender=admin)
    print(f"2. LandRegistry deployed tại: {land_registry.address}")

    # CẬP NHẬT MINTER CHO NFT
    # Bây giờ gán quyền minter chính thức cho LandRegistry
    land_nft.set_minter(land_registry.address, sender=admin)
    print("-> Đã cập nhật Minter của NFT thành LandRegistry")

    # Deploy Marketplace
    # Tham số: land_nft_address, listing_fee, cancel_penalty
    listing_fee = convert("0.001 ether", int)
    cancel_penalty = convert("0.005 ether", int)
    marketplace = project.Marketplace.deploy(
        land_nft.address, 
        listing_fee, 
        cancel_penalty, 
        sender=admin
    )
    print(f"3. Marketplace deployed tại: {marketplace.address}")
    print("-" * 50)

    # 3. KỊCH BẢN: ĐĂNG KÝ ĐẤT (USER A)
    print("\n--- Kịch bản 1: Seller đăng ký đất ---")
    land_address = "123 Nguyen Hue, District 1, HCMC"
    area = 100
    cccd_seller = "079012345678"
    pdf_uri = "ipfs://QmPdf..."
    img_uri = "ipfs://QmImg..."

    tx = land_registry.register_land(
        land_address, area, cccd_seller, pdf_uri, img_uri, 
        sender=seller
    )
    # Lấy land_id từ sự kiện (hoặc tính toán, ở đây giả sử là 1 vì là lần đầu)
    land_id = 1 
    print(f"Seller đã đăng ký đất. Land ID: {land_id}")
    
    # Kiểm tra trạng thái
    assert land_registry.get_land_status(land_id) == 0 # 0 = Pending
    print("-> Trạng thái đất: Pending")

    # 4. KỊCH BẢN: ADMIN DUYỆT ĐẤT
    print("\n--- Kịch bản 2: Admin duyệt và Mint NFT ---")
    metadata_uri = "ipfs://QmMetadata..."
    
    # Admin duyệt
    land_registry.approve_land(land_id, metadata_uri, sender=admin)
    
    # Kiểm tra kết quả
    assert land_registry.get_land_status(land_id) == 1 # 1 = Approved
    assert land_nft.ownerOf(land_id) == seller.address # Seller phải sở hữu NFT
    print(f"-> Đất #{land_id} đã được duyệt.")
    print(f"-> NFT #{land_id} đã nằm trong ví của Seller: {seller.address}")

    # 5. KỊCH BẢN: SELLER ĐĂNG BÁN (LISTING)
    print("\n--- Kịch bản 3: Seller đăng bán trên Marketplace ---")
    price = convert("10 ether", int) # Giá bán 10 ETH

    # Bước 1: Cấp quyền (Approval)
    # Seller cho phép Marketplace chuyển NFT của mình
    land_nft.setApprovalForAll(marketplace.address, True, sender=seller)
    print("-> Seller đã cấp quyền (Approve) cho Marketplace")

    # Bước 2: Tạo Listing
    # Gửi kèm phí listing (msg.value)
    marketplace.create_listing(
        land_id,
        land_registry.get_land(land_id).owner_cccd,
        price, 
        sender=seller, 
        value=listing_fee
    )
    listing_id = 1
    print(f"-> Listing #{listing_id} đã được tạo với giá 10 ETH")

    # 6. KỊCH BẢN: BUYER MUA ĐẤT
    print("\n--- Kịch bản 4: Buyer đặt cọc mua đất ---")
    cccd_buyer = "079087654321"
    
    # Buyer gửi tiền (đúng bằng giá bán) vào contract
    marketplace.initiate_transaction(
        listing_id, 
        cccd_buyer, 
        sender=buyer, 
        value=price
    )
    tx_id = 1
    print(f"-> Buyer đã chuyển 10 ETH vào Marketplace. Transaction ID: {tx_id}")
    
    # Kiểm tra số dư ký quỹ
    escrow = marketplace.get_escrow_balance(buyer.address)
    assert escrow == price
    print(f"-> Số dư ký quỹ của Buyer trong contract: {escrow} Wei")

    # 7. KỊCH BẢN: ADMIN DUYỆT GIAO DỊCH
    print("\n--- Kịch bản 5: Admin duyệt giao dịch ---")
    
    # Admin duyệt giao dịch #1
    marketplace.approve_transaction(tx_id, sender=admin)
    
    # 8. KIỂM TRA KẾT QUẢ CUỐI CÙNG
    print("\n--- Kết quả cuối cùng ---")
    
    # 1. Chủ sở hữu mới của NFT phải là Buyer
    new_owner = land_nft.ownerOf(land_id)
    print(f"Chủ sở hữu NFT #{land_id}: {new_owner}")
    assert new_owner == buyer.address
    print("-> CHECK: NFT đã chuyển sang Buyer thành công!")

    # 2. CCCD trong NFT phải được cập nhật thành của Buyer
    land_data = land_nft.get_land_data(land_id)
    # land_data là một tuple/struct, truy cập index hoặc attribute tùy version ape
    # Giả sử struct LandData(token_id, owner_cccd)
    print(f"CCCD lưu trong NFT: {land_data.owner_cccd}") 
    assert land_data.owner_cccd == cccd_buyer
    print("-> CHECK: CCCD đã cập nhật thành công!")

    # 3. Trạng thái Listing phải là Completed (2)
    listing = marketplace.get_listing(listing_id)
    assert listing.status == 2
    print("-> CHECK: Listing status là Completed!")

    print("\n=== TEST HOÀN TẤT THÀNH CÔNG ===")