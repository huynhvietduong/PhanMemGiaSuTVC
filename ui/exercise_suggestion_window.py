import os
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
class ExerciseSuggestionWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db = db_manager
        self.title("📘 Gợi ý bài tập theo điểm yếu")
        self.geometry("900x650")
        self.grab_set()

        ttk.Label(self, text="📌 Chọn học sinh để gợi ý bài tập", font=("Helvetica", 14, "bold")).pack(pady=10)

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="x")

        ttk.Label(frame, text="Học sinh:").grid(row=0, column=0, sticky="w")
        students = self.db.execute_query("SELECT id, name FROM students ORDER BY name", fetch='all') or []
        self.student_map = {f"{name} (ID {sid})": sid for sid, name in students}
        self.student_var = tk.StringVar()
        student_combo = ttk.Combobox(frame, textvariable=self.student_var, values=list(self.student_map.keys()),
                                     state="readonly", width=40)
        student_combo.grid(row=0, column=1, padx=10)
        student_combo.bind("<<ComboboxSelected>>", self.load_suggestions)

        self.suggestion_frame = ttk.Frame(self)
        self.suggestion_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def load_suggestions(self, event=None):
        for widget in self.suggestion_frame.winfo_children():
            widget.destroy()

        student_name = self.student_var.get()
        student_id = self.student_map.get(student_name)
        if not student_id: return

        # Tìm chủ đề yếu (AVG < 3)
        weak_topics = self.db.execute_query("""
            SELECT chu_de, ROUND(AVG(diem), 1)
            FROM student_skills
            WHERE student_id = ?
            GROUP BY chu_de
            HAVING AVG(diem) < 3
            ORDER BY AVG(diem) ASC
        """, (student_id,), fetch='all') or []

        if not weak_topics:
            ttk.Label(self.suggestion_frame, text="🎉 Học sinh không có chủ đề yếu!", foreground="green").pack()
            return

        for chu_de, avg in weak_topics:
            box = ttk.LabelFrame(self.suggestion_frame, text=f"📉 {chu_de} (Điểm TB: {avg})", padding=10)
            box.pack(fill="x", pady=5)

            rows = self.db.execute_query("SELECT ten_bai, loai_tap, noi_dung FROM exercises WHERE chu_de = ?",
                                         (chu_de,), fetch='all') or []
            if not rows:
                ttk.Label(box, text="(Chưa có bài tập nào trong chủ đề này)").pack()
                continue

            for ten_bai, loai_tap, noi_dung in rows:
                row = ttk.Frame(box)
                row.pack(fill="x", pady=5)

                ttk.Label(row, text=f"• {ten_bai}", width=30).pack(side="left", anchor="w")

                if loai_tap == "text":
                    text = tk.Text(row, height=3, width=60)
                    text.insert("1.0", noi_dung)
                    text.config(state="disabled")
                    text.pack(side="left", padx=5)
                elif loai_tap == "image":
                    img_path = noi_dung
                    if os.path.exists(img_path):
                        try:
                            img = Image.open(img_path)
                            img.thumbnail((200, 150))
                            photo = ImageTk.PhotoImage(img)
                            label = ttk.Label(row, image=photo)
                            label.image = photo
                            label.pack(side="left", padx=5)
                        except:
                            ttk.Label(row, text="[Không mở được ảnh]").pack(side="left", padx=5)
                    else:
                        ttk.Label(row, text="[File ảnh không tồn tại]").pack(side="left", padx=5)
                elif loai_tap in ["pdf", "word", "link"]:
                    def open_link(path=noi_dung):
                        if path.startswith("http"):
                            webbrowser.open(path)
                        else:
                            full_path = os.path.abspath(path)
                            if os.path.exists(full_path):
                                os.startfile(full_path)
                            else:
                                messagebox.showerror("Lỗi", f"Không tìm thấy file: {path}")

                    ttk.Button(row, text="📂 Mở bài tập", command=open_link).pack(side="left", padx=5)
