# file: mock_blockchain.py (Phiên bản "Mô phỏng chính xác" - trả về Tuples)
import json
from app_modules.crypto_utils import encrypt_data, decrypt_data
# =============================================================================
# CÁC ĐỊA CHỈ VÍ MẪU (Không đổi)
# =============================================================================
MOCK_ADMIN_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
MOCK_USER_A_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
MOCK_USER_B_ADDRESS = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
MOCK_LAND_NFT_ADDRESS = "0x_LandNFT_Contract_Address_Mock_0000000"
MOCK_LAND_REGISTRY_ADDRESS = "0x_LandRegistry_Contract_Address_Mock_000"
MOCK_MARKETPLACE_ADDRESS = "0x_Marketplace_Contract_Address_Mock_00"

# =============================================================================
# LỚP GIẢ MẠO VÀ CÁC HÀM PARSER
# =============================================================================

class MockAccount:
    def __init__(self, address):
        self.address = address

class MockLandRegistry:
    def __init__(self):
        print("!!! MOCK (Tuple Mode): LandRegistry instance created !!!")
        self.next_land_id = 8
        self.admin = MOCK_ADMIN_ADDRESS
        self.land_nft = MOCK_LAND_NFT_ADDRESS

        cccd_a = encrypt_data('079011111111')
        cccd_b = encrypt_data('079022222222')
        cccd_c = encrypt_data('079033333333')
        cccd_d = encrypt_data('079044444444')

        # Lưu trữ dữ liệu dưới dạng tuple, giống hệt struct
        self._land_parcels_data = { # id, address, area, cccd, status, pdf, image
            1: (1, '123 Đường A, Quận 1', 100, cccd_a, 0, 'ipfs://QmPDF1...', 'ipfs://QmImage1...'),
            2: (2, '456 Đường B, Quận 3', 150, cccd_a, 1, 'ipfs://QmPDF2...', 'ipfs://QmImage2...'),
            3: (3, '789 Đường C, Quận 5', 120, cccd_b, 0, 'ipfs://QmPDF3...', 'ipfs://QmImage3...'),
            4: (4, '101 Đường D, Quận 7', 200, cccd_b, 1, 'ipfs://QmPDF4...', 'ipfs://QmTD1Tga9tqGJBzk16U7CN5noumnbJTHgkWvn9EpkUfAe4'),
            5: (5, '212 Đường E, Bình Thạnh', 80, cccd_b, 2, 'ipfs://QmPDF5...', 'ipfs://QmImage5...'),
            6: (6, '333 Đường F, TP. Thủ Đức', 180, cccd_c, 0, 'ipfs://QmPDF6...', 'ipfs://QmImage6...'), 
            7: (7, '444 Đường G, Quận 12', 95, cccd_d, 0, 'ipfs://QmPDF7...', 'ipfs://QmImage7...'), 
        }
        self._land_to_owner_data = {
            1: MOCK_USER_A_ADDRESS, 2: MOCK_USER_A_ADDRESS, 3: MOCK_USER_B_ADDRESS,
            4: MOCK_USER_B_ADDRESS, 5: MOCK_USER_B_ADDRESS, 6: MOCK_USER_A_ADDRESS,
            7: MOCK_USER_B_ADDRESS
        }
        self._owner_to_lands_data = {
            MOCK_USER_A_ADDRESS: [1, 2, 6], MOCK_USER_B_ADDRESS: [3, 4, 5, 7]
        }
        self._lands_by_cccd_data = {
            cccd_a: [1, 2],
            cccd_b: [3, 4, 5],
            cccd_c: [6],
            cccd_d: [7],
        }

    # Public HashMap Getters (TRẢ VỀ TUPLE)
    def land_parcels(self, land_id):
        print(f"[MOCK Registry] Getting land_parcels({land_id})...")
        return self._land_parcels_data.get(land_id, (0, "", 0, "", 0, "", ""))
    
    # Public DynArray Getter (TRẢ VỀ LIST)
    def owner_to_lands(self, owner_address):
        print(f"[MOCK Registry] Getting owner_to_lands({owner_address})...")
        return self._owner_to_lands_data.get(owner_address, [])

    def register_land(self, _land_address, _area, _owner_cccd, _pdf_uri, _image_uri, sender):
        """
        Mô phỏng hành động người dùng đăng ký hồ sơ đất mới.
        """
        print(f"[MOCK Registry] User {sender.address} is registering a new land...")
        print(f"      -> Data: Address={_land_address}, Area={_area}, CCCD={_owner_cccd}")

        # 1. Mô phỏng các câu lệnh `assert` trong contract
        assert len(_land_address) > 0, "Mock: Land address cannot be empty"
        assert _area > 0, "Mock: Area must be greater than 0"
        assert len(_owner_cccd) > 0, "Mock: Owner CCCD cannot be empty"
        assert len(_pdf_uri) > 0, "Mock: PDF URI cannot be empty"
        assert len(_image_uri) > 0, "Mock: Image URI cannot be empty"

        # 2. Tạo bản ghi mới
        land_id = self.next_land_id
        
        # Struct LandParcel: id, land_address, area, owner_cccd, status, pdf_uri, image_uri
        new_parcel_tuple = (
            land_id,
            _land_address,
            _area,
            _owner_cccd,
            0,  # status = 0 (Pending)
            _pdf_uri,
            _image_uri
        )

        # 3. Cập nhật "trạng thái" của mock contract
        self._land_parcels_data[land_id] = new_parcel_tuple
        self._land_to_owner_data[land_id] = sender.address
        
        if _owner_cccd not in self._lands_by_cccd_data:
            self._lands_by_cccd_data[_owner_cccd] = []
        self._lands_by_cccd_data[_owner_cccd].append(land_id)
        
        if sender.address not in self._owner_to_lands_data:
            self._owner_to_lands_data[sender.address] = []
        self._owner_to_lands_data[sender.address].append(land_id)
        
        # 4. Tăng ID cho lần sau
        self.next_land_id += 1
        
        print(f"      -> Land registered successfully with ID: {land_id}")

        # 5. Trả về một receipt giả
        return {"txn_hash": f"0xmock_register_tx_{land_id}"}

    # Functions
    def approve_land(self, land_id, metadata_uri, sender):
        assert sender.address == self.admin, "Mock: Not admin"
        data = list(self._land_parcels_data[land_id])
        assert data[4] == 0, "Mock: Not pending"
        data[4] = 1
        self._land_parcels_data[land_id] = tuple(data)
        return {"txn_hash": f"0xmock_approve_{land_id}"}
    
    def reject_land(self, land_id, sender):
        """Hàm giả mạo để từ chối hồ sơ (đã sửa lỗi)."""
        print(f"[MOCK] Admin {sender.address} rejecting land #{land_id}...")
        assert sender.address == self.admin, "Mock: Not admin"

        current_parcel_tuple = self._land_parcels_data.get(land_id)
        if not current_parcel_tuple:
            raise Exception(f"Mock: Land with id {land_id} does not exist")

        parcel_list = list(current_parcel_tuple)

        assert parcel_list[4] == 0, "Mock: Land is not in pending state"
        
        parcel_list[4] = 2
        
        self._land_parcels_data[land_id] = tuple(parcel_list)
        
        print(f"      -> Land #{land_id} status changed to Rejected.")
        return {"txn_hash": f"0xmock_reject_tx_hash_{land_id}"}
    
    # Trong file mock_blockchain.py -> class MockLandRegistry

    def update_ownership(self, token_id, new_owner, new_cccd, sender):
        # 0. Ép kiểu token_id về int để đảm bảo nhất quán
        token_id = int(token_id)
        
        print(f"[MOCK Registry] Updating ownership for land #{token_id} to {new_owner}")
        
        # 1. Xác định chủ cũ
        old_owner = self._land_to_owner_data.get(token_id)
        
        # --- DEBUG LOG (Sẽ giúp bạn thấy ngay vấn đề) ---
        print(f"      [DEBUG] Old owner found: {old_owner}")
        if old_owner:
            current_list = self._owner_to_lands_data.get(old_owner, [])
            print(f"      [DEBUG] Old owner's list before remove: {current_list}")
            print(f"      [DEBUG] Is {token_id} in list? {token_id in current_list}")
        # -----------------------------------------------

        # 2. Xóa khỏi danh sách chủ cũ
        if old_owner and old_owner in self._owner_to_lands_data:
            # Sử dụng try/except để an toàn hơn, hoặc kiểm tra in
            if token_id in self._owner_to_lands_data[old_owner]:
                self._owner_to_lands_data[old_owner].remove(token_id)
                print(f"      -> Removed {token_id} from {old_owner}")
            else:
                print(f"      [WARNING] Token #{token_id} not found in old owner's list to remove!")

        # 3. Thêm vào danh sách chủ mới
        if new_owner not in self._owner_to_lands_data:
            self._owner_to_lands_data[new_owner] = []
        
        # Kiểm tra để tránh duplicate (thêm 2 lần)
        if token_id not in self._owner_to_lands_data[new_owner]:
            self._owner_to_lands_data[new_owner].append(token_id)
            print(f"      -> Added {token_id} to {new_owner}")

        # 4. Cập nhật mapping land_to_owner
        self._land_to_owner_data[token_id] = new_owner
        
        # 5. Cập nhật CCCD trong parcel (Tuple update)
        if token_id in self._land_parcels_data:
            parcel = list(self._land_parcels_data[token_id])
            parcel[3] = new_cccd # Index 3 là owner_cccd
            self._land_parcels_data[token_id] = tuple(parcel)
        
        return {"txn_hash": f"0xmock_update_owner_{token_id}"}
    # ... (các hàm mock khác nếu cần, nhưng GUI nên dùng các hàm public ở trên)
    # Hàm này vẫn có thể tồn tại để tiện lợi hơn cho GUI

    def get_land_owner(self, land_id):
        return self._land_to_owner_data.get(land_id, "0x" + "0"*40)
    
    def is_land_pending(self, land_id):
        """Mô phỏng hàm view is_land_pending."""
        parcel = self._land_parcels_data.get(land_id)
        if parcel:
            is_pending = (parcel[4] == 0) # status là index 4
            print(f"[MOCK Registry] Checking is_land_pending({land_id}): {is_pending}")
            return is_pending
        return False

    def is_land_approved(self, land_id):
        """Mô phỏng hàm view is_land_approved."""
        parcel = self._land_parcels_data.get(land_id)
        if parcel:
            return parcel[4] == 1
        return False

    def is_land_rejected(self, land_id):
        """Mô phỏng hàm view is_land_rejected."""
        parcel = self._land_parcels_data.get(land_id)
        if parcel:
            return parcel[4] == 2
        return False
    
    def lands_by_cccd(self, cccd: str):
        """Mô phỏng hàm getter của public HashMap `lands_by_cccd`."""
        print(f"[MOCK Registry] Getting lands_by_cccd({cccd})...")
        return self._lands_by_cccd_data.get(cccd, [])

