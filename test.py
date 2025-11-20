from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton,
    QLineEdit, QLabel, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QDialogButtonBox, QHBoxLayout, QFileDialog,
    QFrame, QListWidget, QListWidgetItem, QGridLayout, QGroupBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ape import accounts, project
from mock_blockchain import MockLandRegistry, MockAccount, MockMarketplace
from ipfs_utils import upload_file_to_ipfs, upload_json_to_ipfs

USE_MOCK_DATA = True

if not USE_MOCK_DATA:
    LAND_REGISTRY_ADDRESS = "0x..." 
    MARKETPLACE_ADDRESS = "0x..."

# =============================================================================
# WIDGET TÙY CHỈNH CHO MỖI MỤC TRONG DANH SÁCH ĐẤT
# =============================================================================
class LandListItemWidget(QWidget):
    def __init__(self, land_id, land_data, parent=None):
        super().__init__(parent)
        self.land_id = land_id
        self.land_data = land_data

        # Layout chính: Ngang
        main_layout = QHBoxLayout(self)
        
        # Layout phụ: Dọc, chứa các dòng text
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0) # Xóa khoảng trống thừa

        # Dòng 1: Mã thửa đất (in đậm)
        id_label = QLabel(f"Mã Thửa Đất: #{self.land_id}")
        font = QFont()
        font.setBold(True)
        id_label.setFont(font)

        # Dòng 2: Các thông tin khác
        info_label = QLabel(
            f"Địa chỉ: {self.land_data['land_address']}\n"
            f"Diện tích: {self.land_data['area']} m²"
        )

        text_layout.addWidget(id_label)
        text_layout.addWidget(info_label)

        # Thêm layout text vào layout chính
        main_layout.addLayout(text_layout)

        # Thêm một "lò xo" để đẩy nút "Xem" sang phải
        main_layout.addStretch()

        # Nút "Xem"
        self.view_button = QPushButton("Xem")
        self.view_button.clicked.connect(self.show_details)
        main_layout.addWidget(self.view_button, alignment=Qt.AlignCenter)
        
    def show_details(self):
        # Tạm thời chỉ hiển thị một hộp thoại thông báo
        # Sau này có thể thay bằng một cửa sổ chi tiết phức tạp hơn
        # (ví dụ: cửa sổ cho phép bán hoặc chuyển nhượng)
        detail_text = (
            f"Thông tin chi tiết Thửa Đất #{self.land_id}\n\n"
            f"Chủ sở hữu (CCCD): {self.land_data['owner_cccd']}\n"
            f"Địa chỉ: {self.land_data['land_address']}\n"
            f"Diện tích: {self.land_data['area']} m²\n"
            f"Link PDF: {self.land_data['pdf_uri']}\n"
            f"Link Hình ảnh: {self.land_data['image_uri']}"
        )
        QMessageBox.information(self, f"Chi tiết Đất #{self.land_id}", detail_text)

# =============================================================================
# TAB CỦA USER: ĐẤT CỦA TÔI (MY ACCOUNT)
# =============================================================================
class UserMyAccountTab(QWidget):
    def __init__(self, user_account, land_registry_contract, land_nft_contract):
        super().__init__()
        self.user_account = user_account
        self.land_registry_contract = land_registry_contract
        self.land_nft_contract = land_nft_contract # Có thể cần sau này

        layout = QVBoxLayout(self)

        title = QLabel("Tài sản Bất động sản của bạn")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        self.refresh_button = QPushButton("Làm mới Danh sách")
        self.refresh_button.clicked.connect(self.populate_my_lands)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignRight)

        # Widget danh sách chính
        self.land_list_widget = QListWidget()
        self.land_list_widget.setStyleSheet("QListWidget::item { border: 1px solid #ccc; border-radius: 5px; margin-bottom: 5px; }")
        layout.addWidget(self.land_list_widget)

        self.populate_my_lands()

    def populate_my_lands(self):
        self.land_list_widget.clear()

        try:
            # Lấy danh sách ID đất mà người dùng sở hữu từ LandRegistry
            owned_land_ids = self.land_registry_contract.get_lands_by_owner(self.user_account.address)

            if not owned_land_ids:
                self.land_list_widget.addItem("Bạn chưa sở hữu mảnh đất nào.")
                return

            for land_id in owned_land_ids:
                # Lấy thông tin chi tiết cho từng mảnh đất
                land_data = self.land_registry_contract.get_land(land_id)
                
                # Chỉ hiển thị những mảnh đất đã được duyệt (có NFT)
                if land_data['status'] == 1: # 1 = Approved
                    # Tạo widget tùy chỉnh
                    item_widget = LandListItemWidget(land_id, land_data)
                    
                    # Tạo một mục trong QListWidget
                    list_item = QListWidgetItem(self.land_list_widget)
                    # Đặt kích thước cho mục để vừa với widget tùy chỉnh
                    list_item.setSizeHint(item_widget.sizeHint())
                    
                    # Thêm mục vào danh sách
                    self.land_list_widget.addItem(list_item)
                    # Gắn widget tùy chỉnh vào mục đó
                    self.land_list_widget.setItemWidget(list_item, item_widget)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Blockchain", f"Không thể tải dữ liệu tài sản của bạn: {e}")


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


