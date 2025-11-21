import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton,
    QLineEdit, QLabel, QFormLayout, QTableWidget, QTableWidgetItem, QScrollArea,
    QHeaderView, QMessageBox, QDialog, QDialogButtonBox, QHBoxLayout, QFileDialog,
    QFrame, QListWidget, QListWidgetItem, QGridLayout, QGroupBox, QInputDialog, QStackedWidget
)
from PySide6.QtCore import QObject, QThread, Qt, Signal, QRegularExpression, QUrl, Slot
from PySide6.QtGui import QFont, QRegularExpressionValidator, QDesktopServices, QPixmap
from ape import accounts, project
from mock_blockchain import (
    MockAccount, MockLandRegistry, MockLandNFT, MockMarketplace,
    MOCK_ADMIN_ADDRESS, MOCK_USER_A_ADDRESS, MOCK_USER_B_ADDRESS
)
from ipfs_utils import upload_file_to_ipfs, upload_json_to_ipfs, FLASK_BACKEND_URL


from dataclasses import dataclass

USE_MOCK_DATA = True

if not USE_MOCK_DATA:
    LAND_REGISTRY_ADDRESS = "0x..." 
    MARKETPLACE_ADDRESS = "0x..."
# =============================================================================
# CÁC LỚP DỮ LIỆU (DATA CLASSES)
# Định nghĩa cấu trúc dữ liệu sạch mà GUI sẽ sử dụng.
# =============================================================================

@dataclass
class LandParcelData:
    """
    Lớp này đại diện cho dữ liệu của một 'LandParcel' sau khi đã được xử lý.
    Thứ tự các trường phải khớp chính xác với thứ tự trong struct của Vyper.
    """
    id: int
    land_address: str
    area: int
    owner_cccd: str
    status: int
    pdf_uri: str
    image_uri: str

@dataclass
class ListingData:
    """
    Lớp này đại diện cho dữ liệu của một 'Listing' sau khi đã được xử lý.
    Thứ tự các trường phải khớp chính xác với thứ tự trong struct của Vyper.
    """
    listing_id: int
    token_id: int
    seller_cccd: str
    price: int
    status: int
    created_at: int

# =============================================================================
# CÁC HÀM CHUYỂN ĐỔI (PARSERS / ADAPTERS)
# Chịu trách nhiệm "dịch" dữ liệu thô từ blockchain (Tuple) sang Data Class.
# =============================================================================

def parse_land_parcel_tuple(data_tuple: tuple) -> LandParcelData:
    """
    Chuyển đổi một tuple trả về từ contract.land_parcels() thành một đối tượng LandParcelData.
    """
    # Kiểm tra an toàn: nếu tuple không hợp lệ, trả về một đối tượng rỗng
    if not isinstance(data_tuple, tuple) or len(data_tuple) != 7:
        print(f"Cảnh báo: Dữ liệu LandParcel không hợp lệ: {data_tuple}")
        return LandParcelData(id=0, land_address="", area=0, owner_cccd="", status=99, pdf_uri="", image_uri="")
    
    # Kỹ thuật "unpacking": `*data_tuple` sẽ tự động điền các phần tử của tuple
    # vào các tham số của constructor LandParcelData theo đúng thứ tự.
    return LandParcelData(*data_tuple)


def parse_listing_tuple(data_tuple: tuple) -> ListingData:
    """
    Chuyển đổi một tuple trả về từ contract.listings() thành một đối tượng ListingData.
    """
    if not isinstance(data_tuple, tuple) or len(data_tuple) != 6:
        print(f"Cảnh báo: Dữ liệu Listing không hợp lệ: {data_tuple}")
        return ListingData(listing_id=0, token_id=0, seller_cccd="", price=0, status=99, created_at=0)
    
    return ListingData(*data_tuple)

# =============================================================================
# WORKER TẢI ẢNH (GỌI QUA BACKEND FLASK)
# =============================================================================
class ImageDownloader(QObject):
    finished = Signal(QPixmap)
    error = Signal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            # URL bây giờ là một endpoint của Flask, vd: http://.../image/Qm...
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            
            if pixmap.isNull():
                self.error.emit(f"Không thể tải dữ liệu ảnh từ URL: {self.url}")
            else:
                self.finished.emit(pixmap)
        except Exception as e:
            self.error.emit(f"Lỗi khi tải ảnh qua backend: {e}")

# =============================================================================
# WIDGET TÙY CHỈNH CHO MỖI MỤC TRONG DANH SÁCH ĐẤT
# =============================================================================
class LandListItemWidget(QWidget): # SỬA LỖI #1
    sell_requested = Signal(int)

    def __init__(self, land_data: LandParcelData, parent=None):
        super().__init__(parent)
        self.land_data = land_data

        main_layout = QHBoxLayout(self)
        text_layout = QVBoxLayout()
        # ...
        id_label = QLabel(f"<b>Mã Thửa Đất: #{self.land_data.id}</b>")
        
        # SỬA: Dùng `land_data.attribute`
        info_label = QLabel(
            f"Địa chỉ: {self.land_data.land_address}\n"
            f"Diện tích: {self.land_data.area} m²"
        )
        # ...
        text_layout.addWidget(id_label)
        text_layout.addWidget(info_label)
        main_layout.addLayout(text_layout)
        main_layout.addStretch()

        self.sell_button = QPushButton("Bán")
        self.sell_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.sell_button.clicked.connect(lambda: self.sell_requested.emit(self.land_data.id))
        
        self.view_button = QPushButton("Xem Chi tiết")
        self.view_button.clicked.connect(self.show_details)
        
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.sell_button)
        button_layout.addWidget(self.view_button)
        main_layout.addLayout(button_layout)

    def show_details(self):
        # SỬA: Dùng `land_data.attribute`
        detail_text = (
            f"Thông tin chi tiết Thửa Đất #{self.land_data.id}\n\n"
            f"Chủ sở hữu (CCCD): {self.land_data.owner_cccd}\n"
            f"Địa chỉ: {self.land_data.land_address}\n"
            f"Diện tích: {self.land_data.area} m²\n"
            f"Link PDF: {self.land_data.pdf_uri}\n"
            f"Link Hình ảnh: {self.land_data.image_uri}"
        )
        QMessageBox.information(self, f"Chi tiết Đất #{self.land_data.id}", detail_text)
