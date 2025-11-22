# @version ^0.4.3
# SPDX-License-Identifier: MIT

# ===================== EVENTS =====================

event Transfer:
    _from: indexed(address)
    _to: indexed(address)
    _tokenId: indexed(uint256)

event Approval:
    _owner: indexed(address)
    _approved: indexed(address)
    _tokenId: indexed(uint256)

event ApprovalForAll:
    _owner: indexed(address)
    _operator: indexed(address)
    _approved: bool

event CCCDUpdated:
    token_id: indexed(uint256)
    old_cccd: String[20]
    new_cccd: String[20]

# ===================== DATA STRUCTURES =====================

struct LandData:
    token_id: uint256
    owner_cccd: String[20]
    metadata_uri: String[128]

# ===================== STATE VARIABLES =====================

name: public(String[50])
symbol: public(String[10])

owner_of: public(HashMap[uint256, address])
balance_of: public(HashMap[address, uint256])
token_uri: public(HashMap[uint256, String[128]])

land_data: public(HashMap[uint256, LandData])

token_approvals: HashMap[uint256, address]
operator_approvals: HashMap[address, HashMap[address, bool]]

minter: public(address)

# ===================== CONSTRUCTOR =====================

@deploy
def __init__(_name: String[50], _symbol: String[10], _minter_address: address):
    self.name = _name
    self.symbol = _symbol
    self.minter = _minter_address

# ===================== INTERNAL =====================

@internal
def _is_approved_or_owner(spender: address, token_id: uint256) -> bool:
    owner: address = self.owner_of[token_id]
    assert owner != empty(address), "Token does not exist"
    return (
        spender == owner or
        self.token_approvals[token_id] == spender or
        self.operator_approvals[owner][spender]
    )

@internal
def _transfer(from_: address, to: address, token_id: uint256):
    # Clear approvals
    self.token_approvals[token_id] = empty(address)
    
    # Update balances
    self.balance_of[from_] -= 1
    self.balance_of[to] += 1
    
    # Update owner
    self.owner_of[token_id] = to
    
    log Transfer(_from=from_, _to=to, _tokenId=token_id)

# ===================== CORE LOGIC =====================

@external
def set_minter(_minter: address):
    """Allow admin to change the minter address"""
    assert msg.sender == self.minter, "Only current minter can change minter"
    self.minter = _minter

@external
def mint(to: address, token_id: uint256, owner_cccd: String[20], metadata_uri: String[128]) -> bool:
    assert msg.sender == self.minter, "Only minter can mint"
    assert self.owner_of[token_id] == empty(address), "Token ID exists"
    assert to != empty(address), "Invalid recipient"

    self.owner_of[token_id] = to
    self.balance_of[to] += 1
    self.token_uri[token_id] = metadata_uri

    self.land_data[token_id] = LandData(
        token_id=token_id,
        owner_cccd=owner_cccd,
        metadata_uri=metadata_uri
    )
    log Transfer(_from=empty(address), _to=to, _tokenId=token_id)

    return True

@external
def transferWithCCCD(from_: address, to: address, token_id: uint256, new_cccd: String[20]):
    assert self._is_approved_or_owner(msg.sender, token_id), "Not owner or approved"
    assert self.owner_of[token_id] == from_, "Invalid owner"
    assert to != empty(address), "Invalid recipient"

    # Clear approval
    self.token_approvals[token_id] = empty(address)

    # Update balances and owner
    self.balance_of[from_] -= 1
    self.balance_of[to] += 1
    self.owner_of[token_id] = to

    # Update CCCD
    old_data: LandData = self.land_data[token_id]
    old_cccd: String[20] = old_data.owner_cccd
    self.land_data[token_id] = LandData(
        token_id=token_id,
        owner_cccd=new_cccd,
        metadata_uri=old_data.metadata_uri
    )

    log Transfer(_from=from_, _to=to, _tokenId=token_id)
    log CCCDUpdated(token_id=token_id, old_cccd=old_cccd, new_cccd=new_cccd)

# ===================== ERC-721 STANDARD =====================

@external
def transferFrom(_from: address, _to: address, _tokenId: uint256):
    assert self._is_approved_or_owner(msg.sender, _tokenId), "Not owner or approved"
    assert self.owner_of[_tokenId] == _from, "Invalid owner"
    assert _to != empty(address), "Invalid recipient"
    
    self._transfer(_from, _to, _tokenId)

@external
def safeTransferFrom(_from: address, _to: address, _tokenId: uint256, _data: Bytes[1024]=b""):
    assert self._is_approved_or_owner(msg.sender, _tokenId), "Not owner or approved"
    assert self.owner_of[_tokenId] == _from, "Invalid owner"
    assert _to != empty(address), "Invalid recipient"
    
    self._transfer(_from, _to, _tokenId)
    
    # In a real implementation, you would check if the recipient is a contract
    # and call onERC721Received if it is

@external
def approve(_to: address, _tokenId: uint256):
    owner: address = self.owner_of[_tokenId]
    assert msg.sender == owner or self.operator_approvals[owner][msg.sender], "Not authorized"
    self.token_approvals[_tokenId] = _to
    log Approval(_owner=owner, _approved=_to, _tokenId=_tokenId)

@external
def setApprovalForAll(_operator: address, _approved: bool):
    self.operator_approvals[msg.sender][_operator] = _approved
    log ApprovalForAll(_owner=msg.sender, _operator=_operator, _approved=_approved)

@view
@external
def getApproved(_tokenId: uint256) -> address:
    assert self.owner_of[_tokenId] != empty(address), "Token does not exist"
    return self.token_approvals[_tokenId]

@view
@external
def isApprovedForAll(_owner: address, _operator: address) -> bool:
    return self.operator_approvals[_owner][_operator]

@view
@external
def ownerOf(_tokenId: uint256) -> address:
    owner: address = self.owner_of[_tokenId]
    assert owner != empty(address), "Token does not exist"
    return owner

@view
@external
def get_land_data(_tokenId: uint256) -> LandData:
    return self.land_data[_tokenId]