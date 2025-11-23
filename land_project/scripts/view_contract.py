from ape import accounts, project, convert, networks

def main():
    # =========================================================================
    # 1. CẤU HÌNH
    # =========================================================================
    LAND_NFT_ADDR = "0xA9e4241066371Fbc94a70EaC693CB912e7B0c50f"
    LAND_REGISTRY_ADDR = "0xe7da8D4Dd84787e05041eDf4D0E54112f2d332C9"
    MARKETPLACE_ADDR = "0x40d27357B449845D76ab9d0147Fd33a0f270FAB3"

    # --- QUAN TRỌNG: BẮT ĐẦU KẾT NỐI MẠNG TẠI ĐÂY ---
    # Mọi thao tác với contract phải nằm thụt vào trong khối 'with' này
    with networks.ethereum.local.use_provider("http://127.0.0.1:8545"):
        
        print(">>> Đã kết nối thành công vào mạng Local (127.0.0.1:8545)")

        # Tải tài khoản (Có thể để ngoài, nhưng để trong cho an toàn)
        try:
            admin = accounts.load("myacc")
            admin.set_autosign(True, passphrase="test123456")

            seller = accounts.load("voter1")
            seller.set_autosign(True, passphrase="test1")

            buyer = accounts.load("voter2")
            buyer.set_autosign(True, passphrase="test2")
        except:
            admin = accounts.test_accounts[0]
            seller = accounts.test_accounts[1]
            buyer = accounts.test_accounts[2]

        print(f"--- Kết nối đến mạng với Admin: {admin.address} ---")

        # =========================================================================
        # 2. KẾT NỐI VỚI CONTRACT ĐÃ DEPLOY
        # =========================================================================
        try:
            # Bây giờ lệnh này mới hoạt động vì đã có mạng
            land_nft = project.LandNFT.at(LAND_NFT_ADDR)
            land_registry = project.LandRegistry.at(LAND_REGISTRY_ADDR)
            marketplace = project.Marketplace.at(MARKETPLACE_ADDR)
            
            # Kiểm tra thử một hàm view để chắc chắn
            print(f"-> Kết nối contract thành công! Token Name: {land_nft.name()}")
        except Exception as e:
            print(f"LỖI: Không tìm thấy contract. Kiểm tra lại địa chỉ. {e}")
            return

        # =========================================================================
        # 3. KIỂM TRA TRẠNG THÁI HỆ THỐNG
        # =========================================================================
        print("\n--- Bắt đầu kiểm tra trạng thái (Verification) ---")

        # A. Kiểm tra LandRegistry
        land_id = 1
        print(f"\n[1] Kiểm tra LandRegistry cho Land ID #{land_id}...")
        
        try:
            land_data = land_registry.get_land(land_id)
            status = land_registry.get_land_status(land_id)
            
            print(f"   + Địa chỉ đất: {land_data.land_address}")
            print(f"   + Diện tích: {land_data.area}")
            print(f"   + Trạng thái (kỳ vọng 1-Approved): {status}")
            
            if status == 1:
                print("   ✅ PASS: Đất đã được duyệt.")
            else:
                print(f"   ❌ FAIL: Trạng thái không đúng ({status}).")
        except Exception as e:
            print(f"   ❌ Lỗi khi đọc LandRegistry: {e}")

        # B. Kiểm tra LandNFT
        print(f"\n[2] Kiểm tra quyền sở hữu NFT #{land_id}...")
        
        try:
            owner = land_nft.ownerOf(land_id)
            print(f"   + Chủ sở hữu hiện tại: {owner}")
            print(f"   + Buyer Address:       {buyer.address}")
            
            if owner == buyer.address:
                print("   ✅ PASS: NFT đang thuộc về Buyer (Giao dịch thành công).")
            elif owner == seller.address:
                print("   ❌ FAIL: NFT vẫn thuộc về Seller.")
            else:
                print("   ❌ FAIL: Chủ sở hữu không xác định.")

            nft_data = land_nft.get_land_data(land_id)
            print(f"   + CCCD lưu trong NFT: {nft_data.owner_cccd}")
        except Exception as e:
            print(f"   ❌ Lỗi khi đọc LandNFT: {e}")

        # C. Kiểm tra Marketplace
        listing_id = 1
        tx_id = 1
        print(f"\n[3] Kiểm tra Marketplace Listing #{listing_id} & Transaction #{tx_id}...")
        
        try:
            listing = marketplace.get_listing(listing_id)
            print(f"   + Listing Status (kỳ vọng 2-Completed): {listing.status}")
            
            transaction = marketplace.get_transaction(tx_id)
            print(f"   + Transaction Status (kỳ vọng 1-Approved): {transaction.status}")
            
            if listing.status == 2 and transaction.status == 1:
                print("   ✅ PASS: Giao dịch mua bán đã hoàn tất trọn vẹn.")
            else:
                print("   ❌ FAIL: Trạng thái giao dịch chưa hoàn tất.")
        except Exception as e:
             print(f"   ❌ Lỗi khi đọc Marketplace: {e}")

        # D. Kiểm tra Escrow
        print("\n[4] Kiểm tra số dư ký quỹ (Escrow)...")
        buyer_escrow = marketplace.get_escrow_balance(buyer.address)
        print(f"   + Số dư Buyer: {buyer_escrow} (Kỳ vọng: 0 - đã trừ hết)")
        
        if buyer_escrow == 0:
            print("   ✅ PASS: Tiền ký quỹ đã được xử lý.")
        else:
            print("   ⚠️ WARNING: Vẫn còn tiền trong ký quỹ.")

        print("\n=== KẾT THÚC KIỂM TRA ===")