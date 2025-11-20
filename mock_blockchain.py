# file: mock_blockchain.py
MOCK_USER_ADDRESS = "0x1234567890123456789012345678901234567890"
class MockAccount:
    """Lớp giả mạo cho tài khoản Ape."""
    def __init__(self, address):
        self.address = address

class MockLandRegistry:
    """Lớp giả mạo cho contract LandRegistry."""
    def __init__(self):
        self.next_id = 8
        self.parcels = {
            # --- Đất của User A ---
            1: {'id': 1, 'land_address': '123 Đường A, Quận 1, TP.HCM', 'area': 100, 'owner_cccd': '079012345678', 'status': 1, 'pdf_uri': 'ipfs://QmPDFHash1', 'image_uri': 'ipfs://QmImageHash1'}, # Đang chờ duyệt
            2: {'id': 2, 'land_address': '456 Đường B, Quận 3, TP.HCM', 'area': 150, 'owner_cccd': '079012345678', 'status': 1, 'pdf_uri': 'ipfs://QmPDFHash2', 'image_uri': 'ipfs://QmImageHash2'}, # Đã duyệt
            
            # --- Đất của User B ---
            3: {'id': 3, 'land_address': '789 Đường C, Quận 5, TP.HCM', 'area': 120, 'owner_cccd': '079087654321', 'status': 1, 'pdf_uri': 'ipfs://QmPDFHash3', 'image_uri': 'ipfs://QmImageHash3'}, # Đang chờ duyệt
            4: {'id': 4, 'land_address': '101 Đường D, Quận 7, TP.HCM', 'area': 200, 'owner_cccd': '079087654321', 'status': 1, 'pdf_uri': 'ipfs://QmPDFHash4', 'image_uri': 'ipfs://QmImageHash4'}, # Đã duyệt
            5: {'id': 5, 'land_address': '212 Đường E, Quận Bình Thạnh, TP.HCM', 'area': 80, 'owner_cccd': '079087654321', 'status': 1, 'pdf_uri': 'ipfs://QmPDFHash5', 'image_uri': 'ipfs://QmImageHash5'}, # Đã bị từ chối
            
            # --- Thêm đất đang chờ duyệt để danh sách Admin dài hơn ---
            6: {'id': 6, 'land_address': '333 Đường F, TP. Thủ Đức', 'area': 180, 'owner_cccd': '112233445566', 'status': 1, 'pdf_uri': 'ipfs://QmPDFHash6', 'image_uri': 'ipfs://QmImageHash6'},
            7: {'id': 7, 'land_address': '444 Đường G, Quận 12, TP.HCM', 'area': 95, 'owner_cccd': '665544332211', 'status': 1, 'pdf_uri': 'ipfs://QmPDFHash7', 'image_uri': 'ipfs://QmImageHash7'},
        }
        self.owners = {
            1: MOCK_USER_ADDRESS,
            2: MOCK_USER_ADDRESS,
            3: MOCK_USER_ADDRESS,
            4: MOCK_USER_ADDRESS,
            5: MOCK_USER_ADDRESS,
            6: MOCK_USER_ADDRESS, # Thêm chủ sở hữu cho các mảnh mới
            7: MOCK_USER_ADDRESS,
        }

    def next_land_id(self):
        print("[MOCK] Getting next_land_id...")
        return self.next_id

    def is_land_pending(self, land_id):
        print(f"[MOCK] Checking if land #{land_id} is pending...")
        return self.parcels.get(land_id, {}).get('status') == 0

    def get_land(self, land_id):
        print(f"[MOCK] Getting data for land #{land_id}...")
        return self.parcels.get(land_id)

    def get_land_owner(self, land_id):
        print(f"[MOCK] Getting owner for land #{land_id}...")
        return self.owners.get(land_id)

    def get_lands_by_owner(self, owner_address):
        """Hàm giả mạo để lấy danh sách đất của một người."""
        print(f"[MOCK] Getting lands for owner {owner_address}...")
        owned_ids = []
        for land_id, owner in self.owners.items():
            if owner.lower() == owner_address.lower():
                owned_ids.append(land_id)
        print(f"      -> Found IDs: {owned_ids}")
        return owned_ids

    def approve_land(self, land_id, metadata_uri, sender):
        print(f"[MOCK] Admin {sender.address} approving land #{land_id} with metadata {metadata_uri}...")
        if self.parcels[land_id]['status'] == 0:
            self.parcels[land_id]['status'] = 1
            print(f"      -> Land #{land_id} status changed to Approved.")
            return {"txn_hash": "0xmock_approve_tx_hash_" + str(land_id)}
        raise Exception("Land is not in pending state")


    def reject_land(self, land_id, sender):
        print(f"[MOCK] Admin {sender.address} rejecting land #{land_id}...")
        if self.parcels[land_id]['status'] == 0:
            self.parcels[land_id]['status'] = 2
            print(f"      -> Land #{land_id} status changed to Rejected.")
            return {"txn_hash": "0xmock_reject_tx_hash_" + str(land_id)}
        raise Exception("Land is not in pending state")


class MockMarketplace:
    """Lớp giả mạo cho contract Marketplace."""
    def __init__(self, admin_address):
        self._admin = admin_address
        self._listing_fee = 10000000000000000
        self._cancel_penalty = 50000000000000000

    def admin(self):
        print("[MOCK] Getting admin address from Marketplace...")
        return self._admin
    
    def listing_fee(self):
        return self._listing_fee
    
    def cancel_penalty(self):
        return self._cancel_penalty
    
    def set_fees(self, new_listing_fee, new_cancel_penalty, sender):

        self._listing_fee = new_listing_fee
        self._cancel_penalty = new_cancel_penalty

        print(f"    -> New Listing fee: {self._listing_fee}")
        print(f"    -> New Cancel penalty: {self._cancel_penalty}")

        return {"txn_hash": f"0xmock_set_fees_tx_hash"}