import requests
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QPushButton,
    QLineEdit, QLabel, QFormLayout, QTableWidget, QTableWidgetItem, QScrollArea,
    QHeaderView, QMessageBox, QDialog, QDialogButtonBox, QHBoxLayout, QFileDialog,
    QFrame, QListWidget, QListWidgetItem, QGridLayout, QGroupBox, QInputDialog, QStackedWidget
)
from PySide6.QtCore import QObject, QThread, Qt, Signal, QRegularExpression, QUrl, Slot
from PySide6.QtGui import QFont, QRegularExpressionValidator, QDesktopServices, QPixmap
from ape import accounts, project, networks
from app_modules.mock_blockchain import (
    MockAccount, MockLandRegistry, MockLandNFT, MockMarketplace,
    MOCK_ADMIN_ADDRESS, MOCK_USER_A_ADDRESS, MOCK_USER_B_ADDRESS
)
from app_modules.ipfs_utils import upload_file_to_ipfs, upload_json_to_ipfs, FLASK_BACKEND_URL, IPFS_URL_VIEWER
from app_modules.crypto_utils import encrypt_data, decrypt_data, save_land_info, get_real_cccd

from dataclasses import dataclass

USE_MOCK_DATA = False
NODE_URL = "http://192.168.0.140:8545"

LAND_NFT_ADDRESS = "0x437AAc235f0Ed378AB9CbD5b7C20B1c3B28b573a"       # Ví dụ: 0x5FbDB2315678...
LAND_REGISTRY_ADDRESS = "0x9FfDa9D1FeDdF35a26D2F68a50Fd600e68696469"  # Ví dụ: 0xe7f1725E7734...
MARKETPLACE_ADDRESS = "0xa8EFf51482B108A94CB813Af2C59B467Cc5Fa08E"    # Ví dụ: 0x9fE46736679d...
# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LandParcelData:
    id: int
    land_address: str
    area: int
    owner_cccd: str
    status: int
    pdf_uri: str
    image_uri: str

@dataclass
class ListingData:
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
    status: int 
    created_at: int

# =============================================================================
# DATA PARSERS
# =============================================================================

def parse_land_parcel_tuple(data_obj) -> LandParcelData:
    if not data_obj:
         return LandParcelData(id=0, land_address="", area=0, owner_cccd="", status=99, pdf_uri="", image_uri="")
    
    data_tuple = tuple(data_obj) 
    
    if len(data_tuple) != 7:
        print(f"Warning: Invalid LandParcel data length: {data_tuple}")
        return LandParcelData(id=0, land_address="", area=0, owner_cccd="", status=99, pdf_uri="", image_uri="")
    return LandParcelData(*data_tuple)

def parse_listing_tuple(data_obj) -> ListingData:
    if not data_obj:
        return ListingData(listing_id=0, token_id=0, seller_cccd="", price=0, status=99, created_at=0)

    data_tuple = tuple(data_obj) 

    if len(data_tuple) != 6:
        print(f"Warning: Invalid Listing data length: {data_tuple}")
        return ListingData(listing_id=0, token_id=0, seller_cccd="", price=0, status=99, created_at=0)
    return ListingData(*data_tuple)

def parse_transaction_tuple(data_obj) -> TransactionData:
    if not data_obj: return None
    
    data_tuple = tuple(data_obj) 
    
    if len(data_tuple) != 7:
        return None
    return TransactionData(*data_tuple)

# =============================================================================
# WORKERS
# =============================================================================

class ImageDownloader(QObject):
    finished = Signal(QPixmap)
    error = Signal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            
            if pixmap.isNull():
                self.error.emit(f"Unable to load image data from URL: {self.url}")
            else:
                self.finished.emit(pixmap)
        except Exception as e:
            self.error.emit(f"Error downloading image: {e}")

# =============================================================================
# REUSABLE WIDGETS
# =============================================================================

