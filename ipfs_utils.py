# file: ipfs_utils.py (cập nhật)
import requests

# Địa chỉ IP của máy chạy backend Flask
FLASK_BACKEND_URL = "http://192.168.0.140:8000" # Thay bằng IP của bạn
IPFS_URL_VIEWER = "http://192.168.0.140:8000/view/"
def upload_json_to_ipfs(json_data):
    """
    Gửi một đối tượng Python dictionary đến backend Flask để tải lên IPFS.
    Trả về URI theo chuẩn 'ipfs://<CID>'
    """
    try:
        response = requests.post(
            f"{FLASK_BACKEND_URL}/upload_json",
            json=json_data # Gửi dưới dạng JSON body
        )
        response.raise_for_status()
        
        cid = response.json()["cid"]
        print(f"Tải JSON qua backend Flask thành công! CID: {cid}")
        return f"ipfs://{cid}"
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi backend Flask: {e}")
        raise Exception(f"Không thể tải metadata lên IPFS qua backend: {e}")

def upload_file_to_ipfs(file_path):
    """
    Gửi một file vật lý đến backend Flask để tải lên IPFS.
    Trả về CID.
    """
    try:
        with open(file_path, "rb") as f:
            response = requests.post(f"{FLASK_BACKEND_URL}/upload", files={"file": f})
        
        response.raise_for_status()
        cid = response.json()["cid"]
        print(f"Tải file qua backend Flask thành công! CID: {cid}")
        return cid
        
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi backend Flask: {e}")
        raise Exception(f"Không thể tải file lên IPFS qua backend: {e}")