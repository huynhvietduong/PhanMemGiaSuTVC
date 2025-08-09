import os
import json
import tkinter as tk
import unicodedata
import re
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from tkinter import ttk, filedialog, messagebox
from fpdf import FPDF
from database import DatabaseManager
def safe_multicell(pdf, w, h, txt, **kwargs):
    try:
        safe_multicell(w, h, txt, **kwargs)
    except Exception as e:
        fallback = ''.join(c if ord(c) < 128 else '?' for c in txt)
        safe_multicell(w, h, fallback, **kwargs)

class CreateTestWindow(tk.Toplevel):
    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent)
        self.title("Tạo Đề thi từ Ngân hàng câu hỏi")
        self.geometry("1100x700")
        self.db = db
        self.parent = parent

        main_frame = ttk.Frame(self, padding=10);
        main_frame.pack(fill="both", expand=True)
        left_panel = ttk.Frame(main_frame);
        left_panel.pack(side="left", fill="both", expand=True, padx=5)

        filter_frame = ttk.LabelFrame(left_panel, text="Bộ lọc câu hỏi");
        filter_frame.pack(fill="x", pady=5)
        ttk.Label(filter_frame, text="Chủ đề:").grid(row=0, column=0, padx=5)
        self.subject_var = tk.StringVar()
        self.subject_combo = ttk.Combobox(filter_frame, textvariable=self.subject_var, state="readonly")
        self.subject_combo.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(filter_frame, text="Độ khó:").grid(row=0, column=2, padx=5)
        self.difficulty_var = tk.StringVar()
        self.difficulty_combo = ttk.Combobox(filter_frame, textvariable=self.difficulty_var,
                                             values=["", "1", "2", "3", "4", "5"], width=5)
        self.difficulty_combo.grid(row=0, column=3, padx=5, pady=5)
        ttk.Button(filter_frame, text="Lọc", command=self.apply_filter).grid(row=0, column=4, padx=10)

        available_frame = ttk.LabelFrame(left_panel, text="Câu hỏi có sẵn");
        available_frame.pack(fill="both", expand=True)
        self.available_tree = ttk.Treeview(available_frame, columns=("id", "chu_de", "do_kho"), show="headings")
        self.available_tree.heading("id", text="ID");
        self.available_tree.column("id", width=50)
        self.available_tree.heading("chu_de", text="Chủ đề")
        self.available_tree.heading("do_kho", text="Độ khó");
        self.available_tree.column("do_kho", width=60)
        self.available_tree.pack(fill="both", expand=True, padx=5, pady=5)

        mid_panel = ttk.Frame(main_frame);
        mid_panel.pack(side="left", fill="y", padx=5)
        ttk.Button(mid_panel, text=">>", command=self.add_question).pack(pady=10)
        ttk.Button(mid_panel, text="<<", command=self.remove_question).pack(pady=10)

        right_panel = ttk.Frame(main_frame);
        right_panel.pack(side="left", fill="both", expand=True, padx=5)
        test_info_frame = ttk.LabelFrame(right_panel, text="Thông tin đề thi");
        test_info_frame.pack(fill="x", pady=5)
        ttk.Label(test_info_frame, text="Tiêu đề:").grid(row=0, column=0, sticky="w", padx=5)
        self.title_var = tk.StringVar(value="BÀI KIỂM TRA")
        ttk.Entry(test_info_frame, textvariable=self.title_var, width=50).grid(row=0, column=1, sticky="ew", padx=5,
                                                                               pady=2)
        ttk.Label(test_info_frame, text="Thời gian:").grid(row=1, column=0, sticky="w", padx=5)
        self.time_var = tk.StringVar(value="45 phút")
        ttk.Entry(test_info_frame, textvariable=self.time_var).grid(row=1, column=1, sticky="w", padx=5, pady=2)

        selected_frame = ttk.LabelFrame(right_panel, text="Câu hỏi đã chọn");
        selected_frame.pack(fill="both", expand=True)
        self.selected_tree = ttk.Treeview(selected_frame, columns=("id", "chu_de"), show="headings")
        self.selected_tree.heading("id", text="ID");
        self.selected_tree.column("id", width=50)
        self.selected_tree.heading("chu_de", text="Chủ đề")
        self.selected_tree.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Button(right_panel, text="TẠO VÀ XUẤT FILE PDF", command=self.generate_pdf).pack(pady=10, fill="x")
        self.load_subjects();
        self.apply_filter()

    def load_subjects(self):
        subjects = self.db.execute_query("SELECT DISTINCT chu_de FROM question_bank ORDER BY chu_de", fetch='all')
        subject_list = [""] + [row['chu_de'] for row in subjects or []]
        self.subject_combo['values'] = subject_list

    def apply_filter(self):
        for i in self.available_tree.get_children(): self.available_tree.delete(i)
        query = "SELECT id, chu_de, do_kho FROM question_bank WHERE 1=1"
        params = []
        if self.subject_var.get():
            query += " AND chu_de = ?";
            params.append(self.subject_var.get())
        if self.difficulty_var.get():
            query += " AND do_kho = ?";
            params.append(int(self.difficulty_var.get()))
        query += " ORDER BY id DESC"
        rows = self.db.execute_query(query, params, fetch='all')
        for row in rows or []:
            self.available_tree.insert("", "end", values=(row['id'], row['chu_de'], row['do_kho']))

    def add_question(self):
        selected_items = self.available_tree.selection()
        for item in selected_items:
            values = self.available_tree.item(item, 'values')
            if not self.selected_tree.exists(values[0]):
                self.selected_tree.insert("", "end", iid=values[0], values=values)

    def remove_question(self):
        for item in self.selected_tree.selection():
            self.selected_tree.delete(item)

    def generate_pdf(self):
        question_ids = self.selected_tree.get_children()
        if not question_ids:
            messagebox.showwarning("Thông báo", "Chưa có câu hỏi nào trong đề thi.", parent=self)
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")],
            title="Lưu file đề thi"
        )
        if not save_path:
            return

        try:
            # 1. Xác định thư mục gốc và load font DejaVu
            ui_dir = os.path.dirname(os.path.abspath(__file__))  # .../ui
            project_dir = os.path.dirname(ui_dir)  # .../PhanMemGiaSuTVC
            font_dir = os.path.join(project_dir, "assets", "fonts")
            font_reg = os.path.join(font_dir, "DejaVuSans.ttf")
            font_bold = os.path.join(font_dir, "DejaVuSans-Bold.ttf")
            if not (os.path.exists(font_reg) and os.path.exists(font_bold)):
                messagebox.showerror("Lỗi", f"Không tìm thấy font tại:\n{font_dir}", parent=self)
                return

            pdfmetrics.registerFont(TTFont("DejaVu", font_reg))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", font_bold))

            # 2. Khởi tạo ReportLab document
            doc = SimpleDocTemplate(
                save_path, pagesize=A4,
                rightMargin=40, leftMargin=40,
                topMargin=60, bottomMargin=40
            )
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name="ExamTitle",
                fontName="DejaVu-Bold",
                fontSize=18,
                alignment=1,
                spaceAfter=12
            ))
            styles.add(ParagraphStyle(
                name="Normal_DejaVu",
                fontName="DejaVu",
                fontSize=12,
                leading=15
            ))
            styles.add(ParagraphStyle(
                name="QuestionNum",
                fontName="DejaVu-Bold",
                fontSize=12,
                spaceBefore=8,
                leading=14
            ))

            flowables = []

            # 3. Tiêu đề đề thi & thời gian
            flowables.append(Paragraph(self.title_var.get(), styles["ExamTitle"]))
            flowables.append(Paragraph(f"Thời gian làm bài: {self.time_var.get()}", styles["Normal_DejaVu"]))
            flowables.append(Spacer(1, 12))

            answer_key = []

            # 4. Lặp qua các câu đã chọn
            for idx, qid in enumerate(question_ids, start=1):
                row = self.db.execute_query(
                    "SELECT * FROM question_bank WHERE id=?", (qid,), fetch="one"
                )
                if not row:
                    continue

                # Nội dung câu hỏi
                content_text = row["content_text"] or ""
                content_img = row["content_image"] or ""
                if content_text.strip():
                    # Bỏ bất kỳ prefix dạng "Câu <số>:" nếu có
                    body = re.sub(r"^Câu\s*\d+\s*:\s*", "", content_text).strip()
                    flowables.append(
                        Paragraph(
                            f'<b>Câu {idx}:</b> {body}',
                            styles["Normal_DejaVu"]
                        )
                    )
                    flowables.append(Spacer(1, 6))
                elif content_img and os.path.exists(content_img):
                    flowables.append(Image(content_img, width=400, height=0))

                # Phương án
                opts = json.loads(row["options"] or "[]")
                table_data = []
                labels = ["A", "B", "C", "D", "E"]
                for j, opt in enumerate(opts):
                    lbl = labels[j]
                    txt = (opt.get("text") or "").strip()
                    img = opt.get("image_path") or ""

                    cell_label = Paragraph(f"<b>{lbl}.</b>", styles["Normal_DejaVu"])
                    if txt:
                        cell_content = Paragraph(txt, styles["Normal_DejaVu"])
                    elif img and os.path.exists(img):
                        cell_content = Image(img, width=200, height=0)
                    else:
                        cell_content = Paragraph("(Không có nội dung)", styles["Normal_DejaVu"])

                    table_data.append([cell_label, cell_content])
                    if opt.get("is_correct"):
                        answer_key.append((idx, lbl))

                tbl = Table(table_data, colWidths=[20, 420])
                tbl.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]))
                flowables.append(tbl)
                flowables.append(Spacer(1, 12))

            # 5. Trang ĐÁP ÁN
            flowables.append(PageBreak())
            flowables.append(Paragraph("ĐÁP ÁN", styles["ExamTitle"]))

            ans_cells = [
                Paragraph(f"{num}-{lbl}", styles["Normal_DejaVu"])
                for num, lbl in answer_key
            ]
            ans_rows = [ans_cells[i:i + 5] for i in range(0, len(ans_cells), 5)]
            ans_tbl = Table(ans_rows, colWidths=[80] * 5)
            ans_tbl.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            flowables.append(ans_tbl)

            # 6. Build và mở PDF
            doc.build(flowables)
            messagebox.showinfo(
                "Thành công",
                f"Đã xuất file PDF thành công tại:\n{save_path}",
                parent=self
            )
            os.startfile(save_path)

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tạo file PDF:\n{e}", parent=self)