# file: mock_blockchain.py
MOCK_ADMIN_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
MOCK_USER_A_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
MOCK_USER_B_ADDRESS = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
MOCK_LAND_NFT_ADDRESS = "0x_LandNFT_Contract_Address_Mock_0000000"
MOCK_LAND_REGISTRY_ADDRESS = "0x_LandRegistry_Contract_Address_Mock_000"
MOCK_MARKETPLACE_ADDRESS = "0x_Marketplace_Contract_Address_Mock_00"
class MockAccount:
    """Lớp giả mạo cho tài khoản Ape."""
    def __init__(self, address):
        self.address = address

class MockLandRegistry:
    """Lớp giả mạo cho contract LandRegistry."""
    def __init__(self):
        print("!!! A SINGLE MockLandRegistry INSTANCE CREATED !!!")
        
        self.next_land_id = 8
        self.admin = MOCK_ADMIN_ADDRESS

         # --- Internal Data Storage ---
        self._land_parcels_data = {
            1: (1, '123 Đường A, Quận 1', 100, '079011111111', 0, 'ipfs://QmPDF1...', 'ipfs://QmImage1...'),
            2: (2, '456 Đường B, Quận 3', 150, '079011111111', 1, 'ipfs://QmPDF2...', 'ipfs://QmImage2...'),
            3: (3, '789 Đường C, Quận 5', 120, '079022222222', 0, 'ipfs://QmPDF3...', 'ipfs://QmImage3...'),
            4: (4, '101 Đường D, Quận 7', 200, '079022222222', 1, 'ipfs://QmPDF4...', 'ipfs://QmImage4...'),
            5: (5, '212 Đường E, Bình Thạnh', 80, '079022222222', 2, 'ipfs://QmPDF5...', 'ipfs://QmImage5...'),
            6: (6, '333 Đường F, Thủ Đức', 180, '079033333333', 0, 'ipfs://QmPDF6...', 'ipfs://QmImage6...'),
            7: (7, '444 Đường G, Quận 12', 95, '079044444444', 0, 'ipfs://QmPDF7...', 'ipfs://QmImage7...'),
        }
        self._land_to_owner_data = {
            1: MOCK_USER_A_ADDRESS, 2: MOCK_USER_A_ADDRESS, 3: MOCK_USER_B_ADDRESS,
            4: MOCK_USER_B_ADDRESS, 5: MOCK_USER_B_ADDRESS, 6: MOCK_USER_A_ADDRESS, 7: MOCK_USER_B_ADDRESS,
        }
        self._owner_to_lands_data = {
            MOCK_USER_A_ADDRESS: [1, 2, 6], MOCK_USER_B_ADDRESS: [3, 4, 5, 7]
        }
        self._land_ids_data = {
            '079011111111': 1, '079022222222': 3, # etc.
        }

    def land_parcels(self, land_id):
        data = self._land_parcels_data.get(land_id)
        # Trả về tuple giống hệt struct của Vyper để test
        return data if data else (0, "", 0, "", 0, "", "")

    def land_to_owner(self, land_id):
        return self._land_to_owner_data.get(land_id, "0x" + "0"*40)
    
    def owner_to_land(self, owner_address):
        return self._owner_to_lands_data.get(owner_address, [])
    
    def land_ids(self, cccd):
        return self._land_ids_data.get(cccd, 0)

    def get_land(self, land_id):
        # Hàm tiện ích cho GUI, trả về dict
        data = self.land_parcels(land_id)
        return { 'id': data[0], 'land_address': data[1], 'area': data[2], 'owner_cccd': data[3], 'status': data[4], 'pdf_uri': data[5], 'image_uri': data[6] }

    def get_land_owner(self, land_id): return self.land_to_owner(land_id)
    def get_lands_by_owner(self, owner_address): return self.owner_to_lands(owner_address)
    def is_land_pending(self, land_id): return self.land_parcels(land_id)[4] == 0

    def approve_land(self, land_id, metadata_uri, sender):
        assert sender.address == self.admin, "Mock: Not admin"
        data = list(self._land_parcels_data[land_id])
        assert data[4] == 0, "Mock: Not pending"
        data[4] = 1 # Update status
        self._land_parcels_data[land_id] = tuple(data)
        # Giả lập việc gọi mint, không cần trả về gì cụ thể
        return {"txn_hash": f"0xmock_approve_{land_id}"}


    def reject_land(self, land_id, sender):
        print(f"[MOCK] Admin {sender.address} rejecting land #{land_id}...")
        if self.parcels[land_id]['status'] == 0:
            self.parcels[land_id]['status'] = 2
            print(f"      -> Land #{land_id} status changed to Rejected.")
            return {"txn_hash": "0xmock_reject_tx_hash_" + str(land_id)}
        raise Exception("Land is not in pending state")