class LandListItemWidget(QWidget):
    sell_requested = Signal(int)

    def __init__(self, land_data: LandParcelData, is_selling: bool = False, parent=None):
        super().__init__(parent)
        self.land_data = land_data

        main_layout = QHBoxLayout(self)
        text_layout = QVBoxLayout()
        
        id_label = QLabel(f"<b>Mã Thửa Đất: #{self.land_data.id}</b>")
        info_label = QLabel(
            f"Địa chỉ: {self.land_data.land_address}\n"
            f"Diện tích: {self.land_data.area} m²"
        )
        
        text_layout.addWidget(id_label)
        text_layout.addWidget(info_label)
        main_layout.addLayout(text_layout)
        main_layout.addStretch()

        self.sell_button = QPushButton()
        if is_selling:
            self.sell_button.setText("Đang đăng bán")
            self.sell_button.setEnabled(False)
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

class ListingCardWidget(QFrame):
    view_details_requested = Signal(int, str)

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

        cid = image_ipfs_uri.replace("ipfs://", "")
        backend_image_url = f"{IPFS_URL_VIEWER}{cid}"
        
        self.thread = QThread()
        self.worker = ImageDownloader(backend_image_url)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.set_image)
        self.worker.error.connect(self.handle_image_error)
        self.worker.finished.connect(self.thread.quit)
        self.thread.start()
    
    def set_image(self, pixmap):
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)

    def handle_image_error(self, error_message):
        print(f"Lỗi tải ảnh cho listing #{self.listing_id}: {error_message}")
        self.image_label.setText("[Lỗi tải ảnh]")

# =============================================================================
# DIALOGS
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
        
        self.cccd_input = QLineEdit()
        self.cccd_input.setPlaceholderText("Nhập số CCCD của bạn để tiếp tục")
        layout.addWidget(QLabel("<b>CCCD của Người mua (*):</b>"))
        layout.addWidget(self.cccd_input)
        
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
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Giao dịch", f"Gửi yêu cầu mua thất bại: {e}")

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

        self.form_layout.addRow("<b>Giá bán (Wei) (*):</b>", self.price_input)
        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_price(self):
        price_str = self.price_input.text().strip()
        if price_str:
            try:
                return int(price_str)
            except ValueError:
                return None
        return None

