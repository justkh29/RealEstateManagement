# file: crypto_utils.py
import os
import base64
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

# Tên file khóa
PRIVATE_KEY_FILE = "admin_private_key.pem" # CHỈ CÓ TRÊN MÁY ADMIN
PUBLIC_KEY_FILE = "admin_public_key.pem"   # CÓ TRÊN TẤT CẢ MÁY
DATA_FILE = "user_local_data.json"

def generate_keys():
    """Tạo cặp khóa mới (Chỉ chạy 1 lần trên máy Admin)."""
    if os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE):
        return # Đã có khóa, không tạo lại

    print("--- Đang tạo cặp khóa RSA Admin mới ---")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Lưu Private Key
    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Lưu Public Key
    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print("--- Đã tạo khóa thành công ---")

def get_public_key():
    """Đọc Public Key (Dùng để mã hóa)."""
    if not os.path.exists(PUBLIC_KEY_FILE):
        # Nếu chưa có khóa nào, tự động tạo (Dành cho lần chạy đầu tiên)
        generate_keys()
        
    with open(PUBLIC_KEY_FILE, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def get_private_key():
    """Đọc Private Key (Dùng để giải mã). Trả về None nếu không tìm thấy."""
    if not os.path.exists(PRIVATE_KEY_FILE):
        return None # Máy User sẽ rơi vào trường hợp này
        
    with open(PRIVATE_KEY_FILE, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def encrypt_data(message: str) -> str:
    """Mã hóa chuỗi bằng Public Key."""
    try:
        public_key = get_public_key()
        encrypted = public_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        # Trả về chuỗi base64 để lưu vào contract
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        print(f"Lỗi mã hóa: {e}")
        return message # Trả về gốc nếu lỗi (hoặc xử lý khác)

def decrypt_data(encrypted_message_b64: str) -> str:
    """Giải mã chuỗi bằng Private Key."""
    private_key = get_private_key()
    
    if private_key is None:
        # Nếu không có khóa bí mật (Máy User)
        return "[Dữ liệu được bảo mật]"

    try:
        encrypted_bytes = base64.b64decode(encrypted_message_b64)
        original_message = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return original_message.decode('utf-8')
    except Exception as e:
        # Nếu giải mã thất bại (do data rác hoặc sai khóa)
        return "[Không thể giải mã]"

def load_local_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_local_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_land_info(land_address_str, real_cccd):
    """
    Lưu mapping: Địa chỉ đất -> CCCD thật.
    Ta dùng địa chỉ đất làm key vì lúc đăng ký chưa biết TokenID.
    """
    data = load_local_data()
    # Key là địa chỉ đất (viết thường để chuẩn hóa)
    data[land_address_str.strip().lower()] = real_cccd
    save_local_data(data)

def get_real_cccd(land_address_str):
    """Lấy CCCD thật dựa trên địa chỉ đất."""
    data = load_local_data()
    return data.get(land_address_str.strip().lower())