import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QFileDialog, QLineEdit, QTextEdit, QMessageBox, QScrollArea
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from io import BytesIO

IPFS_API = "http://127.0.0.1:5001/api/v0"
IPFS_GATEWAY = "http://127.0.0.1:8080/ipfs"

class IPFSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPFS File Manager")
        self.setGeometry(200, 200, 600, 500)
        
        self.layout = QVBoxLayout()
        self.cid_input = QLineEdit()
        self.cid_input.setPlaceholderText("Enter CID to retrieve file...")
        
        self.upload_btn = QPushButton("Upload File to IPFS")
        self.fetch_btn = QPushButton("Fetch File from CID")
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        
        # Display area
        self.viewer = QLabel()
        self.viewer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer.setScaledContents(True)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.viewer)
        
        # Connect actions
        self.upload_btn.clicked.connect(self.upload_file)
        self.fetch_btn.clicked.connect(self.fetch_file)
        
        # Layout
        self.layout.addWidget(self.upload_btn)
        self.layout.addWidget(QLabel("or"))
        self.layout.addWidget(self.cid_input)
        self.layout.addWidget(self.fetch_btn)
        self.layout.addWidget(self.result_label)
        self.layout.addWidget(scroll)
        
        self.setLayout(self.layout)

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not file_path:
            return
        try:
            with open(file_path, "rb") as f:
                response = requests.post(f"{IPFS_API}/add", files={"file": f})
                cid = response.json()["Hash"]
                self.result_label.setText(f"✅ Uploaded successfully!\nCID: {cid}\nGateway: {IPFS_GATEWAY}/{cid}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload file:\n{e}")

    def fetch_file(self):
        cid = self.cid_input.text().strip()
        if not cid:
            QMessageBox.warning(self, "Warning", "Please enter a CID.")
            return
        try:
            response = requests.get(f"{IPFS_GATEWAY}/{cid}")
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
            
            content_type = response.headers.get("Content-Type", "")
            data = response.content
            
            if "image" in content_type:
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                self.viewer.setPixmap(pixmap)
                self.result_label.setText(f"Displaying image from CID: {cid}")
            elif "text" in content_type or data.decode(errors='ignore').isprintable():
                text = data.decode(errors="ignore")
                self.viewer.setText(text)
                self.result_label.setText(f"Showing text from CID: {cid}")
            else:
                self.viewer.setText("(Binary file, cannot preview)")
                self.result_label.setText(f"Downloaded binary from CID: {cid}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch file:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IPFSApp()
    window.show()
    sys.exit(app.exec())
