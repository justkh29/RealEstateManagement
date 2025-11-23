# file: backend_ipfs.py (cập nhật)

from flask import Flask, request, jsonify, send_file
import requests
import json # Thêm import này
import io
app = Flask(__name__)

IPFS_API = "http://192.168.43.167:5001/api/v0"

# Endpoint tải file (giữ nguyên)
@app.route("/upload", methods=["POST"])
def upload_file():
    # ... (code của bạn giữ nguyên) ...
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    try:
        files = {"file": (file.filename, file.stream)}
        res = requests.post(f"{IPFS_API}/add", files=files)
        data = res.json()
        cid = data["Hash"]
        requests.post(f"{IPFS_API}/pin/add?arg={cid}")
        return jsonify({"cid": cid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoint tải JSON (MỚI)
@app.route("/upload_json", methods=["POST"])
def upload_json():
    # Nhận dữ liệu JSON từ request body
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    try:
        # IPFS API cần dữ liệu ở định dạng multipart/form-data
        # Chúng ta sẽ lưu JSON vào một file tạm trong bộ nhớ
        files = {"file": ("metadata.json", json.dumps(json_data))}
        
        # Gọi endpoint /add
        res = requests.post(f"{IPFS_API}/add", files=files)
        data = res.json()
        cid = data["Hash"]

        # Pin file để nó không bị xóa
        requests.post(f"{IPFS_API}/pin/add?arg={cid}")

        return jsonify({"cid": cid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Endpoint xem file (giữ nguyên)
@app.route("/get/<cid>")
def get_file(cid):
    # ... (code của bạn giữ nguyên) ...
    try:
        res = requests.post(f"{IPFS_API}/cat?arg={cid}")
        content = res.text
        return jsonify({"cid": cid, "content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === ENDPOINT MỚI ĐỂ LẤY DỮ LIỆU ẢNH ===
@app.route("/image/<cid>")
def get_image(cid):
    """
    Lấy dữ liệu ảnh từ IPFS và trả về dưới dạng file ảnh.
    Trình duyệt hoặc client có thể hiển thị trực tiếp.
    """
    try:
        # Dùng `cat` để lấy nội dung file từ IPFS
        res = requests.post(f"{IPFS_API}/cat?arg={cid}", timeout=10)
        res.raise_for_status()
        
        # Dữ liệu trả về là dữ liệu nhị phân (bytes) của ảnh
        image_data = res.content
        
        # Dùng io.BytesIO để tạo một "file" trong bộ nhớ
        # và send_file để trả về với đúng content-type (vd: image/jpeg)
        return send_file(
            io.BytesIO(image_data),
            mimetype='image/jpeg' # Bạn có thể làm nó thông minh hơn để tự phát hiện mimetype
        )
    except Exception as e:
        print(f"Error fetching image {cid}: {e}")
        # Trả về lỗi 404 nếu không tìm thấy
        return jsonify({"error": str(e)}), 404


if __name__ == "__main__":
    # Đảm bảo chạy backend này trước khi chạy GUI
    app.run(host="192.168.43.167", port=8000) # Host 0.0.0.0 để có thể truy cập từ máy khác trong cùng mạng