# =============================================================================
# TAB CỦA ADMIN: DUYỆT ĐĂNG KÝ ĐẤT
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
# TAB CỦA ADMIN: CẤU HÌNH HỆ THỐNG
# =============================================================================
class AdminSystemConfigTab(QWidget):
    def __init__(self, admin_account, marketplace_contract, parent=None):
        super().__init__(parent)
        self.admin_account = admin_account
        self.marketplace_contract = marketplace_contract

        # Layout chính của tab
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # === Khu vực Quản lý Phí ===
        fees_group = QGroupBox("Quản lý Phí Giao dịch")
        fees_layout = QGridLayout(fees_group)

        # --- Dòng Phí Đăng tin (Listing Fee) ---
        fees_layout.addWidget(QLabel("<b>Phí Đăng tin (Listing Fee):</b>"), 0, 0)
        
        self.listing_fee_label = QLabel("<đang tải...>")
        self.listing_fee_label.setStyleSheet("font-style: italic;")
        fees_layout.addWidget(self.listing_fee_label, 0, 1)

        edit_listing_fee_button = QPushButton("Chỉnh sửa")
        edit_listing_fee_button.clicked.connect(self.edit_fees)
        fees_layout.addWidget(edit_listing_fee_button, 0, 2)

        # --- Dòng Phí Hủy (Cancel Penalty) ---
        fees_layout.addWidget(QLabel("<b>Phí Phạt Hủy (Cancel Penalty):</b>"), 1, 0)

        self.cancel_penalty_label = QLabel("<đang tải...>")
        self.cancel_penalty_label.setStyleSheet("font-style: italic;")
        fees_layout.addWidget(self.cancel_penalty_label, 1, 1)

        edit_cancel_fee_button = QPushButton("Chỉnh sửa")
        edit_cancel_fee_button.clicked.connect(self.edit_fees)
        fees_layout.addWidget(edit_cancel_fee_button, 1, 2)
        
        # Căn chỉnh cho cột giá trị và nút
        fees_layout.setColumnStretch(1, 1) # Cho cột giá trị giãn ra

        main_layout.addWidget(fees_group)
        
        # Tải dữ liệu phí ban đầu
        self.load_current_fees()

    def load_current_fees(self):
        """Tải và hiển thị các mức phí hiện tại từ contract."""
        try:
            listing_fee = self.marketplace_contract.listing_fee()
            cancel_penalty = self.marketplace_contract.cancel_penalty()
            
            # Hiển thị giá trị (đơn vị là Wei)
            self.listing_fee_label.setText(f"{listing_fee} Wei")
            self.cancel_penalty_label.setText(f"{cancel_penalty} Wei")
            self.listing_fee_label.setStyleSheet("font-style: normal; font-weight: bold;")
            self.cancel_penalty_label.setStyleSheet("font-style: normal; font-weight: bold;")

        except Exception as e:
            error_message = f"Lỗi: {e}"
            self.listing_fee_label.setText(error_message)
            self.cancel_penalty_label.setText(error_message)
            QMessageBox.critical(self, "Lỗi Blockchain", f"Không thể tải dữ liệu phí: {e}")

    def edit_fees(self):
        """
        Mở một hộp thoại để cho phép Admin nhập cả hai giá trị phí mới.
        """
        # Lấy giá trị hiện tại để hiển thị trong hộp thoại
        current_listing_fee = self.marketplace_contract.listing_fee()
        current_cancel_penalty = self.marketplace_contract.cancel_penalty()

        # Mở hộp thoại cho Phí Đăng tin
        new_listing_fee_str, ok1 = QInputDialog.getText(
            self, 
            "Chỉnh sửa Phí Đăng tin", 
            "Nhập giá trị Phí Đăng tin mới (đơn vị Wei):",
            QLineEdit.Normal,
            str(current_listing_fee)
        )
        
        # Nếu người dùng nhấn OK, tiếp tục hỏi Phí Hủy
        if ok1 and new_listing_fee_str:
            new_cancel_penalty_str, ok2 = QInputDialog.getText(
                self,
                "Chỉnh sửa Phí Phạt Hủy",
                "Nhập giá trị Phí Phạt Hủy mới (đơn vị Wei):",
                QLineEdit.Normal,
                str(current_cancel_penalty)
            )

            # Nếu người dùng nhấn OK ở cả hai hộp thoại
            if ok2 and new_cancel_penalty_str:
                try:
                    # Chuyển đổi sang số nguyên
                    new_listing_fee = int(new_listing_fee_str)
                    new_cancel_penalty = int(new_cancel_penalty_str)
                    
                    # Gửi giao dịch
                    receipt = self.marketplace_contract.set_fees(
                        new_listing_fee,
                        new_cancel_penalty,
                        sender=self.admin_account
                    )
                    
                    tx_hash = getattr(receipt, 'txn_hash', 'N/A')
                    QMessageBox.information(self, "Thành công", f"Đã cập nhật phí thành công!\nTx: {tx_hash}")
                    
                    # Tải lại dữ liệu để hiển thị giá trị mới
                    self.load_current_fees()

                except ValueError:
                    QMessageBox.warning(self, "Dữ liệu không hợp lệ", "Vui lòng chỉ nhập số nguyên.")
                except Exception as e:
                    QMessageBox.critical(self, "Lỗi Giao dịch", f"Cập nhật phí thất bại: {e}")

