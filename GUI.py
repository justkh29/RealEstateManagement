import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton,
    QLineEdit, QLabel, QFormLayout, QTableWidget, QTableWidgetItem, QScrollArea,
    QHeaderView, QMessageBox, QDialog, QDialogButtonBox, QHBoxLayout, QFileDialog,
    QFrame, QListWidget, QListWidgetItem, QGridLayout, QGroupBox, QInputDialog, QStackedWidget
)
from PySide6.QtCore import QObject, QThread, Qt, Signal, QRegularExpression, QUrl, Slot
from PySide6.QtGui import QFont, QRegularExpressionValidator, QDesktopServices, QPixmap
from ape import accounts, project, networks
from mock_blockchain import (
    MockAccount, MockLandRegistry, MockLandNFT, MockMarketplace,
    MOCK_ADMIN_ADDRESS, MOCK_USER_A_ADDRESS, MOCK_USER_B_ADDRESS
)
from ipfs_utils import upload_file_to_ipfs, upload_json_to_ipfs, FLASK_BACKEND_URL, IPFS_URL_VIEWER
from crypto_utils import encrypt_data, decrypt_data, save_land_info, get_real_cccd

from dataclasses import dataclass

USE_MOCK_DATA = True
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

@dataclass
class TransactionData:
    tx_id: int
    listing_id: int
    buyer_cccd: str
    buyer_address: str
    amount: int
    status: int # 0: Pending, 1: Approved, 2: Rejected, 3: Cancelled
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