class LandDetailDialog(QDialog):
    def __init__(self, land_id: int, land_data: LandParcelData, land_owner: str, 
                 land_registry_contract, admin_account, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Chi tiết Hồ sơ Đất #{land_id}")
        self.setMinimumWidth(450)

        self.land_id = land_id
        self.land_data = land_data
        self.land_registry_contract = land_registry_contract
        self.admin_account = admin_account

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        cccd = decrypt_data(self.land_data.owner_cccd)

        form_layout.addRow("ID Hồ sơ:", QLabel(str(land_id)))
        form_layout.addRow("Địa chỉ Ví Đăng ký:", QLabel(land_owner))
        form_layout.addRow("Số CCCD:", QLabel(cccd))
        form_layout.addRow("Địa chỉ Đất:", QLabel(self.land_data.land_address))
        form_layout.addRow("Diện tích (m2):", QLabel(str(self.land_data.area)))
        
        pdf_link = f"<a href='{self.land_data.pdf_uri.replace('ipfs://', IPFS_URL_VIEWER)}'>Mở file PDF</a>"
        pdf_label = QLabel(pdf_link)
        pdf_label.setOpenExternalLinks(True)
        form_layout.addRow("Link PDF:", pdf_label)
        
        image_link = f"<a href='{self.land_data.image_uri.replace('ipfs://', IPFS_URL_VIEWER)}'>Mở file Hình ảnh</a>"
        image_label = QLabel(image_link)
        image_label.setOpenExternalLinks(True)
        form_layout.addRow("Link Hình ảnh:", image_label)
        
        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Duyệt & Mint NFT")
        self.button_box.button(QDialogButtonBox.Cancel).setText("Từ chối Hồ sơ")

        self.button_box.accepted.connect(self.handle_approve)
        self.button_box.rejected.connect(self.handle_reject)
        layout.addWidget(self.button_box)

    def handle_approve(self):
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
        try:
            receipt = self.land_registry_contract.reject_land(self.land_id, sender=self.admin_account)
            tx_hash = getattr(receipt, 'txn_hash', 'N/A')
            QMessageBox.information(self, "Thành công", f"Đã từ chối hồ sơ #{self.land_id}.\nTx: {tx_hash}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Có lỗi xảy ra khi từ chối hồ sơ: {e}")
            self.reject()

# =============================================================================
# CUSTOMER TABS
# =============================================================================

class MarketplaceTab(QWidget):
    def __init__(self, user_account, marketplace_contract, land_registry_contract, land_nft_contract):
        super().__init__()
        self.user_account = user_account
        self.marketplace_contract = marketplace_contract
        self.land_registry_contract = land_registry_contract
        self.land_nft_contract = land_nft_contract

        main_layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        title_label = QLabel("Thị trường Bất động sản")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        
        self.refresh_button = QPushButton("🔄 Làm mới")
        self.refresh_button.setFixedWidth(120)
        self.refresh_button.setStyleSheet("padding: 5px; font-weight: bold;")
        self.refresh_button.clicked.connect(self.load_listings)

        header_layout.addWidget(title_label)
        header_layout.addStretch() 
        header_layout.addWidget(self.refresh_button)
        main_layout.addLayout(header_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setAlignment(Qt.AlignTop)
        self.grid_layout.setSpacing(20)
        
        scroll_area.setWidget(grid_container)
        main_layout.addWidget(scroll_area)

        self.load_listings()

    def load_listings(self):
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Đang tải...")
        QApplication.processEvents()

        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        try:
            next_id = self.marketplace_contract.next_listing_id()
            
            row, col = 0, 0
            max_columns = 3 

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
                        card = ListingCardWidget(listing_data, land_data, seller_address)
                        card.view_details_requested.connect(self.handle_view_details)
                        self.grid_layout.addWidget(card, row, col)
                    
                    col += 1
                    if col >= max_columns:
                        col = 0
                        row += 1
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách niêm yết: {e}")
        
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
        self.land_nft_contract = land_nft_contract

        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        title = QLabel("Lịch sử Giao dịch & Đơn mua")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        self.refresh_button = QPushButton("Làm mới")
        self.refresh_button.clicked.connect(self.populate_transactions)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        layout.addLayout(header_layout)

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
            next_tx_id = self.marketplace_contract.next_tx_id()
            
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

        status_text = {
            0: "Đang chờ duyệt",
            1: "Thành công",
            2: "Bị từ chối",
            3: "Đã hủy"
        }.get(tx_data.status, "Không rõ")
        
        status_item = QTableWidgetItem(status_text)
        if tx_data.status == 0:
            status_item.setForeground(Qt.blue)
            status_item.setFont(QFont("Arial", 9, QFont.Bold))
        elif tx_data.status == 1:
            status_item.setForeground(Qt.green)
        elif tx_data.status == 2 or tx_data.status == 3:
            status_item.setForeground(Qt.red)

        self.table.setItem(row, 0, QTableWidgetItem(str(tx_data.tx_id)))
        self.table.setItem(row, 1, QTableWidgetItem(land_address_display))
        self.table.setItem(row, 2, QTableWidgetItem(f"{tx_data.amount / 10**18:.4f}"))
        self.table.setItem(row, 3, status_item)
        
        import datetime
        date_str = datetime.datetime.fromtimestamp(tx_data.created_at).strftime('%Y-%m-%d %H:%M')
        self.table.setItem(row, 4, QTableWidgetItem(date_str))

        if tx_data.status == 0:
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
                self.populate_transactions()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể hủy giao dịch: {e}")

class MyLandTab(QWidget):
    def __init__(self, user_account, land_registry_contract, land_nft_contract, marketplace_contract):
        super().__init__()
        self.user_account = user_account
        self.land_registry_contract = land_registry_contract
        self.land_nft_contract = land_nft_contract 
        self.marketplace_contract = marketplace_contract
        layout = QVBoxLayout(self)

        title = QLabel("Tài sản Bất động sản của bạn")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        self.refresh_button = QPushButton("Làm mới Danh sách")
        self.refresh_button.clicked.connect(self.populate_my_lands)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignRight)

        self.land_list_widget = QListWidget()
        self.land_list_widget.setStyleSheet("QListWidget::item { border: 1px solid #ccc; border-radius: 5px; margin-bottom: 5px; }")
        layout.addWidget(self.land_list_widget)

        self.populate_my_lands()

    def populate_my_lands(self):
        self.land_list_widget.clear()
        try:
            owned_land_ids = self.land_registry_contract.get_lands_by_owner(self.user_account.address)
            
            active_listing_tokens = set()
            next_listing_id = self.marketplace_contract.next_listing_id()
            for i in range(1, next_listing_id):
                l_tuple = self.marketplace_contract.listings(i)
                l_data = parse_listing_tuple(l_tuple)
                if l_data and l_data.status == 0: 
                    active_listing_tokens.add(l_data.token_id)

            for land_id in owned_land_ids:
                land_tuple = self.land_registry_contract.land_parcels(land_id)
                land_data = parse_land_parcel_tuple(land_tuple)
                
                if land_data and land_data.status == 1:
                    is_selling = land_id in active_listing_tokens
                    item_widget = LandListItemWidget(land_data, is_selling)
                    item_widget.sell_requested.connect(self.handle_sell_request)
                    
                    list_item = QListWidgetItem(self.land_list_widget)
                    list_item.setSizeHint(item_widget.sizeHint())
                    self.land_list_widget.addItem(list_item)
                    self.land_list_widget.setItemWidget(list_item, item_widget)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tải tài sản: {e}")
            
    def handle_sell_request(self, token_id):
        print(f"Bắt đầu quy trình bán cho token #{token_id}")
        
        try:
            dialog = SellDialog(token_id, self)
            if dialog.exec(): 
                price = dialog.get_price()
                price_in_eth = price / 10**18
                if price is None:
                    QMessageBox.warning(self, "Thông tin không hợp lệ", "Vui lòng nhập giá bán hợp lệ.")
                    return
                
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
                    
                    print(f" -> Gửi giao dịch approve cho token #{token_id}...")
                    self.setCursor(Qt.WaitCursor)
                    approve_receipt = self.land_nft_contract.approve(
                        marketplace_addr,
                        token_id,
                        sender=self.user_account
                    )
                    self.unsetCursor()
                    print(" -> Approve thành công.")

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

                print(f" -> Bước 3: Gửi giao dịch create_listing với CCCD tự động: {seller_cccd}")
                listing_fee = self.marketplace_contract.listing_fee()
                
                receipt = self.marketplace_contract.create_listing(
                    token_id,
                    seller_cccd,
                    price,
                    sender=self.user_account,
                    value=listing_fee
                )
                self.unsetCursor()

                QMessageBox.information(self, "Thành công", f"Đã đăng bán bất động sản #{token_id} thành công!\nTx: {getattr(receipt, 'txn_hash', 'N/A')}")
                self.populate_my_lands() 
            else:
                print(" -> Người dùng đã hủy đăng bán.")

        except Exception as e:
            self.unsetCursor()
            QMessageBox.critical(self, "Lỗi", f"Một lỗi đã xảy ra: {e}")

class RegisterLandTab(QWidget): 
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
        
        self.pdf_uri_input = QLineEdit()
        self.pdf_uri_input.setReadOnly(True)
        self.pdf_uri_input.setPlaceholderText("URI của file PDF sẽ hiện ở đây sau khi upload")
        pdf_upload_button = QPushButton("Upload PDF...")
        pdf_upload_button.clicked.connect(self.upload_pdf)
        
        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(self.pdf_uri_input)
        pdf_layout.addWidget(pdf_upload_button)

        self.image_uri_input = QLineEdit()
        self.image_uri_input.setReadOnly(True)
        self.image_uri_input.setPlaceholderText("URI của file ảnh sẽ hiện ở đây sau khi upload")
        image_upload_button = QPushButton("Upload Hình ảnh...")
        image_upload_button.clicked.connect(self.upload_image)

        image_layout = QHBoxLayout()
        image_layout.addWidget(self.image_uri_input)
        image_layout.addWidget(image_upload_button)
        
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
        self.history_table.setMinimumHeight(150) 
        
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_group)

        self.populate_history()
        layout.addStretch(1) 

    def _clear_form(self):
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
            self._clear_form()
            self.populate_history() 
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Gửi hồ sơ thất bại: {e}")
    
    def populate_history(self):
        self.history_table.setRowCount(0)
        try:
            my_land_ids = self.land_registry_contract.get_lands_by_owner(self.user_account)
            
            self.history_table.setRowCount(len(my_land_ids))
            
            for row, land_id in enumerate(my_land_ids):
                land_tuple = self.land_registry_contract.land_parcels(land_id)
                land_data = parse_land_parcel_tuple(land_tuple)
                
                if land_data:
                    self.history_table.setItem(row, 0, QTableWidgetItem(str(land_data.id)))
                    self.history_table.setItem(row, 1, QTableWidgetItem(land_data.land_address))
                    self.history_table.setItem(row, 2, QTableWidgetItem("-")) 
                    
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
# ADMIN TABS
# =============================================================================

