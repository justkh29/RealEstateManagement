from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton,
    QLineEdit, QLabel, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QDialogButtonBox, QHBoxLayout, QFileDialog
)
from PySide6.QtCore import Qt
from ape import accounts, project
from mock_blockchain import MockLandRegistry, MockAccount, MockMarketplace
from ipfs_utils import upload_file_to_ipfs, upload_json_to_ipfs

USE_MOCK_DATA = True

if not USE_MOCK_DATA:
    LAND_REGISTRY_ADDRESS = "0x..." 
    MARKETPLACE_ADDRESS = "0x..."


# =============================================================================
# TAB CỦA USER: ĐĂNG KÝ ĐẤT MỚI
# =============================================================================
class UserRegisterLandTab(QWidget): # Tạo một class riêng cho tab này
    def __init__(self, user_account, land_registry_contract):
        super().__init__()
        self.user_account = user_account
        self.land_registry_contract = land_registry_contract

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.land_address_input = QLineEdit()
        self.area_input = QLineEdit()
        self.cccd_input = QLineEdit()
        
        # ----- Tích hợp Upload PDF -----
        self.pdf_uri_input = QLineEdit()
        self.pdf_uri_input.setReadOnly(True)
        self.pdf_uri_input.setPlaceholderText("URI của file PDF sẽ hiện ở đây sau khi upload")
        pdf_upload_button = QPushButton("Upload PDF...")
        pdf_upload_button.clicked.connect(self.upload_pdf)
        
        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(self.pdf_uri_input)
        pdf_layout.addWidget(pdf_upload_button)

        # ----- Tích hợp Upload Hình ảnh -----
        self.image_uri_input = QLineEdit()
        self.image_uri_input.setReadOnly(True)
        self.image_uri_input.setPlaceholderText("URI của file ảnh sẽ hiện ở đây sau khi upload")
        image_upload_button = QPushButton("Upload Hình ảnh...")
        image_upload_button.clicked.connect(self.upload_image)

        image_layout = QHBoxLayout()
        image_layout.addWidget(self.image_uri_input)
        image_layout.addWidget(image_upload_button)
        
        # ----- Thêm vào Form -----
        form_layout.addRow("Địa chỉ Đất:", self.land_address_input)
        form_layout.addRow("Diện tích (m2):", self.area_input)
        form_layout.addRow("Số CCCD:", self.cccd_input)
        form_layout.addRow("Giấy tờ (PDF):", pdf_layout)
        form_layout.addRow("Hình ảnh:", image_layout)
        
        self.register_button = QPushButton("Gửi Hồ sơ Đăng ký")
        self.register_button.clicked.connect(self.handle_register)

        layout.addLayout(form_layout)
        layout.addWidget(self.register_button, alignment=Qt.AlignCenter)

    def upload_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file PDF", "", "PDF Files (*.pdf)")
        if file_path:
            try:
                cid = upload_file_to_ipfs(file_path)
                self.pdf_uri_input.setText(f"ipfs://{cid}")
                QMessageBox.information(self, "Thành công", f"Đã tải lên file PDF!\nCID: {cid}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Upload", str(e))

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file Hình ảnh", "", "Image Files (*.png *.jpg *.jpeg)")
        if file_path:
            try:
                cid = upload_file_to_ipfs(file_path)
                self.image_uri_input.setText(f"ipfs://{cid}")
                QMessageBox.information(self, "Thành công", f"Đã tải lên file ảnh!\nCID: {cid}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Upload", str(e))

    def handle_register(self):
        # Lấy dữ liệu từ các ô input
        land_address = self.land_address_input.text()
        area = int(self.area_input.text())
        cccd = self.cccd_input.text()
        pdf_uri = self.pdf_uri_input.text()
        image_uri = self.image_uri_input.text()

        if not all([land_address, area, cccd, pdf_uri, image_uri]):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền đầy đủ tất cả các trường.")
            return

        try:
            receipt = self.land_registry_contract.register_land(
                land_address, area, cccd, pdf_uri, image_uri,
                sender=self.user_account
            )
            QMessageBox.information(self, "Thành công", f"Đã gửi hồ sơ đăng ký thành công!\nTx: {receipt.txn_hash}")
            # Xóa các ô input sau khi thành công
            self.land_address_input.clear()
            # ... clear các ô khác
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Gửi hồ sơ thất bại: {e}")


