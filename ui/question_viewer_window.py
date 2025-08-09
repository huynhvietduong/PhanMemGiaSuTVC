import os
import json
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
class QuestionViewerWindow(tk.Toplevel):
    def __init__(self, parent, question_data):
        super().__init__(parent)
        self.title(f"Xem trước câu hỏi #{question_data['id']} - {question_data['chu_de']}")
        self.geometry("600x800")
        self.grab_set()
        self._image_references = []

        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 👉 Tiêu đề nội dung
        ttk.Label(scrollable_frame, text="Nội dung câu hỏi:", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=5)

        content_shown = False
        content_image = question_data.get("content_image")
        if content_image and os.path.exists(content_image):
            self.add_image_to_frame(scrollable_frame, content_image)
            content_shown = True

        content_text = question_data.get("content_text")
        if not content_shown and content_text:
            ttk.Label(scrollable_frame, text=content_text, wraplength=550, justify="left", font=("Helvetica", 11)).pack(anchor="w", padx=10)
            content_shown = True

        if not content_shown:
            ttk.Label(scrollable_frame, text="(Không có nội dung câu hỏi)").pack(anchor="w", padx=10)

        ttk.Separator(scrollable_frame).pack(fill="x", pady=10)

        # 👉 Hiển thị các phương án
        ttk.Label(scrollable_frame, text="Các phương án:", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=10, pady=5)

        if question_data.get("options"):
            try:
                options = json.loads(question_data["options"])
                option_labels = ["A", "B", "C", "D", "E"]
                for i, opt in enumerate(options):
                    opt_frame = ttk.Frame(scrollable_frame)
                    opt_frame.pack(fill="x", padx=10, pady=5)
                    label_text = f"{option_labels[i]}."
                    if opt.get("is_correct"):
                        label_text += " (Đáp án đúng ✅)"
                    ttk.Label(opt_frame, text=label_text,
                              font=("Helvetica", 10, "bold" if opt.get("is_correct") else "normal")).pack(anchor="w")

                    if opt.get("image_path") and os.path.exists(opt["image_path"]):
                        self.add_image_to_frame(opt_frame, opt["image_path"])
                    elif opt.get("text"):
                        ttk.Label(opt_frame, text=opt["text"], wraplength=500, justify="left").pack(anchor="w", padx=10)
                    else:
                        ttk.Label(opt_frame, text="(Không có nội dung phương án)").pack(anchor="w", padx=10)
            except (json.JSONDecodeError, IndexError):
                ttk.Label(scrollable_frame, text="(Lỗi dữ liệu phương án)").pack(anchor="w", padx=10)

    def add_image_to_frame(self, frame, image_path):
        try:
            with Image.open(image_path) as img:
                max_width = 550
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                img_label = ttk.Label(frame, image=photo)
                img_label.image = photo
                self._image_references.append(photo)
                img_label.pack(anchor="w", padx=10)
        except Exception as e:
            ttk.Label(frame, text=f"(Lỗi tải ảnh: {e})").pack(anchor="w", padx=10)