# =============================================================================
# TAB CÀI ĐẶT CHUNG (LOGOUT)
# =============================================================================
# class SettingsTab(QWidget):
#     # Định nghĩa một tín hiệu tùy chỉnh không có tham số
#     logout_requested = Signal()

#     def __init__(self, current_user_address, parent=None):
#         super().__init__(parent)
        
#         layout = QVBoxLayout(self)
#         layout.setAlignment(Qt.AlignTop) # Căn chỉnh các widget lên trên cùng

#         # Hiển thị thông tin người dùng hiện tại
#         info_group = QWidget()
#         info_layout = QFormLayout(info_group)
        
#         user_label = QLabel("<b>Địa chỉ ví đang đăng nhập:</b>")
#         address_label = QLabel(current_user_address)
#         address_label.setWordWrap(True) # Tự động xuống dòng nếu địa chỉ quá dài
        
#         info_layout.addRow(user_label)
#         info_layout.addRow(address_label)
        
#         # Nút Logout
#         self.logout_button = QPushButton("Đăng xuất (Logout)")
#         self.logout_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
#         self.logout_button.setFixedWidth(150) # Đặt chiều rộng cố định
#         self.logout_button.clicked.connect(self.request_logout)

#         layout.addWidget(info_group)
#         layout.addWidget(self.logout_button)
    
#     def request_logout(self):
#         # Hiển thị hộp thoại xác nhận
#         reply = QMessageBox.question(
#             self,
#             "Xác nhận Đăng xuất",
#             "Bạn có chắc chắn muốn đăng xuất không?",
#             QMessageBox.Yes | QMessageBox.No,
#             QMessageBox.No
#         )
        
#         if reply == QMessageBox.Yes:
#             # Nếu người dùng xác nhận, phát tín hiệu logout_requested
#             print("Logout signal emitted.")
#             self.logout_requested.emit()