class LandRegistryTab(QWidget):
    def __init__(self, admin_account, land_registry_contract):
        super().__init__()
        
        self.admin_account = admin_account
        self.land_registry_contract = land_registry_contract

        layout = QVBoxLayout(self)

        title = QLabel("Quản lý Hồ sơ Đăng ký Đất")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        self.refresh_button = QPushButton("Làm mới Danh sách")
        self.refresh_button.clicked.connect(self.populate_pending_lands)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignRight)

        self.pending_lands_table = QTableWidget()
        self.pending_lands_table.setColumnCount(5)
        self.pending_lands_table.setHorizontalHeaderLabels(["ID", "Ví Đăng ký", "CCCD", "Địa chỉ Đất", "Hành động"])
        self.pending_lands_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pending_lands_table.setEditTriggers(QTableWidget.NoEditTriggers) 
        layout.addWidget(self.pending_lands_table)
        
        self.populate_pending_lands()

    def populate_pending_lands(self):
        try:
            self.pending_lands_table.setRowCount(0)
            
            next_id = self.land_registry_contract.next_land_id()
            
            pending_requests = []
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
                process_button = QPushButton("Xem & Xử lý")
                process_button.clicked.connect(lambda checked, lid=land_id: self.show_detail_dialog(lid))
                self.pending_lands_table.setCellWidget(row, 4, process_button)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Blockchain", f"Không thể tải dữ liệu từ contract: {e}")

    def show_detail_dialog(self, land_id):
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
            next_tx_id = self.marketplace_contract.next_tx_id()
            pending_txs = []
            for i in range(1, next_tx_id):
                tx_tuple = self.marketplace_contract.transactions(i)
                if tx_tuple and tx_tuple[5] == 0: 
                    pending_txs.append(tx_tuple)
            
            self.transactions_table.setRowCount(len(pending_txs))

            for row, tx_tuple in enumerate(pending_txs):
                tx_id = tx_tuple[0]
                listing_id = tx_tuple[1]
                buyer_cccd_encrypted = tx_tuple[2]
                buyer_address = tx_tuple[3]
                amount_wei = tx_tuple[4]
                
                listing_tuple = self.marketplace_contract.listings(listing_id)
                listing_data = parse_listing_tuple(listing_tuple)
                
                buyer_cccd = decrypt_data(buyer_cccd_encrypted)
                token_id = listing_data.token_id
                seller_address = self.land_nft_contract.ownerOf(token_id)
                
                self.transactions_table.setItem(row, 0, QTableWidgetItem(str(tx_id)))
                self.transactions_table.setItem(row, 1, QTableWidgetItem(str(token_id)))
                self.transactions_table.setItem(row, 2, QTableWidgetItem(seller_address))
                self.transactions_table.setItem(row, 3, QTableWidgetItem(buyer_address))
                self.transactions_table.setItem(row, 4, QTableWidgetItem(buyer_cccd))
                self.transactions_table.setItem(row, 5, QTableWidgetItem(f"{amount_wei / 10**18:.4f}"))
                
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

