import json
import os
import getpass
from pathlib import Path
from eth_account import Account
from ape import accounts

def main():
    print("=====================================================")
    print("   TOOL IMPORT GETH KEYSTORE VÀO APE FRAMEWORK       ")
    print("=====================================================")

    # 1. Nhập đường dẫn file Keystore
    while True:
        keystore_path_str = input("\n[1] Nhập đường dẫn file Geth Keystore (ví dụ: UTC--2023...): ").strip()
        keystore_path_str = keystore_path_str.replace('"', '').replace("'", "")
        
        keystore_path = Path(keystore_path_str).expanduser().resolve()
        
        if keystore_path.exists() and keystore_path.is_file():
            break
        else:
            print("Lỗi: File không tồn tại hoặc đường dẫn sai. Vui lòng thử lại.")

    # 2. Nhập Alias muốn đặt trong Ape
    container = accounts.containers["accounts"]
    while True:
        alias = input("[2] Nhập tên gợi nhớ (Alias) muốn lưu trong Ape: ").strip()
        if not alias:
            print("Tên không được để trống.")
            continue
        
        if alias in container.aliases:
            print(f"Lỗi: Alias '{alias}' đã tồn tại trong Ape. Vui lòng chọn tên khác.")
        else:
            break

    # 3. Nhập mật khẩu
    # getpass giúp ẩn mật khẩu khi gõ
    password = getpass.getpass("[3] Nhập mật khẩu của file Keystore (sẽ dùng làm mật khẩu Ape luôn): ")

    print("\nĐang xử lý... Vui lòng chờ (việc giải mã có thể mất vài giây)...")

    try:
        # BƯỚC A: Đọc và Giải mã file Geth
        with open(keystore_path, 'r') as f:
            keystore_data = json.load(f)

        private_key_bytes = Account.decrypt(keystore_data, password)
        private_key_hex = private_key_bytes.hex()
        
        if not private_key_hex.startswith("0x"):
            private_key_hex = "0x" + private_key_hex

        print("✅ Giải mã Geth Keystore thành công!")

        # BƯỚC B: Import vào Ape
        acct = Account.from_key(private_key_hex)
        keystore = Account.encrypt(acct.key, password)

        ape_accounts_dir = Path.home() / ".ape" / "accounts" / "accounts"
        ape_accounts_dir.mkdir(parents=True, exist_ok=True)

        keystore_path = ape_accounts_dir / f"{alias}.json"

        with open(keystore_path, "w") as f:
            json.dump(keystore, f)

        print("Import vào Ape THÀNH CÔNG")
        print(f"Alias: {alias}")
        print(f"Address: {acct.address}")



    # ... (phần trên giữ nguyên)
    
    except ValueError as e:
        # SỬA LẠI DÒNG NÀY ĐỂ IN CHI TIẾT LỖI
        print(f"\nTHẤT BẠI: Giải mã thất bại.")
        print(f"Chi tiết lỗi từ hệ thống: {str(e)}")
        print("Gợi ý: Kiểm tra lại CapsLock, hoặc xem file Keystore có bị lỗi copy không.")
        
    except Exception as e:
        print(f"\nLỖI KHÔNG XÁC ĐỊNH: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nĐã hủy bỏ thao tác.")