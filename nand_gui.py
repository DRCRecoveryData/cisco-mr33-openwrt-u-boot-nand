import os
import sys
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# Constants matching hardware block definitions
BLOCK_SIZE = 135168  # 0x21000
EXPECTED_SIZE = 138412032  # 0x8400000

class InjectorWorker(QThread):
    """Asynchronous background worker to perform IO-heavy operations without blocking the UI."""
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, infile, outfile):
        super().__init__()
        self.infile = infile
        self.outfile = outfile

    def write_binary_section(self, target_file, source_file, seek_blocks):
        if not os.path.exists(source_file):
            raise FileNotFoundError(f"Required component binary missing: {source_file}")
            
        offset = BLOCK_SIZE * seek_blocks
        self.log.emit(f"Injecting {source_file} at block {seek_blocks} (Offset: {hex(offset)})...")
        
        with open(source_file, 'rb') as sf:
            data = sf.read()
        with open(target_file, 'r+b') as tf:
            tf.seek(offset)
            tf.write(data)

    def run(self):
        try:
            self.progress.emit(10)
            if not os.path.exists(self.infile):
                self.error.emit("Source image missing!")
                return
            if os.path.abspath(self.infile) == os.path.abspath(self.outfile):
                self.error.emit("Source equals target. Cannot overwrite original dump file!")
                return
            if os.path.exists(self.outfile):
                self.error.emit("Target file already exists. Refusing to overwrite!")
                return
            if os.path.getsize(self.infile) != EXPECTED_SIZE:
                self.error.emit("Source dump has invalid size. Verification failed (Dump may lack OOB data).")
                return

            # Execute safe file clone
            self.progress.emit(30)
            self.log.emit(f"Cloning raw NAND image to {os.path.basename(self.outfile)}...")
            shutil.copyfile(self.infile, self.outfile)

            # Patch Bootloader stage
            self.progress.emit(60)
            self.write_binary_section(self.outfile, "ubootmr332012.bin", seek_blocks=56)
            
            # Patch OpenWrt environment system
            self.progress.emit(85)
            self.write_binary_section(self.outfile, "ubimr33.bin", seek_blocks=96)

            self.progress.emit(100)
            self.log.emit("🎉 Recovery image structured successfully!")
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


class BinaryInjectorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.check_required_binaries()

    def init_ui(self):
        # Set dynamic, informative window title matching your project scope
        self.setWindowTitle("Cisco Meraki MR33 – OpenWrt NAND Recovery Suite")
        self.setMinimumSize(620, 460)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(14)

        # High-visibility dark modern layout palette (Catppuccin inspired)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; font-size: 13px; font-weight: bold; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px; font-family: 'Segoe UI', Arial; }
            QPushButton { background-color: #89b4fa; color: #11111b; font-weight: bold; border-radius: 4px; padding: 6px 14px; }
            QPushButton:hover { background-color: #b4befe; }
            QPushButton:disabled { background-color: #585b70; color: #7f849c; }
            QProgressBar { border: 1px solid #45475a; border-radius: 4px; text-align: center; color: #11111b; font-weight: bold; background-color: #313244;}
            QProgressBar::chunk { background-color: #a6e3a1; }
            QTextEdit { background-color: #181825; color: #a6e3a1; font-family: 'Consolas', 'Courier New'; border: 1px solid #45475a; border-radius: 4px; padding: 5px; }
        """)

        # Raw NAND Input Selection
        input_layout = QHBoxLayout()
        self.lbl_infile = QLabel("Source NAND:")
        self.lbl_infile.setFixedWidth(100)
        self.txt_infile = QLineEdit()
        self.txt_infile.setPlaceholderText("Select raw dump image file (.bin)...")
        self.btn_browse_in = QPushButton("Browse")
        self.btn_browse_in.clicked.connect(self.browse_infile)
        input_layout.addWidget(self.lbl_infile)
        input_layout.addWidget(self.txt_infile)
        input_layout.addWidget(self.btn_browse_in)
        main_layout.addLayout(input_layout)

        # Output Target Path Selection
        output_layout = QHBoxLayout()
        self.lbl_outfile = QLabel("Target Image:")
        self.lbl_outfile.setFixedWidth(100)
        self.txt_outfile = QLineEdit()
        self.txt_outfile.setPlaceholderText("Auto-generated recovery file destination...")
        self.btn_browse_out = QPushButton("Browse")
        self.btn_browse_out.clicked.connect(self.browse_outfile)
        output_layout.addWidget(self.lbl_outfile)
        output_layout.addWidget(self.txt_outfile)
        output_layout.addWidget(self.btn_browse_out)
        main_layout.addLayout(output_layout)

        # Operational Sub-Actions 
        actions_layout = QHBoxLayout()
        self.btn_run = QPushButton("⚡ Inject U-Boot & OpenWrt Assets")
        self.btn_run.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.btn_run.clicked.connect(self.start_injection)
        
        self.btn_open_folder = QPushButton("📁 Open Output Directory")
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.setFixedWidth(180)
        self.btn_open_folder.clicked.connect(self.open_target_folder)
        
        actions_layout.addWidget(self.btn_run)
        actions_layout.addWidget(self.btn_open_folder)
        main_layout.addLayout(actions_layout)

        # Status Tracker
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Output Log Window
        main_layout.addWidget(QLabel("Process Output Log:"))
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        main_layout.addWidget(self.log_window)

    def check_required_binaries(self):
        """Verifies integrity of directory dependencies before activating system processes."""
        missing = []
        if not os.path.exists("ubootmr332012.bin"):
            missing.append("ubootmr332012.bin")
        if not os.path.exists("ubimr33.bin"):
            missing.append("ubimr33.bin")

        if missing:
            self.btn_run.setEnabled(False)
            self.log_window.clear()
            self.log_window.append("<span style='color: #f38ba8;'>⚠️ CRITICAL ERROR: Environment assets missing from executing folder:</span>")
            for item in missing:
                self.log_window.append(f"<span style='color: #f38ba8;'>  - Missing asset file: {item}</span>")
        else:
            self.btn_run.setEnabled(True)
            self.log_window.clear()
            self.log_window.append("<span style='color: #a6e3a1;'>✔️ Recovery dependencies confirmed. System primed and ready.</span>")

    def browse_infile(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Raw MR33 NAND Flash File", "", "Binary Files (*.bin);;All Files (*)")
        if file_path:
            self.txt_infile.setText(file_path)
            
            # Cleanly append suffix without causing double extensions like '.bin_Patched.bin'
            base, ext = os.path.splitext(file_path)
            auto_target_path = f"{base}_Patched{ext}"
            self.txt_outfile.setText(auto_target_path)

    def browse_outfile(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Specify Modified Target Output Destination", self.txt_outfile.text(), "Binary Files (*.bin);;All Files (*)")
        if file_path:
            self.txt_outfile.setText(file_path)

    def start_injection(self):
        infile = self.txt_infile.text().strip()
        outfile = self.txt_outfile.text().strip()

        if not infile or not outfile:
            self.log_window.append("<span style='color: #f38ba8;'>[Error] Absolute filepath routing inputs are missing.</span>")
            return

        # UI State Lockout during processing 
        self.btn_run.setEnabled(False)
        self.btn_browse_in.setEnabled(False)
        self.btn_browse_out.setEnabled(False)
        self.btn_open_folder.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_window.clear()
        
        self.log_window.append("Initialising flash injection sequencing...")

        # Run background worker
        self.worker = InjectorWorker(infile, outfile)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_window.append)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.handle_finished)
        self.worker.start()

    def handle_error(self, message):
        self.log_window.append(f"<span style='color: #f38ba8;'>[Fault] {message}</span>")
        self.reset_ui_elements()

    def handle_finished(self):
        self.btn_open_folder.setEnabled(True)
        self.reset_ui_elements()

    def reset_ui_elements(self):
        self.btn_browse_in.setEnabled(True)
        self.btn_browse_out.setEnabled(True)
        self.check_required_binaries()

    def open_target_folder(self):
        outfile = self.txt_outfile.text().strip()
        if outfile:
            folder = os.path.dirname(os.path.abspath(outfile))
            if os.path.exists(folder):
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    os.system(f'open "{folder}"')
                else:
                    os.system(f'xdg-open "{folder}"')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = BinaryInjectorGUI()
    gui.show()
    sys.exit(app.exec())
