from ape import accounts, project, convert

def main():
    # 1. SETUP
    admin = accounts.load("myacc")
    admin.set_autosign(True, passphrase="test123456")
    seller = accounts.load("voter1")
    seller.set_autosign(True, passphrase="test1")
    buyer = accounts.load("voter2")
    buyer.set_autosign(True, passphrase="test2")

    print("--- 1. DEPLOYMENT ---")
    land_nft = project.LandNFT.deploy("VietLand", "VLAND", admin, sender=admin)
    land_registry = project.LandRegistry.deploy(land_nft.address, sender=admin)
    
    # Cập nhật minter
    land_nft.set_minter(land_registry.address, sender=admin)
    
    listing_fee = convert("0.001 ether", int)
    cancel_penalty = convert("0.5 ether", int) # Phạt 0.5 ETH cho dễ thấy
    marketplace = project.Marketplace.deploy(land_nft.address, listing_fee, cancel_penalty, sender=admin)
    
    print("Deployment completed.")

    # ==========================================
    # SCENARIO A: GIAO DỊCH THÀNH CÔNG (HAPPY PATH)
    # ==========================================
    print("\n=== SCENARIO A: MUA BÁN THÀNH CÔNG ===")
    
    # A1. Seller đăng ký đất
    cccd_seller = "079011111111"
    tx = land_registry.register_land("Quan 1", 100, cccd_seller, "pdf", "img", sender=seller)
    land_id_1 = 1
    
    # A2. Admin duyệt đất
    land_registry.approve_land(land_id_1, "meta_uri", sender=admin)
    assert land_nft.ownerOf(land_id_1) == seller.address
    
    # A3. Seller đăng bán (10 ETH)
    price = convert("10 ether", int)
    land_nft.setApprovalForAll(marketplace.address, True, sender=seller)
    marketplace.create_listing(land_id_1, cccd_seller, price, sender=seller, value=listing_fee)
    listing_id_1 = 1
    
    # A4. Buyer mua
    cccd_buyer = "079022222222"
    marketplace.initiate_transaction(listing_id_1, cccd_buyer, sender=buyer, value=price)
    tx_id_1 = 1
    
    # A5. Admin duyệt giao dịch
    marketplace.approve_transaction(tx_id_1, sender=admin)
    print("-> Admin đã duyệt giao dịch.")

    # ------------------------------------------
    # KIỂM TRA DỮ LIỆU SAU KHI MUA (YÊU CẦU QUAN TRỌNG)
    # ------------------------------------------
    print("\n--- [CHECK] Kiểm tra tính toàn vẹn dữ liệu ---")

    # 1. Kiểm tra Owner NFT
    assert land_nft.ownerOf(land_id_1) == buyer.address
    print("[PASS] NFT Owner là Buyer.")

    # 2. Kiểm tra Registry: LandParcel.owner_cccd
    parcel = land_registry.get_land(land_id_1)
    # parcel struct: (id, address, area, cccd, status, pdf, img)
    # Tùy version ape, truy cập bằng tên thuộc tính
    print(f"Current Parcel CCCD: {parcel.owner_cccd}")
    assert parcel.owner_cccd == cccd_buyer
    print("[PASS] LandParcel trong Registry đã cập nhật CCCD của Buyer.")

    # 3. Kiểm tra Registry: Land Owner Mapping
    reg_owner = land_registry.get_land_owner(land_id_1)
    assert reg_owner == buyer.address
    print("[PASS] LandRegistry ghi nhận Owner là Buyer.")

    # 4. Kiểm tra Registry: Danh sách đất của Buyer
    buyer_lands = land_registry.get_lands_by_owner(buyer.address)
    assert land_id_1 in buyer_lands
    print("[PASS] Đất đã nằm trong danh sách sở hữu của Buyer.")

    # 5. Kiểm tra Registry: Danh sách đất của Seller (phải mất đi)
    seller_lands = land_registry.get_lands_by_owner(seller.address)
    assert land_id_1 not in seller_lands
    print("[PASS] Đất đã bị xóa khỏi danh sách của Seller.")


    # ==========================================
    # SCENARIO B: NGƯỜI MUA HỦY (CANCEL & PENALTY)
    # ==========================================
    print("\n=== SCENARIO B: NGƯỜI MUA HỦY GIAO DỊCH ===")
    
    # B1. Seller đăng ký lô đất thứ 2
    land_registry.register_land("Quan 2", 200, cccd_seller, "pdf2", "img2", sender=seller)
    land_id_2 = 2
    land_registry.approve_land(land_id_2, "meta2", sender=admin)
    
    # B2. Đăng bán
    marketplace.create_listing(land_id_2, cccd_seller, price, sender=seller, value=listing_fee)
    listing_id_2 = 2
    
    # B3. Buyer đặt cọc
    initial_balance = buyer.balance
    marketplace.initiate_transaction(listing_id_2, cccd_buyer, sender=buyer, value=price)
    tx_id_2 = 2
    print(f"-> Buyer đã cọc {price} Wei.")
    
    # B4. Buyer Hủy
    print("-> Buyer tiến hành hủy...")
    marketplace.buyer_cancel(tx_id_2, sender=buyer)
    
    # ------------------------------------------
    # KIỂM TRA PHÍ PHẠT
    # ------------------------------------------
    # Số dư trong escrow phải về 0
    assert marketplace.get_escrow_balance(buyer.address) == 0
    
    # Trạng thái listing quay về Active (0)
    listing_2 = marketplace.get_listing(listing_id_2)
    assert listing_2.status == 0
    
    # Kiểm tra số dư ví Buyer (đã bị trừ phí phạt + gas)
    # Rất khó check chính xác số dư ví vì tốn gas fee thực thi lệnh cancel
    # Nhưng ta có thể check logic trong contract: Collected Fees của Admin tăng lên
    fees = marketplace.collected_fees()
    # Fees = listing_fee (lần 1) + listing_fee (lần 2) + cancel_penalty
    expected_fees = listing_fee * 2 + cancel_penalty
    print(f"Tổng phí Admin thu được: {fees}")
    assert fees == expected_fees
    print("[PASS] Admin đã thu được phí phạt từ Buyer.")
    
    print("\n=== TẤT CẢ TESTCASE ĐỀU THÀNH CÔNG ===")