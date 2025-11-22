# @version ^0.4.3
# SPDX-License-Identifier: MIT
# @title Marketplace

interface ILandNFT:
    def ownerOf(_token_id: uint256) -> address: view
    def transferFrom(_from: address, _to: address, _token_id: uint256): nonpayable
    def transferWithCCCD(_from: address, _to: address, _token_id: uint256, _new_cccd: String[20]): nonpayable

event ListingCreated:
    listing_id: indexed(uint256)
    token_id: uint256
    seller_cccd: String[20]
    price: uint256

event TransactionInitiated:
    tx_id: indexed(uint256)
    listing_id: uint256
    buyer_cccd: String[20]
    amount: uint256

event TransactionApproved:
    tx_id: indexed(uint256)
    buyer_cccd: String[20]
    seller_cccd: String[20]
    amount: uint256

event TransactionRejected:
    tx_id: indexed(uint256)
    reason: String[64]

land_nft: public(address)
admin: public(address)

listing_fee: public(uint256)
cancel_penalty: public(uint256)

next_listing_id: public(uint256)
next_tx_id: public(uint256)

struct Listing:
    listing_id: uint256
    token_id: uint256
    seller_cccd: String[20]
    price: uint256
    status: uint8  # 0: Active, 1: InTransaction, 2: Completed
    created_at: uint256

struct Transaction:
    tx_id: uint256
    listing_id: uint256
    buyer_cccd: String[20]
    buyer_address: address
    amount: uint256
    status: uint8  # 0: Pending, 1: Approved, 2: Rejected, 3: Cancelled
    created_at: uint256

listings: public(HashMap[uint256, Listing])
transactions: public(HashMap[uint256, Transaction])
escrow_balances: public(HashMap[address, uint256])

@deploy
def __init__(_land_nft: address, _listing_fee: uint256, _cancel_penalty: uint256):
    self.land_nft = _land_nft
    self.listing_fee = _listing_fee
    self.cancel_penalty = _cancel_penalty
    self.admin = msg.sender
    self.next_listing_id = 1
    self.next_tx_id = 1

@payable
@external
def create_listing(_token_id: uint256, _seller_cccd: String[20], _price: uint256):
    assert msg.value >= self.listing_fee, "Listing fee required"
    
    # Refund excess payment
    if msg.value > self.listing_fee:
        send(msg.sender, msg.value - self.listing_fee)

    nft_owner: address = staticcall ILandNFT(self.land_nft).ownerOf(_token_id)
    assert nft_owner != empty(address), "Token does not exist"
    assert nft_owner == msg.sender, "Not NFT owner"

    listing_id: uint256 = self.next_listing_id
    self.next_listing_id += 1

    self.listings[listing_id] = Listing(
        listing_id=listing_id,
        token_id=_token_id,
        seller_cccd=_seller_cccd,
        price=_price,
        status=0,  # Active
        created_at=block.timestamp
    )

    log ListingCreated(
        listing_id=listing_id,
        token_id=_token_id,
        seller_cccd=_seller_cccd,
        price=_price
    )

@payable
@external
def initiate_transaction(_listing_id: uint256, _buyer_cccd: String[20]):
    listing: Listing = self.listings[_listing_id]
    assert listing.status == 0, "Listing not active"
    assert msg.value == listing.price, "Incorrect deposit amount"

    tx_id: uint256 = self.next_tx_id
    self.next_tx_id += 1

    self.transactions[tx_id] = Transaction(
        tx_id=tx_id,
        listing_id=_listing_id,
        buyer_cccd=_buyer_cccd,
        buyer_address=msg.sender,
        amount=msg.value,
        status=0,  # Pending
        created_at=block.timestamp
    )

    self.escrow_balances[msg.sender] += msg.value
    self.listings[_listing_id].status = 1  # InTransaction

    log TransactionInitiated(
        tx_id=tx_id,
        listing_id=_listing_id,
        buyer_cccd=_buyer_cccd,
        amount=msg.value
    )

@external
def approve_transaction(_tx_id: uint256):
    assert msg.sender == self.admin, "Only admin"

    tx_data: Transaction = self.transactions[_tx_id]
    assert tx_data.status == 0, "Transaction not pending"

    listing: Listing = self.listings[tx_data.listing_id]
    assert listing.status == 1, "Listing not in transaction"

    seller: address = staticcall ILandNFT(self.land_nft).ownerOf(listing.token_id)
    assert seller != empty(address), "NFT does not exist"

    # SỬA: Dùng transferWithCCCD để update CCCD
    extcall ILandNFT(self.land_nft).transferWithCCCD(
        seller,
        tx_data.buyer_address,
        listing.token_id,
        tx_data.buyer_cccd
    )

    # Transfer payment to seller
    send(seller, tx_data.amount)

    # Update statuses
    self.transactions[_tx_id].status = 1  # Approved
    self.listings[tx_data.listing_id].status = 2  # Completed
    self.escrow_balances[tx_data.buyer_address] -= tx_data.amount

    log TransactionApproved(
        tx_id=_tx_id,
        buyer_cccd=tx_data.buyer_cccd,
        seller_cccd=listing.seller_cccd,
        amount=tx_data.amount
    )


@external
def reject_transaction(_tx_id: uint256, _reason: String[64]):
    assert msg.sender == self.admin, "Only admin"

    tx_data: Transaction = self.transactions[_tx_id]
    assert tx_data.status == 0, "Transaction not pending"

    # Refund buyer
    send(tx_data.buyer_address, tx_data.amount)
    
    # Update statuses
    self.escrow_balances[tx_data.buyer_address] -= tx_data.amount
    self.transactions[_tx_id].status = 2  # Rejected
    self.listings[tx_data.listing_id].status = 0  # Active

    log TransactionRejected(tx_id=_tx_id, reason=_reason)

@external
def buyer_cancel(_tx_id: uint256):
    tx_data: Transaction = self.transactions[_tx_id]
    assert tx_data.status == 0, "Transaction not pending"
    assert msg.sender == tx_data.buyer_address, "Only buyer can cancel"

    penalty: uint256 = self.cancel_penalty
    assert tx_data.amount >= penalty, "Penalty exceeds deposit"
    refund: uint256 = tx_data.amount - penalty

    # Refund minus penalty (penalty stays in contract as cancellation fee)
    send(tx_data.buyer_address, refund)
    
    # Clear the entire escrow balance for this transaction
    self.escrow_balances[tx_data.buyer_address] -= tx_data.amount
    
    # Update statuses
    self.transactions[_tx_id].status = 3  # Cancelled
    self.listings[tx_data.listing_id].status = 0  # Active

@external
def set_land_nft(_land_nft_address: address):
    assert msg.sender == self.admin, "Only admin"
    self.land_nft = _land_nft_address

@external
def set_fees(_listing_fee: uint256, _cancel_penalty: uint256):
    assert msg.sender == self.admin, "Only admin"
    self.listing_fee = _listing_fee
    self.cancel_penalty = _cancel_penalty

@external
def withdraw_fees():
    assert msg.sender == self.admin, "Only admin"
    send(self.admin, self.balance)

@view
@external
def get_listing(_listing_id: uint256) -> Listing:
    return self.listings[_listing_id]

@view
@external
def get_transaction(_tx_id: uint256) -> Transaction:
    return self.transactions[_tx_id]

@view
@external
def get_escrow_balance(_user: address) -> uint256:
    return self.escrow_balances[_user]