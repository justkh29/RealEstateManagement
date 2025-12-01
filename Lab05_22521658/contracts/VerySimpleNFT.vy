# @version ^0.4.3

ownerOf: public(HashMap[uint256, address])

@deploy
def __init__():
    for i: uint256 in range(10):
        self.ownerOf[i] = msg.sender

@external
def transfer(tokenId: uint256, destination: address):
    if self.ownerOf[tokenId] == msg.sender:
        self.ownerOf[tokenId] = destination
        
    
    