class MockLandNFT:
    def __init__(self, registry_mock):
        print("!!! MOCK (Tuple Mode): LandNFT instance created !!!")
        self._registry = registry_mock
        self.name = "Mock Land NFT"
        self.symbol = "MLND"
        self.minter = MOCK_LAND_REGISTRY_ADDRESS
        self._approvals = {}
        self._operator_approvals = {}

    # Public HashMap Getter
    def ownerOf(self, token_id):
        # ownerOf không phải HashMap, nó là hàm view trả về address
        return self._registry._land_to_owner_data.get(token_id, "0x" + "0"*40)

    def approve(self, to, token_id, sender):
        print(f"[MOCK NFT] User {sender.address} approved {to} for token #{token_id}")
        # Lưu trữ approval cho token cụ thể
        self._approvals[token_id] = to
        return {"txn_hash": f"0xmock_approve_token_{token_id}"}

    def getApproved(self, token_id):
        # Trả về địa chỉ được approve, hoặc 0x0 nếu không có
        return self._approvals.get(token_id, "0x" + "0"*40)

    # Functions
    def isApprovedForAll(self, owner, operator):
        return self._operator_approvals.get(owner, {}).get(operator, False)

    def setApprovalForAll(self, operator, approved, sender):
        owner = sender.address
        if owner not in self._operator_approvals: self._operator_approvals[owner] = {}
        self._operator_approvals[owner][operator] = approved
        return {"txn_hash": "0xmock_approval_tx"}
        
    def transferWithCCCD(self, from_, to, token_id, new_cccd, sender):
        parcel = list(self._registry._land_parcels_data[token_id])
        parcel[3] = new_cccd
        self._registry._land_parcels_data[token_id] = tuple(parcel)
        print(f"[MOCK NFT] transferWithCCCD successful for token {token_id}")
        self._registry.update_ownership(token_id, to, new_cccd, self) 
        return {"txn_hash": f"0xmock_transfer_{token_id}"}


