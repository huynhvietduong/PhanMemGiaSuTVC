import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab
import tempfile
from pdf2image import convert_from_path
import comtypes.client  # ← dùng MS Word
class ImageEntry(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, relief="solid", borderwidth=1)
        self.image_path = None
        self.photo_image = None

        self.label = ttk.Label(self, text="(Chưa có ảnh)", anchor="center", justify="center")
        self.label.pack(fill="both", expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Dán", command=self.paste_from_clipboard).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_frame, text="Chọn tệp", command=self.choose_file).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_frame, text="Xóa", command=self.clear_image).pack(side="left", expand=True, fill="x")
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Dán", command=self.paste_from_clipboard).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_frame, text="Chọn ảnh", command=self.choose_file).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_frame, text="📄 Tải từ Word", command=self.load_from_word).pack(side="left", expand=True,
                                                                                      fill="x")
        ttk.Button(btn_frame, text="Xóa", command=self.clear_image).pack(side="left", expand=True, fill="x")

    def _save_image_data(self, img_data: Image.Image):
        if not img_data: return None
        save_dir = "question_images"
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{int(time.time() * 1000)}.png"
        full_path = os.path.join(save_dir, filename)
        img_data.save(full_path, "PNG")
        return full_path

    def paste_from_clipboard(self):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                saved_path = self._save_image_data(img)
                self.set_image(saved_path)
            else:
                messagebox.showwarning("Thông báo", "Không tìm thấy dữ liệu hình ảnh trong Clipboard.", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể dán ảnh: {e}", parent=self)

    def choose_file(self):
        filepath = filedialog.askopenfilename(title="Chọn file ảnh",
                                              filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
        if filepath:
            try:
                with Image.open(filepath) as img:
                    img_copy = img.copy()
                saved_path = self._save_image_data(img_copy)
                self.set_image(saved_path)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở file ảnh: {e}", parent=self)

    def set_image(self, image_path, size=(120, 90)):
        self.image_path = image_path
        if image_path and os.path.exists(image_path):
            try:
                with Image.open(image_path) as img:
                    img.thumbnail(size)
                    self.photo_image = ImageTk.PhotoImage(img)
                    self.label.config(image=self.photo_image, text="")
            except Exception:
                self.label.config(image=None, text="Lỗi ảnh")
        else:
            self.clear_image()

    def clear_image(self):
        self.image_path = None
        self.label.config(image=None, text="(Chưa có ảnh)")

    def get_image_path(self):
        return self.image_path

    def load_from_word(self):
        file_path = filedialog.askopenfilename(filetypes=[("Word files", "*.docx")], title="Chọn file Word")
        if not file_path:
            return

        try:
            # 1. Dùng Word chuyển sang PDF
            word = comtypes.client.CreateObject('Word.Application')
            word.Visible = False
            doc = word.Documents.Open(file_path)
            temp_pdf = os.path.join(tempfile.gettempdir(), f"{int(time.time())}.pdf")
            doc.SaveAs(temp_pdf, FileFormat=17)  # wdFormatPDF
            doc.Close()
            word.Quit()

            # 2. Dùng pdf2image chuyển PDF thành ảnh
            poppler_path = r"C:\poppler-xx\Library\bin"  # ❗ thay đường dẫn này bằng poppler trên máy bạn
            images = convert_from_path(temp_pdf, poppler_path=poppler_path)

            if images:
                saved_path = self._save_image_data(images[0])
                self.set_image(saved_path)
            else:
                messagebox.showerror("Lỗi", "Không thể chuyển file Word thành ảnh.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xử lý file Word: {e}", parent=self)