# =============================================================================
# WIDGET THẺ HIỂN THỊ ĐẤT (TÓM TẮT)
# =============================================================================
class ListingCardWidget(QFrame):
    # Dùng signal để báo cho tab cha biết người dùng muốn xem chi tiết
    view_details_requested = Signal(int, str) # int là listing_id, str là địa chỉ

    def __init__(self, listing_data: ListingData, land_data: LandParcelData, seller_address, parent=None):
        super().__init__(parent)
        self.listing_id = listing_data.listing_id
        self.seller_address = seller_address

        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedWidth(250)
        layout = QVBoxLayout(self)
        
        
        self.image_label = QLabel(f"[Hình ảnh Đất #{listing_data.token_id}]")
        self.image_label.setFixedSize(230, 120)
        self.image_label.setStyleSheet("background-color: #eee; border: 1px solid #ccc;")
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)
        self.load_image(land_data.image_uri)
        
        layout.addWidget(QLabel(f"<b>{land_data.land_address}</b>"))
        layout.addWidget(QLabel(f"Diện tích: {land_data.area} m²"))
        price_in_eth = listing_data.price / 10**18
        layout.addWidget(QLabel(f"<b style='color: #d32f2f; font-size: 16px;'>{price_in_eth:.4f} ETH</b>"))
        
        view_button = QPushButton("Xem Chi tiết & Mua")
        view_button.clicked.connect(lambda: self.view_details_requested.emit(self.listing_id, self.seller_address))
        layout.addWidget(view_button)

    def load_image(self, image_ipfs_uri):
        if not image_ipfs_uri or not image_ipfs_uri.startswith("ipfs://"):
            self.handle_image_error("URI hình ảnh không hợp lệ.")
            return

        # === THAY ĐỔI CHÍNH Ở ĐÂY ===
        # Lấy CID từ URI
        cid = image_ipfs_uri.replace("ipfs://", "")
        
        # Tạo URL để gọi đến backend Flask
        backend_image_url = f"{FLASK_BACKEND_URL}/image/{cid}"
        # ============================
        
        # Phần code tạo luồng và worker còn lại giữ nguyên
        self.thread = QThread()
        self.worker = ImageDownloader(backend_image_url) # Truyền URL của backend vào worker
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.set_image)
        self.worker.error.connect(self.handle_image_error)
        self.worker.finished.connect(self.thread.quit)
        # ... (các kết nối dọn dẹp khác) ...
        self.thread.start()
    
    def set_image(self, pixmap):
        """Slot này được gọi khi ảnh đã được tải xong."""
        # Co dãn ảnh để vừa với QLabel mà không làm méo ảnh
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def handle_image_error(self, error_message):
        """Slot này được gọi khi có lỗi xảy ra."""
        print(f"Lỗi tải ảnh cho listing #{self.listing_id}: {error_message}")
        self.image_label.setText("[Lỗi tải ảnh]")

