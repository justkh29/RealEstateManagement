import ape
import pytest

# Constants
LISTING_FEE = 1000
CANCEL_PENALTY = 100
PRICE = 5000

@pytest.fixture
def active_listing(marketplace, land_registry, land_nft, seller, minted_token_id):
    token_id = minted_token_id
    land_nft.approve(marketplace.address, token_id, sender=seller)
    marketplace.create_listing(token_id, "CCCD_S", PRICE, sender=seller, value=LISTING_FEE)
    return token_id

def test_create_listing_checks(marketplace, land_nft, stranger, seller, minted_token_id):
    # Fail nếu không đủ phí
    with ape.reverts("Listing fee required"):
        marketplace.create_listing(minted_token_id, "C", PRICE, sender=seller, value=LISTING_FEE - 1)
    # Fail nếu không phải owner NFT
    print(seller.address)
    print(ape.accounts[4].address)
    with ape.reverts("Not NFT owner"):
        marketplace.create_listing(minted_token_id, "C", PRICE, sender=stranger , value=LISTING_FEE)

def test_transaction_success_flow(marketplace, land_nft, land_registry, owner, seller, buyer, active_listing):
    listing_id = 1
    
    # Buyer deposits
    marketplace.initiate_transaction(listing_id, "CCCD_BUYER", sender=buyer, value=PRICE)
    
    seller_bal_before = seller.balance
    
    # Admin approves
    marketplace.approve_transaction(1, sender=owner)
    
    # Check Money
    assert seller.balance >= seller_bal_before + PRICE
    assert marketplace.get_escrow_balance(buyer) == 0
    
    # Check NFT
    assert land_nft.ownerOf(active_listing) == buyer
    
    # Check Registry Update (Integration)
    assert land_registry.get_land_owner(active_listing) == buyer
    assert land_registry.get_land(active_listing).owner_cccd == "CCCD_BUYER"

def test_buyer_cancel_penalty(marketplace, buyer, active_listing, owner):
    marketplace.initiate_transaction(1, "CCCD_B", sender=buyer, value=PRICE)
    
    initial_fees = marketplace.collected_fees() # Đang có 1000 từ listing
    
    # Buyer cancel
    marketplace.buyer_cancel(1, sender=buyer)
    
    # Check status
    assert marketplace.get_transaction(1).status == 3 # Cancelled
    assert marketplace.get_listing(1).status == 0 # Active again
    
    # Check fees: Phải tăng thêm bằng penalty
    assert marketplace.collected_fees() == initial_fees + CANCEL_PENALTY
    
    # Check escrow clear
    assert marketplace.get_escrow_balance(buyer) == 0

def test_reject_transaction_refund(marketplace, owner, buyer, active_listing):
    marketplace.initiate_transaction(1, "CCCD_B", sender=buyer, value=PRICE)
    
    buyer_bal_before_reject = buyer.balance
    
    # Admin reject
    marketplace.reject_transaction(1, "Bad buyer", sender=owner)
    
    # Buyer nhận lại đủ tiền (trừ gas cost transaction initiate trước đó, nhưng balance sau reject phải tăng)
    assert buyer.balance > buyer_bal_before_reject
    assert marketplace.get_transaction(1).status == 2 # Rejected
    assert marketplace.get_listing(1).status == 0 # Active
