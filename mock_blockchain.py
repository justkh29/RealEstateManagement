# file: mock_blockchain.py (Phiên bản "Mô phỏng chính xác" - trả về Tuples)
import json

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

# Các hàm parser này sẽ được import và sử dụng trong GUI
def parse_land_parcel(parcel_tuple):
    if not parcel_tuple or parcel_tuple[0] == 0: return None
    return {'id': parcel_tuple[0], 'land_address': parcel_tuple[1], 'area': parcel_tuple[2], 
            'owner_cccd': parcel_tuple[3], 'status': parcel_tuple[4], 'pdf_uri': parcel_tuple[5], 'image_uri': parcel_tuple[6]}

def parse_listing(listing_tuple):
    if not listing_tuple or listing_tuple[0] == 0: return None
    return {'listing_id': listing_tuple[0], 'token_id': listing_tuple[1], 'seller_cccd': listing_tuple[2], 
            'price': listing_tuple[3], 'status': listing_tuple[4], 'created_at': listing_tuple[5]}

class MockAccount:
    def __init__(self, address):
        self.address = address

class MockLandRegistry:
    def __init__(self):
        print("!!! MOCK (Tuple Mode): LandRegistry instance created !!!")
        self.next_land_id = 8
        self.admin = MOCK_ADMIN_ADDRESS
        self.land_nft = MOCK_LAND_NFT_ADDRESS
        
        # Lưu trữ dữ liệu dưới dạng tuple, giống hệt struct
        self._land_parcels_data = { # id, address, area, cccd, status, pdf, image
            1: (1, '123 Đường A, Quận 1', 100, '079011111111', 0, 'ipfs://QmPDF1...', 'ipfs://QmImage1...'),
            2: (2, '456 Đường B, Quận 3', 150, '079011111111', 1, 'ipfs://QmPDF2...', 'ipfs://QmImage2...'),
            3: (3, '789 Đường C, Quận 5', 120, '079022222222', 0, 'ipfs://QmPDF3...', 'ipfs://QmImage3...'),
            4: (4, '101 Đường D, Quận 7', 200, '079022222222', 1, 'ipfs://QmPDF4...', 'ipfs://QmImage4...'),
            5: (5, '212 Đường E, Bình Thạnh', 80, '079022222222', 2, 'ipfs://QmPDF5...', 'ipfs://QmImage5...'),
        }
        self._land_to_owner_data = {
            1: MOCK_USER_A_ADDRESS, 2: MOCK_USER_A_ADDRESS, 3: MOCK_USER_B_ADDRESS,
            4: MOCK_USER_B_ADDRESS, 5: MOCK_USER_B_ADDRESS,
        }
        self._owner_to_lands_data = {
            MOCK_USER_A_ADDRESS: [1, 2, 6], MOCK_USER_B_ADDRESS: [3, 4, 5, 7]
        }

    # Public HashMap Getters (TRẢ VỀ TUPLE)
    def land_parcels(self, land_id):
        print(f"[MOCK Registry] Getting land_parcels({land_id})...")
        return self._land_parcels_data.get(land_id, (0, "", 0, "", 0, "", ""))
    
    # Public DynArray Getter (TRẢ VỀ LIST)
    def owner_to_lands(self, owner_address):
        print(f"[MOCK Registry] Getting owner_to_lands({owner_address})...")
        return self._owner_to_lands_data.get(owner_address, [])

    # Functions
    def approve_land(self, land_id, metadata_uri, sender):
        assert sender.address == self.admin, "Mock: Not admin"
        data = list(self._land_parcels_data[land_id])
        assert data[4] == 0, "Mock: Not pending"
        data[4] = 1
        self._land_parcels_data[land_id] = tuple(data)
        return {"txn_hash": f"0xmock_approve_{land_id}"}
    
    # ... (các hàm mock khác nếu cần, nhưng GUI nên dùng các hàm public ở trên)
    # Hàm này vẫn có thể tồn tại để tiện lợi hơn cho GUI
    def get_land(self, land_id): # GUI sẽ không gọi trực tiếp, mà sẽ gọi land_parcels rồi parse
        return parse_land_parcel(self.land_parcels(land_id))

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
class MockLandNFT:
    def __init__(self, registry_mock):
        print("!!! MOCK (Tuple Mode): LandNFT instance created !!!")
        self._registry = registry_mock
        self.name = "Mock Land NFT"
        self.symbol = "MLND"
        self.minter = MOCK_LAND_REGISTRY_ADDRESS
        self._operator_approvals = {}

    # Public HashMap Getter
    def ownerOf(self, token_id):
        # ownerOf không phải HashMap, nó là hàm view trả về address
        return self._registry._land_to_owner_data.get(token_id, "0x" + "0"*40)

    # Functions
    def isApprovedForAll(self, owner, operator):
        return self._operator_approvals.get(owner, {}).get(operator, False)

    def setApprovalForAll(self, operator, approved, sender):
        owner = sender.address
        if owner not in self._operator_approvals: self._operator_approvals[owner] = {}
        self._operator_approvals[owner][operator] = approved
        return {"txn_hash": "0xmock_approval_tx"}
        
    def transferWithCCCD(self, from_, to, token_id, new_cccd, sender):
        # Mô phỏng việc thay đổi chủ sở hữu trong registry
        self._registry._land_to_owner_data[token_id] = to
        # Mô phỏng việc thay đổi CCCD trong registry (nếu cần)
        parcel = list(self._registry._land_parcels_data[token_id])
        parcel[3] = new_cccd
        self._registry._land_parcels_data[token_id] = tuple(parcel)
        print(f"[MOCK NFT] transferWithCCCD successful for token {token_id}")
        return {"txn_hash": f"0xmock_transfer_{token_id}"}


class MockMarketplace:
    def __init__(self, admin_address):
        print("!!! MOCK (Tuple Mode): Marketplace instance created !!!")
        self.admin = admin_address
        self.listing_fee = 10000000000000000
        self.cancel_penalty = 50000000000000000
        self.next_listing_id = 3
        self.land_nft = MOCK_LAND_NFT_ADDRESS
        self.address = MOCK_MARKETPLACE_ADDRESS
        
        # Dữ liệu niêm yết mẫu dưới dạng tuple
        self._listings_data = { # listing_id, token_id, seller_cccd, price, status, created_at
            1: (1, 2, '079011111111', 10**18, 0, 1672531200),
            2: (2, 4, '079022222222', int(2.5 * 10**18), 0, 1672617600),
        }

    # Public HashMap Getter (TRẢ VỀ TUPLE)
    def listings(self, listing_id):
        print(f"[MOCK Marketplace] Getting listings({listing_id})...")
        return self._listings_data.get(listing_id, (0, 0, "", 0, 0, 0))

    # Functions
    def create_listing(self, token_id, seller_cccd, price, sender, value):
        assert value >= self.listing_fee
        listing_id = self.next_listing_id
        self._listings_data[listing_id] = (listing_id, token_id, seller_cccd, price, 0, 0)
        self.next_listing_id += 1
        return {"txn_hash": f"0xmock_create_listing_{listing_id}"}

    # ... (các hàm mock khác nếu cần)