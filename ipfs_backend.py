from flask import Flask, request, jsonify, send_file
import requests
import json
import io

app = Flask(__name__)

# CẤU HÌNH IP
IPFS_HOST = "192.168.0.160"
IPFS_API_PORT = "5001"
IPFS_API_URL = f"http://{IPFS_HOST}:{IPFS_API_PORT}/api/v0"

# ================= UPLOAD =================

@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload file bất kỳ (PDF, Image, JSON file)"""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        # Gửi file lên IPFS
        files = {"file": (file.filename, file.stream)}
        res = requests.post(f"{IPFS_API_URL}/add", files=files)
        data = res.json()
        cid = data["Hash"]
        
        # Pin file
        requests.post(f"{IPFS_API_URL}/pin/add?arg={cid}")
        
        return jsonify({"cid": cid, "filename": file.filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload_json", methods=["POST"])
def upload_json():
    """Upload dữ liệu raw JSON từ client"""
    json_data = request.get_json()
    if not json_data:
        return jsonify({"error": "No JSON data provided"}), 400
    
    try:
        # Chuyển dict thành string json rồi gửi như một file
        files = {"file": ("data.json", json.dumps(json_data))}
        
        res = requests.post(f"{IPFS_API_URL}/add", files=files)
        data = res.json()
        cid = data["Hash"]

        requests.post(f"{IPFS_API_URL}/pin/add?arg={cid}")

        return jsonify({"cid": cid, "type": "json"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================= VIEW (Hàm quan trọng đã sửa) =================

def detect_mimetype(content_bytes):
    """
    Hàm phụ trợ đơn giản để đoán loại file dựa trên nội dung (Magic Numbers).
    IPFS cat không trả về filename extension nên ta phải đoán.
    """
    # Chuyển vài byte đầu để kiểm tra
    head = content_bytes[:10]
    
    if head.startswith(b'%PDF'):
        return 'application/pdf'
    elif head.startswith(b'\x89PNG'):
        return 'image/png'
    elif head.startswith(b'\xff\xd8'):
        return 'image/jpeg'
    elif head.startswith(b'{') or head.startswith(b'['):
        # Rất có thể là JSON
        return 'application/json'
    
    # Mặc định trả về octet-stream (tải về) nếu không nhận diện được
    return 'application/octet-stream'

@app.route("/view/<cid>")
def view_file(cid):
    """
    Endpoint duy nhất để xem PDF, Image, và JSON.
    Tự động trả về đúng Content-Type.
    """
    try:
        # Lấy dữ liệu từ IPFS (timeout để tránh treo nếu file quá lớn/mạng lag)
        res = requests.post(f"{IPFS_API_URL}/cat?arg={cid}", timeout=20)
        res.raise_for_status()
        
        file_content = res.content # Dạng bytes
        
        # Tự động phát hiện loại file
        mime_type = detect_mimetype(file_content)
        
        # Nếu là JSON, ta có thể muốn trả về dạng pretty print hoặc để trình duyệt render
        # Ở đây dùng send_file để đồng nhất cách xử lý
        return send_file(
            io.BytesIO(file_content),
            mimetype=mime_type,
            as_attachment=False, # False = Xem trên trình duyệt, True = Tải về
            download_name=f"{cid}.{mime_type.split('/')[-1]}" # Đặt tên file ảo
        )

    except Exception as e:
        print(f"Error fetching {cid}: {e}")
        return jsonify({"error": "File not found or IPFS error", "details": str(e)}), 404

if __name__ == "__main__":
    # Chạy host 0.0.0.0 để các máy khác trong mạng LAN truy cập được
    app.run(host=IPFS_HOST, port=8000, debug=True)