# =============================================================================
# CỬA SỔ CHI TIẾT VÀ MUA BÁN
# =============================================================================
class ListingDetailDialog(QDialog):
    def __init__(self, user_account, listing_id, listing_data, land_data, seller_address, marketplace_contract, parent=None):
        super().__init__(parent)
        self.user_account = user_account
        self.listing_data = listing_data
        self.marketplace_contract = marketplace_contract
        
        self.setWindowTitle(f"Chi tiết Bất động sản #{listing_data.token_id}")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        price_in_eth = listing_data.price / 10**18
        
        form_layout.addRow("<b>Địa chỉ:</b>", QLabel(land_data.land_address))
        form_layout.addRow("<b>Diện tích:</b>", QLabel(f"{land_data.area} m²"))
        form_layout.addRow("<b>Giá bán:</b>", QLabel(f"{price_in_eth:.4f} ETH ({listing_data.price} Wei)"))
        
        seller_label = QLabel(seller_address)
        seller_label.setWordWrap(True)
        form_layout.addRow("<b>Người bán:</b>", seller_label)

        pdf_button = QPushButton("Xem Giấy tờ pháp lý (PDF)")
        pdf_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(land_data.pdf_uri.replace("ipfs://", "http://127.0.0.1:8080/ipfs/"))))
        form_layout.addRow(pdf_button)
        
        layout.addLayout(form_layout)
        
        # Ô nhập CCCD người mua
        self.cccd_input = QLineEdit()
        self.cccd_input.setPlaceholderText("Nhập số CCCD của bạn để tiếp tục")
        layout.addWidget(QLabel("<b>CCCD của Người mua (*):</b>"))
        layout.addWidget(self.cccd_input)
        
        # Nút Mua
        self.buy_button = QPushButton(f"Mua Ngay với giá {price_in_eth:.4f} ETH")
        self.buy_button.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; padding: 10px;")
        if seller_address.lower() == self.user_account.address.lower():
            self.buy_button.setText("Đây là tài sản của bạn")
            self.buy_button.setEnabled(False)
            self.cccd_input.setEnabled(False)
        else:
            self.buy_button.setText(f"Mua Ngay với giá {price_in_eth:.4f} ETH")
            self.buy_button.clicked.connect(self.handle_buy)
        layout.addWidget(self.buy_button)

    def handle_buy(self):
        buyer_cccd = self.cccd_input.text().strip()
        if not buyer_cccd:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập số CCCD của bạn.")
            return

        price_wei = self.listing_data.price
        
        reply = QMessageBox.question(
            self, "Xác nhận Mua",
            f"Bạn có chắc chắn muốn mua bất động sản này với giá {price_wei} Wei không?\n"
            "Số tiền sẽ được ký quỹ cho đến khi Admin duyệt giao dịch.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        try:
            receipt = self.marketplace_contract.initiate_transaction(
                self.listing_data.listing_id,
                buyer_cccd,
                sender=self.user_account,
                value=price_wei
            )
            QMessageBox.information(self, "Thành công", f"Đã gửi yêu cầu mua thành công!\nGiao dịch của bạn đang chờ Admin duyệt.\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
            self.accept() # Đóng cửa sổ
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Giao dịch", f"Gửi yêu cầu mua thất bại: {e}")

class MarketplaceTab(QWidget):
    def __init__(self, user_account, marketplace_contract, land_registry_contract, land_nft_contract):
        super().__init__()
        self.user_account = user_account
        self.marketplace_contract = marketplace_contract
        self.land_registry_contract = land_registry_contract
        self.land_nft_contract = land_nft_contract

        main_layout = QHBoxLayout(self)

        # Cột Lọc (tạm thời để trống)
        filter_panel = QFrame()
        filter_panel.setFrameShape(QFrame.StyledPanel)
        filter_panel.setFixedWidth(200)
        filter_layout = QVBoxLayout(filter_panel)
        filter_layout.addWidget(QLabel("<b>Bộ lọc (sắp có)</b>"))
        main_layout.addWidget(filter_panel)
        
        # Cột Danh sách
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setAlignment(Qt.AlignTop)
        scroll_area.setWidget(grid_container)
        main_layout.addWidget(scroll_area)

        self.load_listings()

    def load_listings(self):
        # Xóa các widget cũ
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        try:
            # Truy cập `next_listing_id` như một thuộc tính
            next_id = self.marketplace_contract.next_listing_id
            
            row, col = 0, 0
            for i in range(1, next_id):
                listing_tuple = self.marketplace_contract.listings(i)
                listing_data = parse_listing_tuple(listing_tuple)
                
                if listing_data and listing_data.listing_id != 0 and listing_data.status == 0:
                    token_id = listing_data.token_id
                    seller_address = self.land_nft_contract.ownerOf(token_id)
                    
                    if seller_address.lower() == self.user_account.address.lower():
                        continue 

                    land_tuple = self.land_registry_contract.land_parcels(token_id)
                    land_data = parse_land_parcel_tuple(land_tuple)
                    
                    if land_data and land_data.id != 0:
                        # Truyền các đối tượng dataclass đã được parse
                        card = ListingCardWidget(listing_data, land_data, seller_address)
                        card.view_details_requested.connect(self.handle_view_details)
                        self.grid_layout.addWidget(card, row, col)
                    col += 1
                    if col >= 3:
                        col = 0
                        row += 1
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách niêm yết: {e}")

    @Slot(int, str)
    def handle_view_details(self, listing_id, seller_address):
        try:
            listing_tuple = self.marketplace_contract.listings(listing_id)
            listing_data = parse_listing_tuple(listing_tuple)

            land_tuple = self.land_registry_contract.land_parcels(listing_data.token_id)
            land_data = parse_land_parcel_tuple(land_tuple)
            
            if listing_data and land_data:
                dialog = ListingDetailDialog(
                    self.user_account, listing_id, listing_data, land_data, seller_address, 
                    self.marketplace_contract, self
                )
                if dialog.exec():
                    self.load_listings()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể hiển thị chi tiết: {e}")

# =============================================================================
# TAB CỦA USER: ĐẤT CỦA TÔI (MY ACCOUNT)
# =============================================================================
class MyAccountTab(QWidget):
    def __init__(self, user_account, land_registry_contract, land_nft_contract, marketplace_contract):
        super().__init__()
        self.user_account = user_account
        self.land_registry_contract = land_registry_contract
        self.land_nft_contract = land_nft_contract # Có thể cần sau này
        self.marketplace_contract = marketplace_contract
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
            owned_land_ids = self.land_registry_contract.owner_to_lands(self.user_account.address)

            if not owned_land_ids:
                self.land_list_widget.addItem("Bạn chưa sở hữu mảnh đất nào.")
                return

            for land_id in owned_land_ids:
                # Lấy thông tin chi tiết cho từng mảnh đất
                land_tuple = self.land_registry_contract.land_parcels(land_id)
                land_data = parse_land_parcel_tuple(land_tuple)
                
                if land_data and land_data.status == 1:
                    # Truyền đối tượng dataclass vào widget
                    item_widget = LandListItemWidget(land_data)
                    
                    item_widget.sell_requested.connect(self.handle_sell_request)
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
    def handle_sell_request(self, token_id):
        """Hàm xử lý đầy đủ luồng đăng bán, tự động lấy CCCD."""
        print(f"Bắt đầu quy trình bán cho token #{token_id}")
        
        try:
            # === BƯỚC 1: KIỂM TRA PHÊ DUYỆT (APPROVAL) ===
            print(" -> Bước 1: Kiểm tra quyền (approval)...")
            is_approved = self.land_nft_contract.isApprovedForAll(
                self.user_account.address,
                self.marketplace_contract.address
            )
            
            if not is_approved:
                reply = QMessageBox.question(
                    self,
                    "Yêu cầu Phê duyệt",
                    "Bạn cần cấp quyền cho Sàn giao dịch để quản lý NFT của bạn trước khi có thể đăng bán. "
                    "Bạn có muốn tiếp tục không?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return # Người dùng từ chối
                
                approval_receipt = self.land_nft_contract.setApprovalForAll(
                    self.marketplace_contract.address, True, sender=self.user_account
                )
                QMessageBox.information(self, "Phê duyệt Thành công", f"Đã cấp quyền thành công!\nTx: {getattr(approval_receipt, 'txn_hash', 'N/A')}\n\nBây giờ bạn có thể nhấn 'Bán' lại.")
                return # Dừng lại để người dùng nhấn bán lại, đảm bảo luồng rõ ràng

            # === BƯỚC 2: CHỈ HỎI GIÁ BÁN ===
            print(" -> Bước 2: Mở dialog để lấy giá bán...")
            dialog = SellDialog(token_id, self)
            if dialog.exec(): # Trả về True nếu người dùng nhấn OK
                price = dialog.get_price()
                
                if price is None:
                    QMessageBox.warning(self, "Thông tin không hợp lệ", "Vui lòng nhập giá bán hợp lệ.")
                    return
                
                # === BƯỚC 2.5: TỰ ĐỘNG LẤY CCCD TỪ LANDREGISTRY ===
                print(" -> Lấy CCCD từ LandRegistry...")
                land_tuple = self.land_registry_contract.land_parcels(token_id)
                land_parcel_data = parse_land_parcel_tuple(land_tuple)
                
                if not land_parcel_data:
                    QMessageBox.critical(self, "Lỗi Dữ liệu", "Không tìm thấy dữ liệu cho mảnh đất này.")
                    return
                    
                seller_cccd = land_parcel_data.owner_cccd
                
                if not seller_cccd:
                    QMessageBox.critical(self, "Lỗi Dữ liệu", "Không tìm thấy thông tin CCCD cho mảnh đất này trong Registry.")
                    return

                # === BƯỚC 3: GỬI GIAO DỊCH CREATE_LISTING ===
                print(f" -> Bước 3: Gửi giao dịch create_listing với CCCD tự động: {seller_cccd}")
                listing_fee = self.marketplace_contract.listing_fee()
                
                receipt = self.marketplace_contract.create_listing(
                    token_id,
                    seller_cccd, # Dùng CCCD vừa lấy được từ Registry
                    price,
                    sender=self.user_account,
                    value=listing_fee
                )
                
                QMessageBox.information(self, "Thành công", f"Đã đăng bán bất động sản #{token_id} thành công!\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
                # Làm mới danh sách để cập nhật trạng thái (ví dụ: hiển thị "Đang bán")
                self.populate_my_lands() 
            else:
                print(" -> Người dùng đã hủy đăng bán.")

        except Exception as e:
            self.unsetCursor() # Đảm bảo con trỏ chuột được trả lại nếu có lỗi
            QMessageBox.critical(self, "Lỗi", f"Một lỗi đã xảy ra: {e}")

class SellDialog(QDialog):
    def __init__(self, token_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Đăng bán Bất động sản #{token_id}")
        
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Nhập giá bán bằng số (đơn vị Wei)")
        
        regex = QRegularExpression("[0-9]+")
        validator = QRegularExpressionValidator(regex, self)
        self.price_input.setValidator(validator)
        # ============================

        self.form_layout.addRow("<b>Giá bán (Wei) (*):</b>", self.price_input)
        self.layout.addLayout(self.form_layout)

        # Nút OK và Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_price(self):
        """Chỉ trả về giá trị giá bán đã được nhập."""
        price_str = self.price_input.text().strip()
        if price_str:
            try:
                return int(price_str)
            except ValueError:
                return None
        return None


# =============================================================================
# TAB CỦA USER: ĐĂNG KÝ ĐẤT MỚI
# =============================================================================
class RegisterLandTab(QWidget): # Tạo một class riêng cho tab này
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

        layout.addStretch(1) 

    def _clear_form(self):
        """Hàm trợ giúp để xóa trắng tất cả các ô input."""
        self.land_address_input.clear()
        self.area_input.clear()
        self.cccd_input.clear()
        self.pdf_uri_input.clear()
        self.image_uri_input.clear()
        print("Registration form has been cleared.")

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
            QMessageBox.information(self, "Thành công", f"Đã gửi hồ sơ đăng ký thành công!\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
            # Xóa các ô input sau khi thành công
            self._clear_form()
            # ... clear các ô khác
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Gửi hồ sơ thất bại: {e}")


# =============================================================================
# TAB CỦA ADMIN: DUYỆT ĐĂNG KÝ ĐẤT
# =============================================================================
class LandRegistryTab(QWidget):
    def __init__(self, admin_account, land_registry_contract):
        super().__init__()
        
        self.admin_account = admin_account
        self.land_registry_contract = land_registry_contract
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
            
            next_id = self.land_registry_contract.next_land_id
            
            pending_requests = []
            # Lặp qua tất cả các land_id đã được tạo
            for i in range(1, next_id):
                status = self.land_registry_contract.is_land_pending(i)
                if status:
                    pending_requests.append(i)

            self.pending_lands_table.setRowCount(len(pending_requests))

            for row, land_id in enumerate(pending_requests):
                land_tuple = self.land_registry_contract.land_parcels(land_id)
                land_data = parse_land_parcel_tuple(land_tuple)
                land_owner = self.land_registry_contract.get_land_owner(land_id)

                if land_data:
                    self.pending_lands_table.setItem(row, 0, QTableWidgetItem(str(land_id)))
                    self.pending_lands_table.setItem(row, 1, QTableWidgetItem(land_owner))
                    self.pending_lands_table.setItem(row, 2, QTableWidgetItem(land_data.owner_cccd))
                    self.pending_lands_table.setItem(row, 3, QTableWidgetItem(land_data.land_address))
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
            land_tuple = self.land_registry_contract.land_parcels(land_id)
            land_data = parse_land_parcel_tuple(land_tuple)
            land_owner = self.land_registry_contract.get_land_owner(land_id)

            if land_data:
                dialog = LandDetailDialog(land_id, land_data, land_owner, self.land_registry_contract, self.admin_account, self)
                if dialog.exec():
                    self.populate_pending_lands()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lấy chi tiết hồ sơ: {e}")

class LandDetailDialog(QDialog):
    # Sử dụng type hint (LandParcelData) để code rõ ràng hơn
    def __init__(self, land_id: int, land_data: LandParcelData, land_owner: str, 
                 land_registry_contract, admin_account, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Chi tiết Hồ sơ Đất #{land_id}")
        self.setMinimumWidth(450)

        # Lưu lại các biến để sử dụng
        self.land_id = land_id
        self.land_data = land_data # Bây giờ là một đối tượng LandParcelData
        self.land_registry_contract = land_registry_contract
        self.admin_account = admin_account

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # <<< THAY ĐỔI: Truy cập dữ liệu bằng thuộc tính (attribute) >>>
        form_layout.addRow("ID Hồ sơ:", QLabel(str(land_id)))
        form_layout.addRow("Địa chỉ Ví Đăng ký:", QLabel(land_owner))
        form_layout.addRow("Số CCCD:", QLabel(self.land_data.owner_cccd))
        form_layout.addRow("Địa chỉ Đất:", QLabel(self.land_data.land_address))
        form_layout.addRow("Diện tích (m2):", QLabel(str(self.land_data.area)))
        
        # Tạo link có thể click được
        pdf_link = f"<a href='{self.land_data.pdf_uri.replace('ipfs://', 'http://127.0.0.1:8080/ipfs/')}'>Mở file PDF</a>"
        pdf_label = QLabel(pdf_link)
        pdf_label.setOpenExternalLinks(True)
        form_layout.addRow("Link PDF:", pdf_label)
        
        image_link = f"<a href='{self.land_data.image_uri.replace('ipfs://', 'http://127.0.0.1:8080/ipfs/')}'>Mở file Hình ảnh</a>"
        image_label = QLabel(image_link)
        image_label.setOpenExternalLinks(True)
        form_layout.addRow("Link Hình ảnh:", image_label)
        
        layout.addLayout(form_layout)

        # Nút Duyệt và Từ chối (không đổi)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Duyệt & Mint NFT")
        self.button_box.button(QDialogButtonBox.Cancel).setText("Từ chối Hồ sơ")

        self.button_box.accepted.connect(self.handle_approve)
        self.button_box.rejected.connect(self.handle_reject)
        layout.addWidget(self.button_box)

    def handle_approve(self):
        # <<< THAY ĐỔI: Truy cập dữ liệu bằng thuộc tính >>>
        print(" -> Bước 1: Tạo đối tượng JSON metadata...")
        metadata_json = {
            "name": f"Bất động sản #{self.land_id}",
            "description": f"Đại diện quyền sở hữu kỹ thuật số cho bất động sản tại địa chỉ {self.land_data.land_address}.",
            "image": self.land_data.image_uri,
            "attributes": [
                {"trait_type": "Địa chỉ", "value": self.land_data.land_address},
                {"trait_type": "Diện tích (m2)", "value": self.land_data.area},
                {"trait_type": "Tài liệu pháp lý", "value": self.land_data.pdf_uri}
            ]
        }
        
        try:
            # Phần còn lại của hàm không cần thay đổi
            print(f" -> Bước 2: Đang tải metadata lên IPFS...")
            self.parent().setCursor(Qt.WaitCursor)
            metadata_uri = upload_json_to_ipfs(metadata_json)
            self.parent().unsetCursor()
            print(f" -> Tải metadata thành công, URI: {metadata_uri}")

            print(f" -> Bước 3: Đang gửi giao dịch duyệt hồ sơ #{self.land_id}...")
            receipt = self.land_registry_contract.approve_land(
                self.land_id,
                metadata_uri,
                sender=self.admin_account
            )
            
            tx_hash = getattr(receipt, 'txn_hash', 'N/A')
            QMessageBox.information(self, "Thành công", f"Đã duyệt và mint NFT thành công cho hồ sơ #{self.land_id}.\nTx: {tx_hash}")
            self.accept()
            
        except Exception as e:
            self.parent().unsetCursor()
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra trong quá trình duyệt hồ sơ:\n{e}")
            self.reject()

    def handle_reject(self):
        # Hàm này không cần thay đổi gì
        try:
            receipt = self.land_registry_contract.reject_land(self.land_id, sender=self.admin_account)
            tx_hash = getattr(receipt, 'txn_hash', 'N/A')
            QMessageBox.information(self, "Thành công", f"Đã từ chối hồ sơ #{self.land_id}.\nTx: {tx_hash}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra khi từ chối hồ sơ: {e}")
            self.reject()

# =============================================================================
# TAB CỦA ADMIN: DUYỆT GIAO DỊCH
# =============================================================================
class AdminTransactionTab(QWidget):
    def __init__(self, admin_account, marketplace_contract, land_nft_contract, land_registry_contract):
        super().__init__()
        self.admin_account = admin_account
        self.marketplace_contract = marketplace_contract
        self.land_nft_contract = land_nft_contract
        self.land_registry_contract = land_registry_contract

        layout = QVBoxLayout(self)
        title = QLabel("Quản lý Giao dịch Mua bán")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.refresh_button = QPushButton("Làm mới Danh sách")
        self.refresh_button.clicked.connect(self.populate_pending_transactions)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignRight)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(7)
        self.transactions_table.setHorizontalHeaderLabels([
            "ID Giao dịch", "ID Đất", "Người bán", "Người mua", 
            "CCCD Người mua", "Giá (ETH)", "Hành động"
        ])
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transactions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.transactions_table)
        
        self.populate_pending_transactions()

    def populate_pending_transactions(self):
        self.transactions_table.setRowCount(0)
        try:
            next_tx_id = self.marketplace_contract.next_tx_id
            pending_txs = []
            for i in range(1, next_tx_id):
                tx_tuple = self.marketplace_contract.transactions(i)
                if tx_tuple and tx_tuple[5] == 0: # status == 0 (Pending)
                    pending_txs.append(tx_tuple)
            
            self.transactions_table.setRowCount(len(pending_txs))

            for row, tx_tuple in enumerate(pending_txs):
                tx_id = tx_tuple[0]
                listing_id = tx_tuple[1]
                buyer_cccd = tx_tuple[2]
                buyer_address = tx_tuple[3]
                amount_wei = tx_tuple[4]
                
                # Lấy thông tin bổ sung
                listing_tuple = self.marketplace_contract.listings(listing_id)
                listing_data = parse_listing_tuple(listing_tuple)
                
                token_id = listing_data.token_id
                seller_address = self.land_nft_contract.ownerOf(token_id)
                
                # Điền vào bảng
                self.transactions_table.setItem(row, 0, QTableWidgetItem(str(tx_id)))
                self.transactions_table.setItem(row, 1, QTableWidgetItem(str(token_id)))
                self.transactions_table.setItem(row, 2, QTableWidgetItem(seller_address))
                self.transactions_table.setItem(row, 3, QTableWidgetItem(buyer_address))
                self.transactions_table.setItem(row, 4, QTableWidgetItem(buyer_cccd))
                self.transactions_table.setItem(row, 5, QTableWidgetItem(f"{amount_wei / 10**18:.4f}"))
                
                # Tạo các nút hành động
                approve_button = QPushButton("Duyệt")
                reject_button = QPushButton("Từ chối")
                approve_button.setStyleSheet("background-color: #4CAF50; color: white;")
                reject_button.setStyleSheet("background-color: #f44336; color: white;")
                
                approve_button.clicked.connect(lambda checked, tid=tx_id: self.handle_approve(tid))
                reject_button.clicked.connect(lambda checked, tid=tx_id: self.handle_reject(tid))

                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.addWidget(approve_button)
                action_layout.addWidget(reject_button)
                action_layout.setContentsMargins(0, 0, 0, 0)
                self.transactions_table.setCellWidget(row, 6, action_widget)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách giao dịch: {e}")

    def handle_approve(self, tx_id):
        reply = QMessageBox.question(self, "Xác nhận Duyệt", f"Bạn có chắc chắn muốn duyệt giao dịch #{tx_id} không?")
        if reply == QMessageBox.Yes:
            try:
                receipt = self.marketplace_contract.approve_transaction(tx_id, sender=self.admin_account)
                QMessageBox.information(self, "Thành công", f"Đã duyệt giao dịch #{tx_id}!\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
                self.populate_pending_transactions()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Duyệt giao dịch thất bại: {e}")

    def handle_reject(self, tx_id):
        reason, ok = QInputDialog.getText(self, "Lý do Từ chối", "Nhập lý do từ chối giao dịch:")
        if ok:
            try:
                receipt = self.marketplace_contract.reject_transaction(tx_id, reason, sender=self.admin_account)
                QMessageBox.information(self, "Thành công", f"Đã từ chối giao dịch #{tx_id}!\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
                self.populate_pending_transactions()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Từ chối giao dịch thất bại: {e}")

# =============================================================================
# TAB CỦA ADMIN: CẤU HÌNH HỆ THỐNG
# =============================================================================
class SystemConfigTab(QWidget):
    def __init__(self, admin_account, marketplace_contract, parent=None):
        super().__init__(parent)
        self.admin_account = admin_account
        self.marketplace_contract = marketplace_contract

        # Layout chính của tab
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        # === Khu vực Quản lý Phí ===
        fees_group = QGroupBox("Quản lý Phí Giao dịch")
        # Sử dụng QFormLayout để căn chỉnh đẹp hơn
        fees_layout = QFormLayout(fees_group)

        # --- Dòng Phí Đăng tin (Listing Fee) ---
        self.listing_fee_label = QLabel("<đang tải...>")
        self.listing_fee_label.setStyleSheet("font-style: italic;")
        fees_layout.addRow("<b>Phí Đăng tin (Listing Fee):</b>", self.listing_fee_label)

        # --- Dòng Phí Hủy (Cancel Penalty) ---
        self.cancel_penalty_label = QLabel("<đang tải...>")
        self.cancel_penalty_label.setStyleSheet("font-style: italic;")
        fees_layout.addRow("<b>Phí Phạt Hủy (Cancel Penalty):</b>", self.cancel_penalty_label)

        # --- Nút Chỉnh sửa duy nhất ---
        self.edit_fees_button = QPushButton("Chỉnh sửa Phí")
        self.edit_fees_button.clicked.connect(self.edit_fees)
        
        # Thêm nút vào một hàng riêng để nó nằm ở dưới
        fees_layout.addRow("", self.edit_fees_button)

        main_layout.addWidget(fees_group)
        
        # Tải dữ liệu phí ban đầu
        self.load_current_fees()

    def load_current_fees(self):
        """Tải và hiển thị các mức phí hiện tại từ contract."""
        try:
            listing_fee = self.marketplace_contract.listing_fee
            cancel_penalty = self.marketplace_contract.cancel_penalty
            
            # Hiển thị giá trị (đơn vị là Wei), có thể thêm định dạng cho dễ đọc
            # Ví dụ: f"{listing_fee / 10**18:.4f} ETH ({listing_fee} Wei)"
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
        # Lấy giá trị hiện tại để hiển thị làm giá trị mặc định trong hộp thoại
        try:
            current_listing_fee = self.marketplace_contract.listing_fee
            current_cancel_penalty = self.marketplace_contract.cancel_penalty
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lấy giá trị phí hiện tại: {e}")
            return

        # Mở hộp thoại cho Phí Đăng tin
        new_listing_fee_str, ok1 = QInputDialog.getText(
            self, 
            "Bước 1/2: Chỉnh sửa Phí Đăng tin", 
            "Nhập giá trị Phí Đăng tin mới (đơn vị Wei):",
            QLineEdit.Normal,
            str(current_listing_fee)
        )
        
        # Nếu người dùng nhấn OK và có nhập liệu, tiếp tục hỏi Phí Hủy
        if ok1 and new_listing_fee_str is not None:
            new_cancel_penalty_str, ok2 = QInputDialog.getText(
                self,
                "Bước 2/2: Chỉnh sửa Phí Phạt Hủy",
                "Nhập giá trị Phí Phạt Hủy mới (đơn vị Wei):",
                QLineEdit.Normal,
                str(current_cancel_penalty)
            )

            # Nếu người dùng nhấn OK ở cả hai hộp thoại
            if ok2 and new_cancel_penalty_str is not None:
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
                    QMessageBox.information(self, "Thành công", f"Đã gửi giao dịch cập nhật phí!\nTx: {tx_hash}")
                    
                    # Tải lại dữ liệu để hiển thị giá trị mới sau khi giao dịch thành công
                    # Trong ứng dụng thực tế, nên chờ xác nhận giao dịch
                    self.load_current_fees()

                except ValueError:
                    QMessageBox.warning(self, "Dữ liệu không hợp lệ", "Vui lòng chỉ nhập số nguyên.")
                except Exception as e:
                    QMessageBox.critical(self, "Lỗi Giao dịch", f"Cập nhật phí thất bại: {e}")   

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
        self.setWindowTitle("Đăng nhập Hệ thống")
        self.setGeometry(100, 100, 350, 220)

        main_layout = QVBoxLayout(self)
        
        title = QLabel("Đăng nhập")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        main_layout.addWidget(title)

        form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        # === THAY ĐỔI: Tùy chỉnh form dựa trên chế độ ===
        if USE_MOCK_DATA:
            # Ở chế độ mock, chỉ cần username
            self.username_input.setPlaceholderText("Nhập 'admin', 'user_a', hoặc 'user_b'")
            form_layout.addRow("Username:", self.username_input)
            form_layout.addRow("Password:", self.password_input)
        else:
            # Ở chế độ thật, cần username (alias) và password
            self.username_input.setPlaceholderText("Nhập alias tài khoản Ape của bạn")
            form_layout.addRow("Username (Alias):", self.username_input)
            form_layout.addRow("Password:", self.password_input)
        
        main_layout.addLayout(form_layout)

        self.login_button = QPushButton("Đăng nhập")
        main_layout.addWidget(self.login_button, alignment=Qt.AlignCenter)
        self.login_button.clicked.connect(self.handle_login)
        self.setLayout(main_layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Username.")
            return

        if USE_MOCK_DATA:
            # --- Logic đăng nhập giả (đã cập nhật) ---
            if username == "admin":
                # Sử dụng địa chỉ nhất quán từ mock_blockchain.py
                mock_admin_account = MockAccount(MOCK_ADMIN_ADDRESS)
                self.main_window.show_admin_ui(mock_admin_account)
            elif username == "user_a":
                mock_user_account = MockAccount(MOCK_USER_A_ADDRESS)
                self.main_window.show_customer_ui(mock_user_account)
            elif username == "user_b":
                mock_user_account = MockAccount(MOCK_USER_B_ADDRESS)
                self.main_window.show_customer_ui(mock_user_account)
            else:
                QMessageBox.warning(self, "Đăng nhập thất bại", "Username phải là 'admin', 'user_a', hoặc 'user_b'.")
        else:
            # --- Logic đăng nhập thật với Ape ---
            password = self.password_input.text()
            if not password:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Password.")
                return
            
            try:
                # 1. Tải và mở khóa tài khoản Ape
                user_account = accounts.load(username)
                user_account.set_autosign(True, passphrase=password)
                print(f"Đăng nhập thành công với tài khoản: {user_account.address}")
                
                # 2. Lấy địa chỉ admin từ contract thật
                marketplace_contract = project.Marketplace.at(MARKETPLACE_ADDRESS)
                admin_address = marketplace_contract.admin
                
                # 3. Kiểm tra vai trò và chuyển giao diện
                if user_account.address.lower() == admin_address.lower():
                    self.main_window.show_admin_dashboard(user_account)
                else:
                    self.main_window.show_user_dashboard(user_account)
            
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Đăng nhập", f"Tên người dùng hoặc mật khẩu không hợp lệ.\nChi tiết: {e}")

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
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        # Tạo sẵn các "trang" giao diện
        self.login_page = LoginWindow(self)
        self.admin_dashboard_page = QWidget() # Widget giữ chỗ
        self.user_dashboard_page = QWidget()  # Widget giữ chỗ

        self.central_widget.addWidget(self.login_page)
        self.central_widget.addWidget(self.admin_dashboard_page)
        self.central_widget.addWidget(self.user_dashboard_page)
        
        self.current_user = None
        self.mock_registry = MockLandRegistry()
        self.mock_nft = MockLandNFT(self.mock_registry)
        self.mock_marketplace = MockMarketplace(MOCK_ADMIN_ADDRESS)
        # Bắt đầu ở trang đăng nhập
        self.show_login_ui()
    
    def show_login_ui(self):
        self.central_widget.setCurrentWidget(self.login_page)
        print("Switched backs to Login Page")

    def show_admin_ui(self, admin_account):
        # Khởi tạo layout
        container = self.admin_dashboard_page

        # Xóa các layout cũ nếu có
        old_layout = container.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            # Xóa layout cũ
            QWidget().setLayout(old_layout)

        tabs = QTabWidget()

        # Set contract
        marketplace_contract = self.mock_marketplace
        land_registry_contract = self.mock_registry
        land_nft_contract = self.mock_nft

        # Admin Tabs
        self.land_registry_tab = LandRegistryTab(admin_account, land_registry_contract)
        self.transaction_tab = AdminTransactionTab(admin_account, marketplace_contract, land_nft_contract, land_registry_contract)
        self.config_tab = SystemConfigTab(admin_account, marketplace_contract)
        self.settings_tab = SettingsTab(admin_account.address, self)
        

        tabs.addTab(self.land_registry_tab, "Land Registration")
        tabs.addTab(self.transaction_tab, "Transaction")
        tabs.addTab(self.config_tab, "System Config")
        tabs.addTab(self.settings_tab, "Setting")
        
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(tabs)

        # Thay thế widget giữ chỗ bằng dashboard thật
        self.central_widget.setCurrentWidget(container)
        print("Switched to Admin Dashboard.")
    
    def show_customer_ui(self, user_account):
        container = self.user_dashboard_page

        # Xóa các layout cũ nếu có
        old_layout = container.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            # Xóa layout cũ
            QWidget().setLayout(old_layout)

        tabs = QTabWidget()
        
        # Set contract
        land_registry_contract = self.mock_registry
        marketplace_contract = self.mock_marketplace
        land_nft_contract = self.mock_nft


        self.register_tab = RegisterLandTab(user_account, land_registry_contract)
        self.marketplace_tab = MarketplaceTab(user_account, marketplace_contract, land_registry_contract, land_nft_contract)
        self.my_account_tab = MyAccountTab(user_account, land_registry_contract, land_nft_contract, marketplace_contract)
        self.settings_tab = SettingsTab(user_account.address, self)
        
        # Customer Tabs
        tabs.addTab(QLabel(f"Welcome User: {user_account.address}"), "Sàn Giao Dịch")
        tabs.addTab(self.register_tab, "Register Land")
        tabs.addTab(self.marketplace_tab, "Marketplace")
        tabs.addTab(self.my_account_tab, "My Account")
        tabs.addTab(self.settings_tab, "Setting")

        container_layout = QVBoxLayout(container)
        container_layout.addWidget(tabs)

        self.central_widget.setCurrentWidget(container)
        print("Switched to User Dashboard.")

    def handle_logout(self):
        """
        Hàm xử lý khi nhận được tín hiệu logout.
        Chuyển giao diện về màn hình đăng nhập.
        """
        print("Handling logout...")
        self.current_user = None
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