class SystemConfigTab(QWidget):
    def __init__(self, admin_account, marketplace_contract, parent=None):
        super().__init__(parent)
        self.admin_account = admin_account
        self.marketplace_contract = marketplace_contract

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)

        fees_group = QGroupBox("Quản lý Phí Giao dịch")
        fees_layout = QFormLayout(fees_group)

        self.listing_fee_label = QLabel("<đang tải...>")
        self.listing_fee_label.setStyleSheet("font-style: italic;")
        fees_layout.addRow("<b>Phí Đăng tin (Listing Fee):</b>", self.listing_fee_label)

        self.cancel_penalty_label = QLabel("<đang tải...>")
        self.cancel_penalty_label.setStyleSheet("font-style: italic;")
        fees_layout.addRow("<b>Phí Phạt Hủy (Cancel Penalty):</b>", self.cancel_penalty_label)

        self.edit_fees_button = QPushButton("Chỉnh sửa Phí")
        self.edit_fees_button.clicked.connect(self.edit_fees)
        
        fees_layout.addRow("", self.edit_fees_button)

        main_layout.addWidget(fees_group)
        self.load_current_fees()

    def load_current_fees(self):
        try:
            listing_fee = self.marketplace_contract.listing_fee() / 10**18
            cancel_penalty = self.marketplace_contract.cancel_penalty() / 10**18
            
            self.listing_fee_label.setText(f"{listing_fee} ETH")
            self.cancel_penalty_label.setText(f"{cancel_penalty} ETH")
            
            self.listing_fee_label.setStyleSheet("font-style: normal; font-weight: bold;")
            self.cancel_penalty_label.setStyleSheet("font-style: normal; font-weight: bold;")

        except Exception as e:
            error_message = f"Lỗi: {e}"
            self.listing_fee_label.setText(error_message)
            self.cancel_penalty_label.setText(error_message)
            QMessageBox.critical(self, "Lỗi Blockchain", f"Không thể tải dữ liệu phí: {e}")

    def edit_fees(self):
        try:
            current_listing_fee = self.marketplace_contract.listing_fee() 
            current_cancel_penalty = self.marketplace_contract.cancel_penalty()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lấy giá trị phí hiện tại: {e}")
            return

        new_listing_fee_str, ok1 = QInputDialog.getText(
            self, 
            "Bước 1/2: Chỉnh sửa Phí Đăng tin", 
            "Nhập giá trị Phí Đăng tin mới (đơn vị Wei):",
            QLineEdit.Normal,
            str(current_listing_fee)
        )
        
        if ok1 and new_listing_fee_str is not None:
            new_cancel_penalty_str, ok2 = QInputDialog.getText(
                self,
                "Bước 2/2: Chỉnh sửa Phí Phạt Hủy",
                "Nhập giá trị Phí Phạt Hủy mới (đơn vị Wei):",
                QLineEdit.Normal,
                str(current_cancel_penalty)
            )

            if ok2 and new_cancel_penalty_str is not None:
                try:
                    new_listing_fee = int(new_listing_fee_str)
                    new_cancel_penalty = int(new_cancel_penalty_str)
                    
                    receipt = self.marketplace_contract.set_fees(
                        new_listing_fee,
                        new_cancel_penalty,
                        sender=self.admin_account
                    )
                    
                    tx_hash = getattr(receipt, 'txn_hash', 'N/A')
                    QMessageBox.information(self, "Thành công", f"Đã gửi giao dịch cập nhật phí!\nTx: {tx_hash}")
                    
                    self.load_current_fees()

                except ValueError:
                    QMessageBox.warning(self, "Dữ liệu không hợp lệ", "Vui lòng chỉ nhập số nguyên.")
                except Exception as e:
                    QMessageBox.critical(self, "Lỗi Giao dịch", f"Cập nhật phí thất bại: {e}")   

