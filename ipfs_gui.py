import sys, requests, webbrowser
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QLineEdit, QTextEdit, QTabWidget
)

# Change these to your backend device IP
BACKEND = "http://192.168.0.140:8000"
GATEWAY = "http://192.168.0.140:8080/ipfs"

# ──────────────────────────────────────────────
# Upload tab
# ──────────────────────────────────────────────
class UploadTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a file to upload to IPFS."))

        self.btn_select = QPushButton("Select File")
        self.btn_select.clicked.connect(self.choose_file)
        layout.addWidget(self.btn_select)

        self.btn_upload = QPushButton("Upload")
        self.btn_upload.clicked.connect(self.upload_file)
        layout.addWidget(self.btn_upload)

        self.cid_box = QLineEdit()
        self.cid_box.setPlaceholderText("CID will appear here")
        self.cid_box.setReadOnly(True)
        layout.addWidget(self.cid_box)

        self.btn_open = QPushButton("Open in Browser")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_browser)
        layout.addWidget(self.btn_open)

        self.file_path = None
        self.setLayout(layout)

    def choose_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Choose file")
        if file:
            self.file_path = file

    def upload_file(self):
        if not self.file_path:
            QMessageBox.warning(self, "No File", "Please choose a file first.")
            return
        try:
            with open(self.file_path, "rb") as f:
                r = requests.post(f"{BACKEND}/upload", files={"file": f})
            if r.status_code == 200:
                cid = r.json()["cid"]
                self.cid_box.setText(cid)
                self.btn_open.setEnabled(True)
                QMessageBox.information(
                    self, "Success",
                    f"Uploaded!\nCID: {cid}\n\nYou can view it at:\n{GATEWAY}/{cid}"
                )
            else:
                QMessageBox.critical(self, "Upload Failed", r.text)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def open_browser(self):
        cid = self.cid_box.text().strip()
        if cid:
            webbrowser.open(f"{GATEWAY}/{cid}")

# ──────────────────────────────────────────────
# View tab
# ──────────────────────────────────────────────
class ViewTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter a CID to view content from IPFS:"))

        self.cid_input = QLineEdit()
        self.cid_input.setPlaceholderText("e.g., QmTzQ...abc")
        layout.addWidget(self.cid_input)

        self.btn_view = QPushButton("Fetch Content")
        self.btn_view.clicked.connect(self.fetch_content)
        layout.addWidget(self.btn_view)

        self.btn_open = QPushButton("Open in Browser")
        self.btn_open.clicked.connect(self.open_browser)
        layout.addWidget(self.btn_open)

        self.content_box = QTextEdit()
        self.content_box.setPlaceholderText("File content (text only) will appear here.")
        self.content_box.setReadOnly(True)
        layout.addWidget(self.content_box)

        self.setLayout(layout)

    def fetch_content(self):
        cid = self.cid_input.text().strip()
        if not cid:
            QMessageBox.warning(self, "Missing", "Please enter a CID.")
            return
        try:
            r = requests.get(f"{BACKEND}/get/{cid}")
            if r.status_code == 200:
                data = r.json()
                if "content" in data:
                    self.content_box.setPlainText(data["content"])
                else:
                    QMessageBox.information(self, "Notice", "This file is not text-based.\nTry 'Open in Browser'.")
            else:
                QMessageBox.critical(self, "Error", r.text)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def open_browser(self):
        cid = self.cid_input.text().strip()
        if cid:
            webbrowser.open(f"{GATEWAY}/{cid}")

# ──────────────────────────────────────────────
# Main window with tabs
# ──────────────────────────────────────────────
class IPFSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPFS Uploader & Viewer")
        self.resize(500, 400)

        tabs = QTabWidget()
        tabs.addTab(UploadTab(), "Upload")
        tabs.addTab(ViewTab(), "View")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = IPFSApp()
    w.show()
    sys.exit(app.exec())