class LandDetailDialog(QDialog):
    def __init__(self, land_id, land_data, land_owner, land_registry_contract, admin_account, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Chi tiết Hồ sơ Đất #{land_id}")
        self.setMinimumWidth(450)

        self.land_id = land_id
        self.land_data = land_data
        self.land_registry_contract = land_registry_contract
        self.admin_account = admin_account

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Hiển thị thông tin chi tiết
        form_layout.addRow("ID Hồ sơ:", QLabel(str(land_id)))
        form_layout.addRow("Địa chỉ Ví Đăng ký:", QLabel(land_owner))
        form_layout.addRow("Số CCCD:", QLabel(land_data['owner_cccd']))
        form_layout.addRow("Địa chỉ Đất:", QLabel(land_data['land_address']))
        form_layout.addRow("Diện tích (m2):", QLabel(str(land_data['area'])))
        form_layout.addRow("Link PDF:", QLabel(f"<a href='{land_data['pdf_uri']}'>{land_data['pdf_uri']}</a>"))
        form_layout.addRow("Link Hình ảnh:", QLabel(f"<a href='{land_data['image_uri']}'>{land_data['image_uri']}</a>"))

        layout.addLayout(form_layout)

        # Nút Duyệt và Từ chối
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Duyệt Hồ sơ")
        self.button_box.button(QDialogButtonBox.Cancel).setText("Từ chối Hồ sơ")

        self.button_box.accepted.connect(self.handle_approve)
        self.button_box.rejected.connect(self.handle_reject)

        layout.addWidget(self.button_box)

    def handle_approve(self):
        """
        Hàm này giờ sẽ tự động hóa toàn bộ quy trình:
        1. Tạo JSON metadata.
        2. Tải lên IPFS.
        3. Gửi giao dịch blockchain.
        """
        # Bước 1: Tạo đối tượng JSON metadata theo tiêu chuẩn OpenSea
        print("Bắt đầu quy trình duyệt...")
        print(" -> Bước 1: Tạo đối tượng JSON metadata...")
        metadata_json = {
            "name": f"Bất động sản #{self.land_id}",
            "description": f"Đại diện quyền sở hữu kỹ thuật số cho bất động sản tại địa chỉ {self.land_data['land_address']}.",
            "image": self.land_data['image_uri'],  # Link IPFS của hình ảnh
            "attributes": [
                {"trait_type": "Địa chỉ", "value": self.land_data['land_address']},
                {"trait_type": "Diện tích (m2)", "value": self.land_data['area']},
                {"trait_type": "Tài liệu pháp lý", "value": self.land_data['pdf_uri']}
                # Lưu ý: Không bao giờ đưa thông tin nhạy cảm như CCCD vào metadata công khai
            ]
        }
        
        try:
            # Bước 2: Tải JSON lên IPFS thông qua backend Flask để lấy URI
            print(f" -> Bước 2: Đang tải metadata lên IPFS...")
            self.parent().setCursor(Qt.WaitCursor) # Thay đổi con trỏ chuột để báo đang xử lý
            metadata_uri = upload_json_to_ipfs(metadata_json)
            self.parent().unsetCursor() # Trả lại con trỏ chuột
            print(f" -> Tải metadata thành công, URI: {metadata_uri}")

            # Bước 3: Gọi hàm `approve_land` trên smart contract với URI vừa tạo
            print(f" -> Bước 3: Đang gửi giao dịch duyệt hồ sơ #{self.land_id}...")
            receipt = self.land_registry_contract.approve_land(
                self.land_id,
                metadata_uri,
                sender=self.admin_account
            )
            
            tx_hash = getattr(receipt, 'txn_hash', 'N/A')
            QMessageBox.information(self, "Thành công", f"Đã duyệt và mint NFT thành công cho hồ sơ #{self.land_id}.\nTx: {tx_hash}")
            self.accept() # Đóng cửa sổ và báo hiệu thành công
            
        except Exception as e:
            self.parent().unsetCursor() # Đảm bảo trả lại con trỏ chuột nếu có lỗi
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra trong quá trình duyệt hồ sơ:\n{e}")
            self.reject() # Đóng cửa sổ và báo hiệu thất bại

    def handle_reject(self):
        try:
            # Gọi hàm `reject_land`
            receipt = self.land_registry_contract.reject_land(self.land_id, sender=self.admin_account)
            QMessageBox.information(self, "Thành công", f"Đã từ chối hồ sơ #{self.land_id}.\nTx: {receipt.txn_hash}")
            self.accept() # Đóng cửa sổ dialog và báo hiệu thành công
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra khi từ chối hồ sơ: {e}")
            self.reject()


# =============================================================================
# TAB CHÍNH: DUYỆT ĐĂNG KÝ ĐẤT
# =============================================================================
class AdminLandRegistryTab(QWidget):
    def __init__(self, admin_account):
        super().__init__()
        
        self.admin_account = admin_account
        self.land_registry_contract = MockLandRegistry()
        ##self.land_registry_contract = project.LandRegistry.at(LAND_REGISTRY_ADDRESS)

        # Main layout
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Quản lý Hồ sơ Đăng ký Đất")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Refresh button
        self.refresh_button = QPushButton("Làm mới Danh sách")
        self.refresh_button.clicked.connect(self.populate_pending_lands)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignRight)

        # Table to display pending lands
        self.pending_lands_table = QTableWidget()
        self.pending_lands_table.setColumnCount(5)
        self.pending_lands_table.setHorizontalHeaderLabels(["ID", "Ví Đăng ký", "CCCD", "Địa chỉ Đất", "Hành động"])
        self.pending_lands_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pending_lands_table.setEditTriggers(QTableWidget.NoEditTriggers) # Read-only
        layout.addWidget(self.pending_lands_table)
        
        # Load data initially
        self.populate_pending_lands()

    def populate_pending_lands(self):
        """Lấy dữ liệu từ blockchain và điền vào bảng"""
        try:
            self.pending_lands_table.setRowCount(0) # Xóa dữ liệu cũ
            
            next_id = self.land_registry_contract.next_land_id()
            
            pending_requests = []
            # Lặp qua tất cả các land_id đã được tạo
            for i in range(1, next_id):
                status = self.land_registry_contract.is_land_pending(i)
                if status:
                    pending_requests.append(i)

            self.pending_lands_table.setRowCount(len(pending_requests))

            for row, land_id in enumerate(pending_requests):
                land_data = self.land_registry_contract.get_land(land_id)
                land_owner = self.land_registry_contract.get_land_owner(land_id)

                self.pending_lands_table.setItem(row, 0, QTableWidgetItem(str(land_id)))
                self.pending_lands_table.setItem(row, 1, QTableWidgetItem(land_owner))
                self.pending_lands_table.setItem(row, 2, QTableWidgetItem(land_data['owner_cccd']))
                self.pending_lands_table.setItem(row, 3, QTableWidgetItem(land_data['land_address']))

                # Tạo nút "Xem & Xử lý" cho mỗi hàng
                process_button = QPushButton("Xem & Xử lý")
                # Dùng lambda để truyền đúng land_id vào hàm khi nút được nhấn
                process_button.clicked.connect(lambda checked, lid=land_id: self.show_detail_dialog(lid))
                self.pending_lands_table.setCellWidget(row, 4, process_button)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Blockchain", f"Không thể tải dữ liệu từ contract: {e}")

    def show_detail_dialog(self, land_id):
        """Hiển thị cửa sổ chi tiết khi nút được nhấn"""
        try:
            land_data = self.land_registry_contract.get_land(land_id)
            land_owner = self.land_registry_contract.get_land_owner(land_id)

            dialog = LandDetailDialog(land_id, land_data, land_owner, self.land_registry_contract, self.admin_account, self)
            
            # Nếu dialog được chấp nhận (approve/reject thành công), làm mới bảng
            if dialog.exec():
                self.populate_pending_lands()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lấy chi tiết hồ sơ: {e}")




class LoginWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 300, 200)

        # Main layout (to center the form)
        main_layout = QVBoxLayout()
        
        # Title
        title = QLabel("Login")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(title)

        # Create form layout
        form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.address_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Account Address:", self.address_input)
        form_layout.addRow("Password:", self.password_input)

        # Add the form to the main layout
        main_layout.addLayout(form_layout)

        # Login button
        self.login_button = QPushButton("Login")
        main_layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        self.login_button.clicked.connect(self.handle_login)

        self.setLayout(main_layout)


    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        # You can replace this with your actual login logic
        if username == "mock_admin":
            admin_address = "0xdeADBEeF00000000000000000000000000000000"
            mock_admin_account = MockAccount(admin_address)
            self.main_window.show_admin_ui(mock_admin_account)
        elif username == "mock_user":
            user_address = "0x1234567890123456789012345678901234567890"
            mock_user_account = MockAccount(user_address)
            self.main_window.show_customer_ui(mock_user_account)
        else:
            QMessageBox.warning(self, "Đăng nhập thất bại", "Username phải là 'mock_admin' hoặc 'mock_user'.")
        return

    # def handle_login(self):
    #     username = self.username_input.text()
    #     password = self.password_input.text()
    #     address  = self.address_input.text()


    #     # 1. Try loading + unlocking the user account
    #     try:
    #         voter = accounts.load(username)
    #         voter.set_autosign(True, passphrase=password)
    #     except Exception as e:
    #         print(f"Invalid username or password: {e}")
    #         return

    #     # 2. Load your deployed contract
    #     contract = project.YourContractName.at("0xYOUR_DEPLOYED_CONTRACT")

    #     # 3. Get admin address from the chain
    #     admin_address = contract.admin()

    #     # 4. Compare the user's entered address to the admin address
    #     if address.lower() == admin_address.lower():
    #         # Admin login
    #         self.parent().show_admin_tabs()
    #     else:
    #         # Customer login
    #         self.parent().show_customer_tabs()

    #     self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Real Estate Management System")
        self.setGeometry(100, 100, 600, 400)
        
        # Initially, only the login window is shown
        self.login_window = LoginWindow(self)
        self.setCentralWidget(self.login_window)
    
    def show_admin_ui(self, admin_account):
        self.tabs = QTabWidget()
        
        # Admin Tabs
        self.land_registry_tab = AdminLandRegistryTab(admin_account)
        self.tabs.addTab(self.land_registry_tab, "Land Registration")
        self.tabs.addTab(QWidget(), "Transaction")
        self.tabs.addTab(QWidget(), "System Config")
        self.tabs.addTab(QWidget(), "Setting")
        
        self.setCentralWidget(self.tabs)
    
    def show_customer_ui(self, user_account):
        self.tabs = QTabWidget()
        land_registry_contract = MockLandRegistry()
        self.register_tab = UserRegisterLandTab(user_account, land_registry_contract)
        # Customer Tabs
        self.tabs.addTab(QLabel(f"Welcome User: {user_account.address}"), "Sàn Giao Dịch")
        
        self.tabs.addTab(self.register_tab, "Register Land")
        self.tabs.addTab(QWidget(), "Marketplace")
        self.tabs.addTab(QWidget(), "My Account")
        self.tabs.addTab(QWidget(), "Setting")

        self.setCentralWidget(self.tabs)


def main():
    app = QApplication([])
    
    window = MainWindow()
    window.show()
    
    app.exec()

if __name__ == "__main__":
    main()