# =============================================================================
# SHARED TABS
# =============================================================================

class SettingsTab(QWidget):
    def __init__(self, user_account, main_window, parent=None): 
        super().__init__(parent)
        self.main_window = main_window 
        self.user_account = user_account
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        info_group = QWidget()
        info_layout = QFormLayout(info_group)
        
        # Địa chỉ
        address_label = QLabel(self.user_account.address)
        address_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addRow("<b>Địa chỉ ví:</b>", address_label)

        # Số dư
        try:
            balance_wei = self.user_account.balance
            balance_eth = balance_wei / 10**18
            balance_label = QLabel(f"{balance_eth:.4f} ETH")
            balance_label.setStyleSheet("color: green; font-weight: bold;")
        except:
            balance_label = QLabel("N/A")
        info_layout.addRow("<b>Số dư:</b>", balance_label)

        self.logout_button = QPushButton("Đăng xuất")
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

        if USE_MOCK_DATA:
            self.username_input.setPlaceholderText("Mock: admin / user_a / user_b")
        else:
            self.username_input.setPlaceholderText("Nhập Alias (Tên ví trong Ape)")

        form_layout.addRow("Alias/Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        main_layout.addLayout(form_layout)

        self.login_button = QPushButton("Đăng nhập")
        main_layout.addWidget(self.login_button, alignment=Qt.AlignCenter)
        self.login_button.clicked.connect(self.handle_login)
        self.setLayout(main_layout)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập Username/Alias.")
            return

        # --- LOGIC MOCK ---
        if USE_MOCK_DATA:
            if username == "admin":
                self.main_window.show_admin_ui(MockAccount(MOCK_ADMIN_ADDRESS))
            elif username in ["user_a", "user_b"]:
                addr = MOCK_USER_A_ADDRESS if username == "user_a" else MOCK_USER_B_ADDRESS
                self.main_window.show_customer_ui(MockAccount(addr))
            else:
                QMessageBox.warning(self, "Lỗi", "Username Mock không hợp lệ.")
            return

        # --- LOGIC REAL (APE) ---
        if not password:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập mật khẩu ví.")
            return

        try:
            print(f"Đang thử tải ví alias: {username}...")
            # 1. Load account từ keystore của Ape
            user_account = accounts.load(username)
            # 2. Unlock account
            user_account.set_autosign(True, passphrase=password)
            
            print(f" -> Đăng nhập thành công: {user_account.address}")
            
            # 3. Kiểm tra quyền Admin (so sánh với admin của contract Marketplace)
            # Lưu ý: Gọi contract thật
            admin_address = self.main_window.marketplace_contract.admin()
            
            if user_account.address.lower() == admin_address.lower():
                self.main_window.show_admin_ui(user_account)
            else:
                self.main_window.show_customer_ui(user_account)

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Đăng nhập", f"Không thể đăng nhập: {e}\n(Kiểm tra lại Alias và Mật khẩu)")

# =============================================================================
# CỬA SỔ CHÍNH
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real Estate Blockchain System")
        self.setGeometry(100, 100, 800, 600)
        
        # 1. KẾT NỐI BLOCKCHAIN
        self.connect_blockchain()

        # 2. SETUP UI
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        self.login_page = LoginWindow(self)
        self.admin_dashboard_page = QWidget() 
        self.user_dashboard_page = QWidget() 

        self.central_widget.addWidget(self.login_page)
        self.central_widget.addWidget(self.admin_dashboard_page)
        self.central_widget.addWidget(self.user_dashboard_page)
        
        self.current_user = None
        self.show_login_ui()

    def connect_blockchain(self):
        """Thiết lập kết nối Provider và khởi tạo Contract Objects"""
        if USE_MOCK_DATA:
            print("⚠️ Đang chạy chế độ MOCK DATA.")
            self.mock_registry = MockLandRegistry()
            self.mock_nft = MockLandNFT(self.mock_registry)
            self.mock_marketplace = MockMarketplace(MOCK_ADMIN_ADDRESS, self.mock_nft)
            
            # Gán vào biến chung để UI dùng
            self.land_registry_contract = self.mock_registry
            self.land_nft_contract = self.mock_nft
            self.marketplace_contract = self.mock_marketplace
        else:
            print(f"🔌 Đang kết nối tới Geth tại {NODE_URL}...")
            try:
                # Kết nối Provider
                self.provider_context = networks.ethereum.local.use_provider(NODE_URL)
                self.active_provider = self.provider_context.__enter__()
                print(f"✅ Kết nối thành công! Chain ID: {networks.active_provider.chain_id}")

                # Load Contracts bằng Ape Project
                # Lưu ý: Cần file JSON artifact (được tạo ra khi compile)
                # project.ContractName.at(address) tự động tìm ABI
                
                print("⏳ Đang tải Contracts...")
                self.land_nft_contract = project.LandNFT.at(LAND_NFT_ADDRESS)
                self.land_registry_contract = project.LandRegistry.at(LAND_REGISTRY_ADDRESS)
                self.marketplace_contract = project.Marketplace.at(MARKETPLACE_ADDRESS)
                
                print("✅ Đã tải xong 3 Contracts.")

            except Exception as e:
                error_msg = f"Lỗi kết nối Blockchain:\n{e}\n\nHãy đảm bảo Geth đang chạy và bạn đang ở đúng thư mục dự án Ape."
                print(error_msg)
                QMessageBox.critical(self, "Fatal Error", error_msg)
                # Fallback về Mock hoặc đóng app tùy logic
                sys.exit(1)

    def show_login_ui(self):
        self.central_widget.setCurrentWidget(self.login_page)

    def show_admin_ui(self, admin_account):
        # Tạo lại Dashboard để làm mới dữ liệu
        container = self.admin_dashboard_page
        if container.layout():
            QWidget().setLayout(container.layout()) # Hack để xóa layout cũ
            
        tabs = QTabWidget()
        
        # Truyền Contract thật (đã khởi tạo ở __init__) vào các Tab
        self.land_registry_tab = LandRegistryTab(admin_account, self.land_registry_contract)
        self.admin_transaction_tab = AdminTransactionTab(admin_account, self.marketplace_contract, self.land_nft_contract, self.land_registry_contract)
        self.config_tab = SystemConfigTab(admin_account, self.marketplace_contract)
        self.settings_tab = SettingsTab(admin_account, self) # Đã update
        
        tabs.addTab(self.land_registry_tab, "Land Registry")
        tabs.addTab(self.admin_transaction_tab, "Transactions")
        tabs.addTab(self.config_tab, "Config")
        tabs.addTab(self.settings_tab, "Settings")
        
        layout = QVBoxLayout(container)
        layout.addWidget(tabs)
        self.central_widget.setCurrentWidget(container)

    def show_customer_ui(self, user_account):
        container = self.user_dashboard_page
        if container.layout():
            QWidget().setLayout(container.layout())
            
        tabs = QTabWidget()
        
        self.register_tab = RegisterLandTab(user_account, self.land_registry_contract)
        self.marketplace_tab = MarketplaceTab(user_account, self.marketplace_contract, self.land_registry_contract, self.land_nft_contract)
        self.my_account_tab = MyLandTab(user_account, self.land_registry_contract, self.land_nft_contract, self.marketplace_contract)
        self.transaction_history_tab = MyTransactionsTab(user_account, self.marketplace_contract, self.land_registry_contract, self.land_nft_contract)
        self.settings_tab = SettingsTab(user_account, self)
        
        tabs.addTab(self.register_tab, "Register Land")
        tabs.addTab(self.marketplace_tab, "Marketplace")
        tabs.addTab(self.my_account_tab, "My Assets")
        tabs.addTab(self.transaction_history_tab, "History")
        tabs.addTab(self.settings_tab, "Settings")

        layout = QVBoxLayout(container)
        layout.addWidget(tabs)
        self.central_widget.setCurrentWidget(container)

    def handle_logout(self):
        self.current_user = None
        self.show_login_ui()

    def closeEvent(self, event):
        """Ngắt kết nối an toàn khi đóng App"""
        if hasattr(self, 'provider_context') and not USE_MOCK_DATA:
            print("Đang ngắt kết nối mạng...")
            self.provider_context.__exit__(None, None, None)
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()