class SettingsTab(QWidget):
    # Không cần định nghĩa signal nữa
    # logout_requested = Signal()

    def __init__(self, current_user_address, main_window, parent=None): # Thêm tham số main_window
        super().__init__(parent)
        self.main_window = main_window # Lưu lại tham chiếu đến cửa sổ chính
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        info_group = QWidget()
        info_layout = QFormLayout(info_group)
        
        user_label = QLabel("<b>Địa chỉ ví đang đăng nhập:</b>")
        address_label = QLabel(current_user_address)
        address_label.setWordWrap(True)
        
        info_layout.addRow(user_label)
        info_layout.addRow(address_label)
        
        self.logout_button = QPushButton("Đăng xuất (Logout)")
        self.logout_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.logout_button.setFixedWidth(150)
        # Kết nối nút bấm với một hàm xử lý mới
        self.logout_button.clicked.connect(self.confirm_and_logout)

        layout.addWidget(info_group)
        layout.addWidget(self.logout_button)
    
    def confirm_and_logout(self):
        reply = QMessageBox.question(
            self,
            "Xác nhận Đăng xuất",
            "Bạn có chắc chắn muốn đăng xuất không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # GỌI TRỰC TIẾP HÀM CỦA MAINWINDOW
            print("Logout confirmed. Calling main window's handle_logout...")
            self.main_window.handle_logout()

# =============================================================================
# CỬA SỔ ĐĂNG NHẬP
# =============================================================================
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

# =============================================================================
# CỬA SỔ CHÍNH
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Real Estate Management System")
        self.setGeometry(100, 100, 600, 400)
        
        # Initially, only the login window is shown
        self.login_window = LoginWindow(self)
        self.setCentralWidget(self.login_window)
    
    def show_login_ui(self):
        self.login_window = LoginWindow(self)
        self.setCentralWidget(self.login_window)
        print("Switched back to Login Page")

    def show_admin_ui(self, admin_account):
        self.tabs = QTabWidget()
        marketplace_contract = MockMarketplace(admin_account)
        # Admin Tabs
        self.land_registry_tab = AdminLandRegistryTab(admin_account)
        self.config_tab = AdminSystemConfigTab(admin_account, marketplace_contract)
        self.settings_tab = SettingsTab(admin_account.address, self)
        #self.settings_tab.logout_requested.connect(self.handle_logout)
        

        self.tabs.addTab(self.land_registry_tab, "Land Registration")
        self.tabs.addTab(QWidget(), "Transaction")
        self.tabs.addTab(self.config_tab, "System Config")
        self.tabs.addTab(self.settings_tab, "Setting")
        
        self.setCentralWidget(self.tabs)
    
    def show_customer_ui(self, user_account):
        self.tabs = QTabWidget()
        land_registry_contract = MockLandRegistry()
        land_nft_contract = None


        self.register_tab = UserRegisterLandTab(user_account, land_registry_contract)
        self.my_account_tab = UserMyAccountTab(user_account, land_registry_contract, land_nft_contract)
        self.settings_tab = SettingsTab(user_account.address, self)
        #self.settings_tab.logout_requested.connect(self.handle_logout)
        
        # Customer Tabs
        self.tabs.addTab(QLabel(f"Welcome User: {user_account.address}"), "Sàn Giao Dịch")
        self.tabs.addTab(self.register_tab, "Register Land")
        self.tabs.addTab(QWidget(), "Marketplace")
        self.tabs.addTab(self.my_account_tab, "My Account")
        self.tabs.addTab(self.settings_tab, "Setting")

        self.setCentralWidget(self.tabs)
    def handle_logout(self):
        """
        Hàm xử lý khi nhận được tín hiệu logout.
        Chuyển giao diện về màn hình đăng nhập.
        """
        print("Handling logout...")
        # Xóa tài khoản hiện tại (nếu có logic autosign)
        # Trong trường hợp của Ape, việc này không thực sự cần thiết vì
        # đối tượng account chỉ tồn tại trong bộ nhớ.
        # Nhưng nếu bạn lưu trữ session, đây là nơi để xóa nó.
        
        # Hiển thị lại cửa sổ đăng nhập
        self.show_login_ui()

def main():
    app = QApplication([])
    
    window = MainWindow()
    window.show()
    
    app.exec()

if __name__ == "__main__":
    main()