class MockMarketplace:
    def __init__(self, admin_address):
        print("!!! MOCK: Marketplace instance created !!!")
        
        # Public variables
        self.admin = admin_address
        self.listing_fee = 10000000000000000
        self.cancel_penalty = 50000000000000000
        self.next_listing_id = 3
        self.next_tx_id = 1
        self.land_nft = MOCK_LAND_NFT_ADDRESS
        self.address = MOCK_MARKETPLACE_ADDRESS
        
        # Internal data
        self._listings_data = {
            1: (1, 2, '079011111111', 10**18, 0, 0), # id, token_id, cccd, price, status, created_at
            2: (2, 4, '079022222222', 2.5 * 10**18, 0, 0),
        }
        
    # Public HashMap Getters
    def listings(self, listing_id):
        data = self._listings_data.get(listing_id)
        # Trả về dict mô phỏng struct
        if not data: return {'listing_id': 0}
        return {'listing_id': data[0], 'token_id': data[1], 'seller_cccd': data[2], 'price': data[3], 'status': data[4], 'created_at': data[5]}

    # Functions
    def create_listing(self, token_id, seller_cccd, price, sender, value):
        assert value >= self.listing_fee
        listing_id = self.next_listing_id
        self._listings_data[listing_id] = (listing_id, token_id, seller_cccd, price, 0, 0)
        self.next_listing_id += 1
        return {"txn_hash": f"0xmock_create_listing_{listing_id}"}
        
    def initiate_transaction(self, listing_id, buyer_cccd, sender, value):
        listing = list(self._listings_data[listing_id])
        assert listing[4] == 0 and value == listing[3]
        listing[4] = 1 # InTransaction
        self._listings_data[listing_id] = tuple(listing)
        return {"txn_hash": f"0xmock_initiate_tx_{listing_id}"}


class MockLandNFT:
    def __init__(self, registry_mock):
        print("!!! MOCK: LandNFT instance created !!!")
        self._registry = registry_mock # Cần để tra cứu owner
        
        # Public variables
        self.name = "Mock Land NFT"
        self.symbol = "MLND"
        self.minter = MOCK_LAND_REGISTRY_ADDRESS
        
        # Internal data
        self._approvals = {}
        self._operator_approvals = {}

    # Public HashMap Getters
    def owner_of(self, token_id):
        return self._registry.get_land_owner(token_id)
    
    # Functions
    def isApprovedForAll(self, owner, operator):
        return self._operator_approvals.get(owner, {}).get(operator, False)

    def setApprovalForAll(self, operator, approved, sender):
        owner = sender.address
        if owner not in self._operator_approvals: self._operator_approvals[owner] = {}
        self._operator_approvals[owner][operator] = approved
        return {"txn_hash": "0xmock_approval_tx"}

    def transferWithCCCD(self, from_, to, token_id, new_cccd, sender):
        # Logic chuyển quyền sở hữu sẽ được giả lập trong MockLandRegistry
        # Hàm này chỉ cần xác nhận nó đã được gọi
        print(f"[MOCK NFT] transferWithCCCD called for token {token_id} to {to}")
        return {"txn_hash": f"0xmock_transfer_{token_id}"}