class MockMarketplace:
    def __init__(self, admin_address, nft_contract_mock=None):
        print("!!! MOCK (Tuple Mode): Marketplace instance created !!!")
        self.admin = admin_address
        self.listing_fee = 10000000000000000
        self.cancel_penalty = 50000000000000000
        self.next_listing_id = 3
        self.land_nft = MOCK_LAND_NFT_ADDRESS
        self._nft_contract_instance = nft_contract_mock
        self.address = MOCK_MARKETPLACE_ADDRESS
        self.next_tx_id = 2
        self._transactions_data = {} # Sẽ lưu các giao dịch đang chờ
        self._escrow_balances = {} # Sẽ lưu tiền ký quỹ của người mua

        # Dữ liệu niêm yết mẫu dưới dạng tuple
        # Mã hóa CCCD cho dữ liệu mẫu
        cccd_a = encrypt_data('079011111111')
        cccd_b = encrypt_data('079022222222')

        self._listings_data = { 
            # listing_id, token_id, seller_cccd (ENCRYPTED), price, status, created_at
            1: (1, 2, cccd_a, 10**18, 0, 1672531200),
            2: (2, 4, cccd_b, int(2.5 * 10**18), 0, 1672617600),
        }

        # tx_id, listing_id, buyer_cccd, buyer_addr, amount, status, created_at
        self._transactions_data[1] = (1, 1, '079022222222', MOCK_USER_B_ADDRESS, 10**18, 0, 0) 

    # Public HashMap Getter (TRẢ VỀ TUPLE)
    def listings(self, listing_id):
        print(f"[MOCK Marketplace] Getting listings({listing_id})...")
        return self._listings_data.get(listing_id, (0, 0, "", 0, 0, 0))

    # Functions
    def create_listing(self, token_id, seller_cccd, price, sender, value):
        assert value >= self.listing_fee
        listing_id = self.next_listing_id
        self._listings_data[listing_id] = (listing_id, int(token_id), seller_cccd, price, 0, 0)
        self.next_listing_id += 1
        return {"txn_hash": f"0xmock_create_listing_{listing_id}"}

    def set_fees(self, new_listing_fee, new_cancel_penalty, sender):

        self.listing_fee = new_listing_fee
        self.cancel_penalty = new_cancel_penalty

        print(f"    -> New Listing fee: {self.listing_fee}")
        print(f"    -> New Cancel penalty: {self.cancel_penalty}")

        return {"txn_hash": f"0xmock_set_fees_tx_hash"}
    # ... (các hàm mock khác nếu cần)

    def initiate_transaction(self, listing_id, buyer_cccd, sender, value):
        """
        Mô phỏng hành động người mua ký quỹ để mua đất.
        """
        print(f"[MOCK Marketplace] User {sender.address} is initiating a transaction for listing #{listing_id}")

        # 1. Lấy thông tin niêm yết
        listing_tuple = self._listings_data.get(listing_id)
        if not listing_tuple:
            raise Exception(f"Mock: Listing with ID {listing_id} does not exist.")

        # 2. Thực hiện các kiểm tra (asserts) giống như contract
        listing_status = listing_tuple[4]
        listing_price = listing_tuple[3]
        
        assert listing_status == 0, f"Mock: Listing #{listing_id} is not active (status is {listing_status})."
        assert value == listing_price, f"Mock: Incorrect deposit amount. Expected {listing_price}, got {value}."

        # 3. Tạo một bản ghi giao dịch mới
        tx_id = self.next_tx_id
        self.next_tx_id += 1

        # Struct Transaction: tx_id, listing_id, buyer_cccd, buyer_address, amount, status, created_at
        new_transaction_tuple = (tx_id, listing_id, buyer_cccd, sender.address, value, 0, 0) # status=0 (Pending)
        self._transactions_data[tx_id] = new_transaction_tuple

        # 4. Ghi nhận tiền ký quỹ
        if sender.address not in self._escrow_balances:
            self._escrow_balances[sender.address] = 0
        self._escrow_balances[sender.address] += value

        # 5. Cập nhật trạng thái của tin đăng thành "InTransaction"
        # Vì tuple là bất biến, chúng ta cần tạo một tuple mới
        temp_listing_list = list(listing_tuple)
        temp_listing_list[4] = 1 # Cập nhật status thành 1 (InTransaction)
        self._listings_data[listing_id] = tuple(temp_listing_list)
        
        print(f"      -> Transaction #{tx_id} created successfully.")
        print(f"      -> Listing #{listing_id} status updated to 'InTransaction'.")
        print(f"      -> Escrow balance for {sender.address} is now {self._escrow_balances[sender.address]}.")

        # 6. Trả về một receipt giả
        return {"txn_hash": f"0xmock_initiate_tx_{tx_id}"}
    
    def transactions(self, tx_id):
        """Mô phỏng hàm getter của public HashMap `transactions`."""
        print(f"[MOCK Marketplace] Getting data for transaction #{tx_id}...")
        return self._transactions_data.get(tx_id, (0, 0, "", "0x"+"0"*40, 0, 99, 0))
    
    def approve_transaction(self, tx_id, sender):
        """
        Duyệt giao dịch: Chuyển tiền, Chuyển NFT, Cập nhật trạng thái.
        """
        assert sender.address == self.admin, "Mock: Not admin"
        
        # 1. Lấy dữ liệu Transaction
        # Struct Transaction: tx_id, listing_id, buyer_cccd, buyer_address, amount, status, created_at
        if tx_id not in self._transactions_data:
             raise Exception("Transaction not found")
             
        tx = list(self._transactions_data[tx_id])
        
        # Kiểm tra trạng thái (index 5 là status)
        assert tx[5] == 0, "Mock: Transaction not pending"
        
        listing_id = tx[1]
        buyer_cccd = tx[2]
        buyer_address = tx[3]
        amount = tx[4] # Dùng để trừ escrow
        
        # 2. Lấy dữ liệu Listing
        # Struct Listing: listing_id, token_id, seller_cccd, price, status, created_at
        listing = list(self._listings_data[listing_id])
        token_id = listing[1]
        
        # 3. Xác định người bán (Seller Address)
        # Vì listing chỉ lưu CCCD, ta phải hỏi NFT contract xem ai đang giữ token này
        if self._nft_contract_instance:
            seller_address = self._nft_contract_instance.ownerOf(token_id)
            
            # 4. Thực hiện chuyển nhượng NFT (Gọi sang contract NFT)
            print(f"[MOCK Marketplace] Calling NFT transfer: {seller_address} -> {buyer_address}")
            self._nft_contract_instance.transferWithCCCD(
                seller_address,  # From
                buyer_address,   # To
                token_id,        # Token ID
                buyer_cccd,      # New CCCD
                self             # Sender là Marketplace
            )
        else:
            print("WARNING: NFT Contract Instance missing in MockMarketplace!")

        # 5. Cập nhật tiền ký quỹ (Escrow)
        if buyer_address in self._escrow_balances:
            self._escrow_balances[buyer_address] -= amount

        # 6. Cập nhật trạng thái Transaction -> Approved (1)
        tx[5] = 1 
        self._transactions_data[tx_id] = tuple(tx)
        
        # 7. Cập nhật trạng thái Listing -> Completed (2)
        listing[4] = 2
        self._listings_data[listing_id] = tuple(listing)
        
        print(f"[MOCK Marketplace] Transaction #{tx_id} approved. NFT transferred.")
        return {"txn_hash": f"0xmock_approve_tx_{tx_id}"}
        
    def reject_transaction(self, tx_id, reason, sender):
        assert sender.address == self.admin, "Mock: Not admin"
        tx = list(self._transactions_data[tx_id])
        assert tx[5] == 0, "Mock: Transaction not pending"
        tx[5] = 2 # Rejected
        self._transactions_data[tx_id] = tuple(tx)

        listing = list(self._listings_data[tx[1]])
        listing[4] = 0 # Back to Active
        self._listings_data[tx[1]] = tuple(listing)

        print(f"[MOCK Marketplace] Transaction #{tx_id} rejected. Reason: {reason}")
        return {"txn_hash": f"0xmock_reject_tx_{tx_id}"}