def parse_transaction_tuple(data_tuple: tuple) -> TransactionData:
    if not isinstance(data_tuple, tuple) or len(data_tuple) != 7:
        return None
    return TransactionData(*data_tuple)
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
class LandListItemWidget(QWidget):
    sell_requested = Signal(int)

    def __init__(self, land_data: LandParcelData, is_selling: bool = False, parent=None):
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

        self.sell_button = QPushButton()
        if is_selling:
            self.sell_button.setText("Đang đăng bán")
            self.sell_button.setEnabled(False) # Vô hiệu hóa nút
            # Có thể đổi màu để dễ nhận biết
            self.sell_button.setStyleSheet("background-color: #FFC107; color: black;") 
        else:
            self.sell_button.setText("Bán")
            self.sell_button.setEnabled(True)
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
        real_cccd = get_real_cccd(self.land_data.land_address)
        if real_cccd is None:
            display_cccd = f"{self.land_data.owner_cccd[:15]}... [Đã mã hóa]"
        else:
            display_cccd = f"{real_cccd} (Đã xác minh cục bộ)"
        detail_text = (
            f"Thông tin chi tiết Thửa Đất #{self.land_data.id}\n\n"
            f"Chủ sở hữu (CCCD): {display_cccd}\n"
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
        backend_image_url = f"{IPFS_URL_VIEWER}{cid}"
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
        self.land_data = land_data
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
        pdf_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(land_data.pdf_uri.replace("ipfs://", IPFS_URL_VIEWER))))
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
            print("Đang mã hóa thông tin người mua...")
            buyer_cccd_encrypted = encrypt_data(buyer_cccd)
            receipt = self.marketplace_contract.initiate_transaction(
                self.listing_data.listing_id,
                buyer_cccd_encrypted,
                sender=self.user_account,
                value=price_wei
            )
            QMessageBox.information(self, "Thành công", f"Đã gửi yêu cầu mua thành công!\nGiao dịch của bạn đang chờ Admin duyệt.\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
            save_land_info(self.land_data.land_address, buyer_cccd)
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

        # Sử dụng QVBoxLayout để xếp các thành phần theo chiều dọc
        # (Header ở trên, Danh sách ở dưới)
        main_layout = QVBoxLayout(self)

        # 1. Header: Chứa Tiêu đề và Nút Refresh
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Thị trường Bất động sản")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        
        self.refresh_button = QPushButton("🔄 Làm mới")
        self.refresh_button.setFixedWidth(120)
        self.refresh_button.setStyleSheet("padding: 5px; font-weight: bold;")
        self.refresh_button.clicked.connect(self.load_listings)

        header_layout.addWidget(title_label)
        header_layout.addStretch() # Khoảng trống để đẩy nút sang phải
        header_layout.addWidget(self.refresh_button)
        
        # Thêm header vào layout chính
        main_layout.addLayout(header_layout)

        # 2. Khu vực hiển thị danh sách (Scroll Area)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame) # Bỏ viền để nhìn thoáng hơn
        
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setSpacing(20) # Tăng khoảng cách giữa các thẻ cho đẹp
        
        scroll_area.setWidget(grid_container)
        
        main_layout.addWidget(scroll_area)

        self.load_listings()

    def load_listings(self):
        # Hiệu ứng loading cho nút bấm
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Đang tải...")
        QApplication.processEvents()

        # Xóa các widget cũ trong lưới
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        try:
            next_id = self.marketplace_contract.next_listing_id
            
            row, col = 0, 0
            max_columns = 3 

            for i in range(1, next_id):
                listing_tuple = self.marketplace_contract.listings(i)
                listing_data = parse_listing_tuple(listing_tuple)
                
                if listing_data and listing_data.listing_id != 0 and listing_data.status == 0:
                    token_id = listing_data.token_id
                    seller_address = self.land_nft_contract.ownerOf(token_id)
                    
                    # Không hiển thị đất do chính mình bán
                    if seller_address.lower() == self.user_account.address.lower():
                        continue 

                    land_tuple = self.land_registry_contract.land_parcels(token_id)
                    land_data = parse_land_parcel_tuple(land_tuple)
                    
                    if land_data and land_data.id != 0:
                        card = ListingCardWidget(listing_data, land_data, seller_address)
                        card.view_details_requested.connect(self.handle_view_details)
                        self.grid_layout.addWidget(card, row, col)
                    
                    # Logic xuống dòng
                    col += 1
                    if col >= max_columns:
                        col = 0
                        row += 1
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách niêm yết: {e}")
        
        # Trả lại trạng thái nút bấm
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("🔄 Làm mới")

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

class MyTransactionsTab(QWidget):
    def __init__(self, user_account, marketplace_contract, land_registry_contract, land_nft_contract):
        super().__init__()
        self.user_account = user_account
        self.marketplace_contract = marketplace_contract
        self.land_registry_contract = land_registry_contract
        self.land_nft_contract = land_nft_contract # Dùng để lấy thông tin bổ sung nếu cần

        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Lịch sử Giao dịch & Đơn mua")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.populate_transactions)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

        # Bảng hiển thị
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID GD", "Địa chỉ Đất", "Giá (ETH)", "Trạng thái", "Ngày tạo", "Hành động"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.populate_transactions()

    def populate_transactions(self):
        self.table.setRowCount(0)
        try:
            next_tx_id = self.marketplace_contract.next_tx_id
            
            # Duyệt ngược để thấy giao dịch mới nhất trước
            for i in range(next_tx_id - 1, 0, -1):
                tx_tuple = self.marketplace_contract.transactions(i)
                tx_data = parse_transaction_tuple(tx_tuple)
                
                if tx_data and tx_data.buyer_address.lower() == self.user_account.address.lower():
                    self.add_transaction_row(tx_data)
                    
        except Exception as e:
            print(f"Lỗi tải giao dịch: {e}")

    def add_transaction_row(self, tx_data: TransactionData):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 1. Lấy thông tin đất để hiển thị cho đẹp (thay vì chỉ hiện ID)
        land_address_display = "Đang tải..."
        try:
            listing_tuple = self.marketplace_contract.listings(tx_data.listing_id)
            listing_data = parse_listing_tuple(listing_tuple)
            if listing_data:
                land_tuple = self.land_registry_contract.land_parcels(listing_data.token_id)
                land_data = parse_land_parcel_tuple(land_tuple)
                if land_data:
                    land_address_display = f"#{listing_data.token_id} - {land_data.land_address}"
        except:
            land_address_display = f"Listing #{tx_data.listing_id}"

        # 2. Xử lý hiển thị trạng thái
        status_text = {
            0: "Đang chờ duyệt",
            1: "Thành công",
            2: "Bị từ chối",
            3: "Đã hủy"
        }.get(tx_data.status, "Không rõ")
        
        # Màu sắc trạng thái
        status_item = QTableWidgetItem(status_text)
        if tx_data.status == 0:
            status_item.setForeground(Qt.blue)
            status_item.setFont(QFont("Arial", 9, QFont.Bold))
        elif tx_data.status == 1:
            status_item.setForeground(Qt.green)
        elif tx_data.status == 2 or tx_data.status == 3:
            status_item.setForeground(Qt.red)

        # 3. Điền dữ liệu vào cột
        self.table.setItem(row, 0, QTableWidgetItem(str(tx_data.tx_id)))
        self.table.setItem(row, 1, QTableWidgetItem(land_address_display))
        self.table.setItem(row, 2, QTableWidgetItem(f"{tx_data.amount / 10**18:.4f}"))
        self.table.setItem(row, 3, status_item)
        
        # Convert timestamp (nếu cần, ở đây hiển thị raw hoặc format lại)
        import datetime
        date_str = datetime.datetime.fromtimestamp(tx_data.created_at).strftime('%Y-%m-%d %H:%M')
        self.table.setItem(row, 4, QTableWidgetItem(date_str))

        # 4. Cột Hành động (Nút Hủy)
        if tx_data.status == 0: # Chỉ hiển thị nút hủy nếu đang chờ (Pending)
            cancel_btn = QPushButton("Hủy Giao dịch")
            cancel_btn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
            cancel_btn.clicked.connect(lambda: self.handle_cancel(tx_data.tx_id))
            self.table.setCellWidget(row, 5, cancel_btn)
        else:
            self.table.setItem(row, 5, QTableWidgetItem("-"))

    def handle_cancel(self, tx_id):
        reply = QMessageBox.question(
            self, "Xác nhận Hủy",
            "Bạn có chắc chắn muốn hủy giao dịch này?\n"
            "Bạn sẽ nhận lại tiền cọc nhưng sẽ bị trừ một khoản phí phạt nhỏ.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                receipt = self.marketplace_contract.buyer_cancel(tx_id, sender=self.user_account)
                
                QMessageBox.information(self, "Đã hủy", f"Giao dịch #{tx_id} đã được hủy thành công.\nTiền cọc (sau khi trừ phí) đã được hoàn lại.")
                self.populate_transactions() # Làm mới bảng
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể hủy giao dịch: {e}")
# =============================================================================
# TAB CỦA USER: ĐẤT CỦA TÔI (MY ACCOUNT)
# =============================================================================
class MyLandTab(QWidget):
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
            owned_land_ids = self.land_registry_contract.owner_to_lands(self.user_account.address)
            
            # Lấy danh sách tất cả các listing đang active để đối chiếu
            # (Lưu ý: Cách này có thể chậm nếu có quá nhiều listing. 
            # Trong thực tế nên dùng The Graph hoặc lưu cache listing theo owner)
            active_listing_tokens = set()
            next_listing_id = self.marketplace_contract.next_listing_id
            for i in range(1, next_listing_id):
                l_tuple = self.marketplace_contract.listings(i)
                l_data = parse_listing_tuple(l_tuple)
                if l_data and l_data.status == 0: # Active
                    active_listing_tokens.add(l_data.token_id)

            for land_id in owned_land_ids:
                land_tuple = self.land_registry_contract.land_parcels(land_id)
                land_data = parse_land_parcel_tuple(land_tuple)
                
                if land_data and land_data.status == 1:
                    # Kiểm tra xem đất này có đang được bán không
                    is_selling = land_id in active_listing_tokens
                    
                    # Truyền trạng thái is_selling vào widget
                    item_widget = LandListItemWidget(land_data, is_selling)
                    item_widget.sell_requested.connect(self.handle_sell_request)
                    
                    list_item = QListWidgetItem(self.land_list_widget)
                    list_item.setSizeHint(item_widget.sizeHint())
                    self.land_list_widget.addItem(list_item)
                    self.land_list_widget.setItemWidget(list_item, item_widget)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tải tài sản: {e}")
            
    def handle_sell_request(self, token_id):
        """Hàm xử lý đầy đủ luồng đăng bán, tự động lấy CCCD."""
        print(f"Bắt đầu quy trình bán cho token #{token_id}")
        
        try:
            # === BƯỚC 1: HỎI GIÁ ===
            dialog = SellDialog(token_id, self)
            if dialog.exec(): # Trả về True nếu người dùng nhấn OK
                price = dialog.get_price()
                price_in_eth = price / 10**18
                if price is None:
                    QMessageBox.warning(self, "Thông tin không hợp lệ", "Vui lòng nhập giá bán hợp lệ.")
                    return
                # === BƯỚC 2: XÁC NHẬN VÀ ỦY QUYỀN ===
                approved_addr = self.land_nft_contract.getApproved(token_id)
                marketplace_addr = self.marketplace_contract.address

                if approved_addr.lower() != marketplace_addr.lower():
                    reply = QMessageBox.question(
                        self, "Xác nhận Bán và Ủy quyền",
                        f"Bạn đang đăng bán Bất động sản #{token_id} với giá {price} Wei ({price_in_eth} ETH). \n\n"
                        "Để thực hiện đăng bán, bạn cần đồng ý ủy quyền cho Sàn giao dịch được phép chuyển nhượng mảnh đất này khi có người mua. \n\n",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                    
                    # Thực hiện Approve
                    print(f" -> Gửi giao dịch approve cho token #{token_id}...")
                    self.setCursor(Qt.WaitCursor)
                    approve_receipt = self.land_nft_contract.approve(
                        marketplace_addr,
                        token_id,
                        sender=self.user_account
                    )
                    self.unsetCursor()
                    print(" -> Approve thành công.")

                # === BƯỚC 2: TỰ ĐỘNG LẤY CCCD TỪ LANDREGISTRY ===
                self.setCursor(Qt.WaitCursor)
                land_tuple = self.land_registry_contract.land_parcels(token_id)
                land_parcel_data = parse_land_parcel_tuple(land_tuple)
                
                if not land_parcel_data:
                    self.unsetCursor()
                    QMessageBox.critical(self, "Lỗi", "Không tìm thấy dữ liệu đất.")
                    return
                    
                seller_cccd = land_parcel_data.owner_cccd
                
                if not seller_cccd:
                    self.unsetCursor()
                    QMessageBox.critical(self, "Lỗi Dữ liệu", "Không tìm thấy thông tin CCCD cho mảnh đất này trong Registry.")
                    return

                # === BƯỚC 3: GỬI GIAO DỊCH CREATE_LISTING ===
                print(f" -> Bước 3: Gửi giao dịch create_listing với CCCD tự động: {seller_cccd}")
                listing_fee = self.marketplace_contract.listing_fee
                
                receipt = self.marketplace_contract.create_listing(
                    token_id,
                    seller_cccd, # Dùng CCCD vừa lấy được từ Registry
                    price,
                    sender=self.user_account,
                    value=listing_fee
                )
                self.unsetCursor()

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

        form_group = QGroupBox("Đăng ký Mới")
        form_layout = QFormLayout(form_group)
        
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
        
        layout.addWidget(form_group)


        self.register_button = QPushButton("Gửi Hồ sơ Đăng ký")
        self.register_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.register_button.clicked.connect(self.handle_register)
        layout.addWidget(self.register_button, alignment=Qt.AlignCenter)

        history_group = QGroupBox("Lịch sử Đăng ký của Bạn")
        history_layout = QVBoxLayout(history_group)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["ID", "Địa chỉ", "Ngày đăng ký", "Trạng thái"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Giới hạn chiều cao để không chiếm hết chỗ của form
        self.history_table.setMinimumHeight(150) 
        
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_group)

        # Load lịch sử lần đầu
        self.populate_history()
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
        cccd_raw = self.cccd_input.text()
        pdf_uri = self.pdf_uri_input.text()
        image_uri = self.image_uri_input.text()

        if not all([land_address, area, cccd_raw, pdf_uri, image_uri]):
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền đầy đủ tất cả các trường.")
            return

        try:
            cccd_encrypted = encrypt_data(cccd_raw)
            receipt = self.land_registry_contract.register_land(
                land_address, area, cccd_encrypted, pdf_uri, image_uri,
                sender=self.user_account
            )
            QMessageBox.information(self, "Thành công", f"Đã gửi hồ sơ đăng ký thành công!\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
            save_land_info(land_address, cccd_raw)
            # Xóa các ô input sau khi thành công
            self._clear_form()
            self.populate_history() 
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Gửi hồ sơ thất bại: {e}")
    
    def populate_history(self):
        """Tải danh sách đất mà user này đã đăng ký (bao gồm cả Pending)."""
        self.history_table.setRowCount(0)
        try:
            # Lấy danh sách ID đất của user (Mock/Contract cần hỗ trợ hàm này)
            # Lưu ý: Hàm owner_to_lands trả về cả đất đã duyệt và chưa duyệt
            my_land_ids = self.land_registry_contract.owner_to_lands(self.user_account.address)
            
            # Nếu muốn sắp xếp mới nhất lên đầu:
            # my_land_ids.reverse() 

            self.history_table.setRowCount(len(my_land_ids))
            
            for row, land_id in enumerate(my_land_ids):
                # Lấy dữ liệu và parse
                land_tuple = self.land_registry_contract.land_parcels(land_id)
                land_data = parse_land_parcel_tuple(land_tuple)
                
                if land_data:
                    # ID
                    self.history_table.setItem(row, 0, QTableWidgetItem(str(land_data.id)))
                    # Địa chỉ
                    self.history_table.setItem(row, 1, QTableWidgetItem(land_data.land_address))
                    # Ngày (Nếu contract không lưu ngày đk, có thể để trống hoặc update contract)
                    self.history_table.setItem(row, 2, QTableWidgetItem("-")) 
                    
                    # Trạng thái (Tô màu cho đẹp)
                    status_text = "Chờ duyệt"
                    color = Qt.blue
                    if land_data.status == 1: 
                        status_text = "Đã duyệt"
                        color = Qt.green
                    elif land_data.status == 2: 
                        status_text = "Bị từ chối"
                        color = Qt.red
                    
                    status_item = QTableWidgetItem(status_text)
                    status_item.setForeground(color)
                    status_item.setFont(QFont("Arial", 8, QFont.Bold))
                    self.history_table.setItem(row, 3, status_item)

        except Exception as e:
            print(f"Lỗi tải lịch sử: {e}")

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
                cccd = decrypt_data(land_data.owner_cccd)

                if land_data:
                    self.pending_lands_table.setItem(row, 0, QTableWidgetItem(str(land_id)))
                    self.pending_lands_table.setItem(row, 1, QTableWidgetItem(land_owner))
                    self.pending_lands_table.setItem(row, 2, QTableWidgetItem(cccd))
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

        cccd = decrypt_data(self.land_data.owner_cccd)

        # <<< THAY ĐỔI: Truy cập dữ liệu bằng thuộc tính (attribute) >>>
        form_layout.addRow("ID Hồ sơ:", QLabel(str(land_id)))
        form_layout.addRow("Địa chỉ Ví Đăng ký:", QLabel(land_owner))
        form_layout.addRow("Số CCCD:", QLabel(cccd))
        form_layout.addRow("Địa chỉ Đất:", QLabel(self.land_data.land_address))
        form_layout.addRow("Diện tích (m2):", QLabel(str(self.land_data.area)))
        
        # Tạo link có thể click được
        pdf_link = f"<a href='{self.land_data.pdf_uri.replace('ipfs://', IPFS_URL_VIEWER)}'>Mở file PDF</a>"
        pdf_label = QLabel(pdf_link)
        pdf_label.setOpenExternalLinks(True)
        form_layout.addRow("Link PDF:", pdf_label)
        
        image_link = f"<a href='{self.land_data.image_uri.replace('ipfs://', IPFS_URL_VIEWER)}'>Mở file Hình ảnh</a>"
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
                buyer_cccd_encrypted = tx_tuple[2]
                buyer_address = tx_tuple[3]
                amount_wei = tx_tuple[4]
                
                # Lấy thông tin bổ sung
                listing_tuple = self.marketplace_contract.listings(listing_id)
                listing_data = parse_listing_tuple(listing_tuple)
                
                buyer_cccd = decrypt_data(buyer_cccd_encrypted)
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
        self.mock_marketplace = MockMarketplace(MOCK_ADMIN_ADDRESS, self.mock_nft)
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
        self.admin_transaction_tab = AdminTransactionTab(admin_account, marketplace_contract, land_nft_contract, land_registry_contract)
        self.config_tab = SystemConfigTab(admin_account, marketplace_contract)
        self.settings_tab = SettingsTab(admin_account.address, self)
        

        tabs.addTab(self.land_registry_tab, "Land Registration")
        tabs.addTab(self.admin_transaction_tab, "Transaction")
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
        self.my_account_tab = MyLandTab(user_account, land_registry_contract, land_nft_contract, marketplace_contract)
        self.settings_tab = SettingsTab(user_account.address, self)
        self.transaction_history_tab = MyTransactionsTab(user_account, marketplace_contract, land_registry_contract, land_nft_contract)
        
        # Customer Tabs
        tabs.addTab(self.register_tab, "Register Land")
        tabs.addTab(self.marketplace_tab, "Marketplace")
        tabs.addTab(self.my_account_tab, "My Land")
        tabs.addTab(self.transaction_history_tab, "Transaction History")
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
