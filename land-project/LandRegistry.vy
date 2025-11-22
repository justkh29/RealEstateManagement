# @version ^0.4.3
# SPDX-License-Identifier: MIT
# @title LandRegistry

# =====================================================
# =============== INTERFACE & EVENTS ==================
# =====================================================

interface ILandNFT:
    def mint(_to: address, _token_id: uint256, _owner_cccd: String[20], _metadata_uri: String[100]) -> bool: nonpayable

event LandRegistered:
    land_id: indexed(uint256)
    owner: indexed(address)
    owner_cccd: String[20]

event LandApproved:
    land_id: indexed(uint256)
    admin: indexed(address)

event LandRejected:
    land_id: indexed(uint256)
    admin: indexed(address)

# =====================================================
# ================== DATA STRUCTURES ==================
# =====================================================

struct LandParcel:
    id: uint256
    land_address: String[100]
    area: uint256
    owner_cccd: String[20]
    status: uint8  # 0: Pending, 1: Approved, 2: Rejected
    pdf_uri: String[100]
    image_uri: String[100]

# =====================================================
# ================= STATE VARIABLES ===================
# =====================================================

land_parcels: public(HashMap[uint256, LandParcel])
land_to_owner: public(HashMap[uint256, address])
owner_to_lands: public(HashMap[address, DynArray[uint256, 1000]])  
lands_count: public(HashMap[address, uint256]) 
land_ids: public(HashMap[String[20], DynArray[uint256, 100]])  # ADD THIS LINE - maps CCCD to land_id 

next_land_id: public(uint256)
admin: public(address)
land_nft: public(address)

# =====================================================
# ===================== CONSTRUCTOR ===================
# =====================================================

@deploy
def __init__(_land_nft_address: address):
    self.admin = msg.sender
    self.land_nft = _land_nft_address
    self.next_land_id = 1  

# =====================================================
# ====================== MODIFIERS ====================
# =====================================================

@internal
def _only_admin():
    assert msg.sender == self.admin, "Caller is not the admin"

@external
def change_admin(new_admin: address):
    self._only_admin()
    self.admin = new_admin


@external
def set_land_nft(_land_nft_address: address):
    self._only_admin()
    self.land_nft = _land_nft_address


# =====================================================
# ====================== CORE LOGIC ===================
# =====================================================

@external
def register_land(
    _land_address: String[100],
    _area: uint256,
    _owner_cccd: String[20],
    _pdf_uri: String[100],
    _image_uri: String[100]
):

    land_id: uint256 = self.next_land_id

    # Fix string length checks
    assert len(_land_address) > 0, "Land address cannot be empty"
    assert _area > 0, "Area must be greater than 0"
    assert len(_owner_cccd) > 0, "Owner CCCD cannot be empty"
    assert len(_pdf_uri) > 0, "PDF URI cannot be empty"
    assert len(_image_uri) > 0, "Image URI cannot be empty"
    
    self.land_parcels[land_id] = LandParcel(
        id=land_id,
        land_address=_land_address,
        area=_area,
        owner_cccd=_owner_cccd,
        status=0,  # 0 = Pending
        pdf_uri=_pdf_uri,
        image_uri=_image_uri
    )

    self.land_to_owner[land_id] = msg.sender
    self.land_ids[_owner_cccd].append(land_id)  # Store the mapping

    # Fix array handling - initialize if needed
    if self.lands_count[msg.sender] == 0:
        self.owner_to_lands[msg.sender] = [land_id]
    else:
        self.owner_to_lands[msg.sender].append(land_id)
    self.lands_count[msg.sender] += 1
    
    # owner_lands_count: uint256 = self.lands_count[msg.sender]
    # assert owner_lands_count < 100, "Maximum land parcels per owner reached"
    # self.owner_to_lands[msg.sender][owner_lands_count] = land_id
    # self.lands_count[msg.sender] += 1
    
    self.next_land_id += 1
    
    log LandRegistered(land_id=land_id, owner=msg.sender, owner_cccd=_owner_cccd)

@external
def approve_land(_land_id: uint256, _metadata_uri: String[100]):
    self._only_admin()
    
    parcel: LandParcel = self.land_parcels[_land_id]
    assert parcel.id != 0, "Land parcel does not exist"
    assert parcel.status == 0, "Land is not in pending state"

    # Update status to Approved
    updated_parcel: LandParcel = LandParcel(
        id=parcel.id,
        land_address=parcel.land_address,
        area=parcel.area,
        owner_cccd=parcel.owner_cccd,
        status=1,  # 1 = Approved
        pdf_uri=parcel.pdf_uri,
        image_uri=parcel.image_uri
    )
    self.land_parcels[_land_id] = updated_parcel
    
    owner_address: address = self.land_to_owner[_land_id]
    owner_cccd: String[20] = parcel.owner_cccd  
    
    mint_success: bool = extcall ILandNFT(self.land_nft).mint(owner_address, _land_id, owner_cccd, _metadata_uri)
    assert mint_success, "NFT minting failed"
    
    log LandApproved(land_id=_land_id, admin=msg.sender)


@external
def reject_land(_land_id: uint256):
    self._only_admin()
    
    parcel: LandParcel = self.land_parcels[_land_id]
    assert parcel.id != 0, "Land parcel does not exist"
    assert parcel.status == 0, "Land is not in pending state"
    
    updated_parcel: LandParcel = LandParcel(
        id=parcel.id,
        land_address=parcel.land_address,
        area=parcel.area,
        owner_cccd=parcel.owner_cccd,
        status=2,  # 2 = Rejected
        pdf_uri=parcel.pdf_uri,
        image_uri=parcel.image_uri
    )
    self.land_parcels[_land_id] = updated_parcel
    
    log LandRejected(land_id=_land_id, admin=msg.sender)

# =====================================================
# ===================== VIEWERS =======================
# =====================================================

@view
@external
def get_land(_land_id: uint256) -> LandParcel:
    return self.land_parcels[_land_id]

@view
@external
def get_lands_by_owner(_owner: address) -> DynArray[uint256, 1000]:
    return self.owner_to_lands[_owner]

@view
@external
def get_lands_count_by_owner(_owner: address) -> uint256:
    return self.lands_count[_owner]

@view
@external
def get_land_owner(_land_id: uint256) -> address:
    return self.land_to_owner[_land_id]

@view
@external
def get_land_status(_land_id: uint256) -> uint8:
    return self.land_parcels[_land_id].status

@view
@external
def is_land_approved(_land_id: uint256) -> bool:
    return self.land_parcels[_land_id].status == 1

@view
@external
def is_land_pending(_land_id: uint256) -> bool:
    return self.land_parcels[_land_id].status == 0

@view
@external
def is_land_rejected(_land_id: uint256) -> bool:
    return self.land_parcels[_land_id].status == 2