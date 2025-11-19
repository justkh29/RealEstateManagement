# file: mock_blockchain.py

class MockAccount:
    """Lớp giả mạo cho tài khoản Ape."""
    def __init__(self, address):
        self.address = address

class MockLandRegistry:
    """Lớp giả mạo cho contract LandRegistry."""
    def __init__(self):
        self.next_id = 4
        self.parcels = {
            1: {'id': 1, 'land_address': '123 Đường A, Quận 1', 'area': 100, 'owner_cccd': '0123456789', 'status': 0, 'pdf_uri': 'ipfs://pdf1', 'image_uri': 'ipfs://img1'},
            2: {'id': 2, 'land_address': '456 Đường B, Quận 3', 'area': 150, 'owner_cccd': '0987654321', 'status': 0, 'pdf_uri': 'ipfs://pdf2', 'image_uri': 'ipfs://img2'},
            3: {'id': 3, 'land_address': '789 Đường C, Quận 5', 'area': 120, 'owner_cccd': '1122334455', 'status': 1, 'pdf_uri': 'ipfs://pdf3', 'image_uri': 'ipfs://img3'}, # Đã duyệt
        }
        self.owners = {
            1: "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", # Địa chỉ ví mẫu
            2: "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
            3: "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC",
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

    def admin(self):
        print("[MOCK] Getting admin address from Marketplace...")
        return self._admin