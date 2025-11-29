from ape import accounts, project, convert, networks

def main():
    # =========================================================================
    # 1. CẤU HÌNH
    # =========================================================================
    LAND_NFT_ADDR = "0x437AAc235f0Ed378AB9CbD5b7C20B1c3B28b573a"
    LAND_REGISTRY_ADDR = "0x9FfDa9D1FeDdF35a26D2F68a50Fd600e68696469"
    MARKETPLACE_ADDR = "0xa8EFf51482B108A94CB813Af2C59B467Cc5Fa08E"
    
    # CCCD MONG ĐỢI CỦA NGƯỜI MUA (Phải khớp với input khi tạo Transaction)
    EXPECTED_BUYER_CCCD = "079012345678" 

    with networks.ethereum.local.use_provider("http://127.0.0.1:8545"):
        
        print(">>> Đã kết nối thành công vào mạng Local (127.0.0.1:8545)")

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
        # 2. KẾT NỐI VỚI CONTRACT
        # =========================================================================
        try:
            land_nft = project.LandNFT.at(LAND_NFT_ADDR)
            land_registry = project.LandRegistry.at(LAND_REGISTRY_ADDR)
            marketplace = project.Marketplace.at(MARKETPLACE_ADDR)
            print(f"-> Kết nối contract thành công!")
        except Exception as e:
            print(f"LỖI: {e}")
            return

        # =========================================================================
        # 3. KIỂM TRA TRẠNG THÁI HỆ THỐNG
        # =========================================================================
        print("\n--- Bắt đầu kiểm tra trạng thái (Verification) ---")

        land_id = 1
        
        # ---------------------------------------------------------------------
        # [PHẦN BỔ SUNG QUAN TRỌNG] Kiểm tra LandRegistry & CCCD
        # ---------------------------------------------------------------------
        print(f"\n[1] Kiểm tra LandRegistry cho Land ID #{land_id}...")
        
        try:
            # Lấy struct LandParcel
            land_data = land_registry.get_land(land_id)
            status = land_registry.get_land_status(land_id)
            
            print(f"   + Địa chỉ đất: {land_data.land_address}")
            print(f"   + Diện tích:   {land_data.area}")
            print(f"   + Trạng thái:  {status} (1=Approved)")
            
            # --- KIỂM TRA CCCD ---
            current_cccd = land_data.owner_cccd
            print(f"   + CCCD Chủ sở hữu (Trong Registry): {current_cccd}")
            
            # Logic verify CCCD
            if current_cccd == EXPECTED_BUYER_CCCD:
                print(f"   ✅ PASS: CCCD đã được cập nhật sang Buyer ({EXPECTED_BUYER_CCCD}).")
            elif "123" in current_cccd: # Giả sử CCCD cũ có số 123
                print(f"   ❌ FAIL: CCCD vẫn là của Seller cũ ({current_cccd}).")
            else:
                print(f"   ⚠️ INFO: CCCD hiện tại là '{current_cccd}'. Hãy đối chiếu với dữ liệu đầu vào.")

            # Logic verify Status
            if status == 1:
                print("   ✅ PASS: Trạng thái đất hợp lệ.")
            else:
                print(f"   ❌ FAIL: Trạng thái không đúng ({status}).")
                
        except Exception as e:
            print(f"   ❌ Lỗi khi đọc LandRegistry: {e}")

        # ---------------------------------------------------------------------
        # [2] Kiểm tra LandNFT (Đối chiếu dữ liệu chéo)
        # ---------------------------------------------------------------------
        print(f"\n[2] Kiểm tra quyền sở hữu NFT #{land_id}...")
        
        try:
            owner = land_nft.ownerOf(land_id)
            print(f"   + Chủ sở hữu (On-chain): {owner}")
            
            if owner == buyer.address:
                print("   ✅ PASS: NFT đang thuộc về Buyer.")
            else:
                print(f"   ❌ FAIL: NFT đang thuộc về {owner}.")

            # Kiểm tra dữ liệu lưu trong NFT struct (nếu có)
            nft_data = land_nft.get_land_data(land_id)
            nft_cccd = nft_data.owner_cccd
            print(f"   + CCCD lưu trong NFT: {nft_cccd}")
            
            # Verify sự đồng bộ giữa Registry và NFT
            if nft_cccd == land_data.owner_cccd:
                 print("   ✅ PASS: Dữ liệu CCCD đồng bộ giữa LandRegistry và LandNFT.")
            else:
                 print("   ❌ FAIL: Dữ liệu không đồng bộ! (Registry khác NFT).")

        except Exception as e:
            print(f"   ❌ Lỗi khi đọc LandNFT: {e}")

        # [3] Kiểm tra Marketplace (Giữ nguyên)
        print(f"\n[3] Kiểm tra trạng thái giao dịch...")
        try:
            listing = marketplace.get_listing(1)
            transaction = marketplace.get_transaction(1)
            
            if listing.status == 2 and transaction.status == 1:
                print("   ✅ PASS: Marketplace ghi nhận giao dịch đã hoàn tất.")
            else:
                print(f"   ⚠️ INFO: Listing Status: {listing.status}, Transaction Status: {transaction.status}")
        except Exception as e:
             print(f"   ❌ Lỗi marketplace: {e}")

        print("\n=== KẾT THÚC KIỂM TRA ===")

if __name__ == "__main__":
    main()