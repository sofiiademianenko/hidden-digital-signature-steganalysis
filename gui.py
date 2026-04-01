from __future__ import annotations
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from pathlib import Path
from PIL import Image, ImageTk
from key_manager import (
    generate_key_pair,
    save_private_key,
    save_public_key,
    load_private_key,
    load_public_key,
)
from signer import create_signature_package
from lsb_steganography import embed_signature_bits
from verifier import verify_document_signature
from utils import validate_supported_document, build_signed_output_path, is_supported_image

class HiddenEPApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Система прихованого електронного підпису")
        self.root.geometry("860x620")
        self.root.minsize(820, 580)
        self.selected_file = tk.StringVar()
        self.password_var = tk.StringVar(value="123456")
        self.channels_var = tk.IntVar(value=3)
        self.private_key_path = Path("keys/private_key.pem")
        self.public_key_path = Path("keys/public_key.pem")
        self.output_dir = Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_original_file: Path | None = None
        self.last_signed_file: Path | None = None

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self) -> None:
        style = ttk.Style()

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.configure(bg="#f7f7f7")

        style.configure("TFrame", background="#f7f7f7")
        style.configure("TLabelframe", background="#f7f7f7", borderwidth=1, relief="solid")
        style.configure(
            "TLabelframe.Label",
            background="#f7f7f7",
            foreground="#222222",
            font=("Arial", 12, "bold")
        )
        style.configure(
            "TLabel",
            background="#f7f7f7",
            foreground="#222222",
            font=("Arial", 11)
        )
        style.configure(
            "Title.TLabel",
            background="#f7f7f7",
            foreground="#1f1f1f",
            font=("Arial", 20, "bold")
        )
        style.configure("TButton", font=("Arial", 11), padding=(12, 8))
        style.configure("Action.TButton", font=("Arial", 11, "bold"), padding=(14, 10))
        style.configure("TEntry", padding=6, font=("Arial", 11))
        style.configure("TSpinbox", arrowsize=14)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        title_label = ttk.Label(
            main,
            text="Система прихованого електронного підпису",
            style="Title.TLabel",
            anchor="center"
        )
        title_label.pack(fill="x", pady=(0, 18))

        file_frame = ttk.LabelFrame(main, text="Вибір документа", padding=14)
        file_frame.pack(fill="x", pady=(0, 12))

        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x")

        file_entry = ttk.Entry(file_row, textvariable=self.selected_file)
        file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_button = ttk.Button(file_row, text="Огляд...", command=self.browse_file)
        browse_button.pack(side="right")

        settings_frame = ttk.LabelFrame(main, text="Параметри", padding=14)
        settings_frame.pack(fill="x", pady=(0, 12))

        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(anchor="w")

        ttk.Label(
            settings_grid,
            text="Пароль до приватного ключа:"
        ).grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 10))

        password_entry = ttk.Entry(
            settings_grid,
            textvariable=self.password_var,
            show="*",
            width=28
        )
        password_entry.grid(row=0, column=1, sticky="w", pady=(0, 10))

        ttk.Label(
            settings_grid,
            text="Кількість RGB-каналів для LSB:"
        ).grid(row=1, column=0, sticky="w", padx=(0, 12))

        channels_spinbox = ttk.Spinbox(
            settings_grid,
            from_=1,
            to=3,
            textvariable=self.channels_var,
            width=5
        )
        channels_spinbox.grid(row=1, column=1, sticky="w")

        buttons_frame = ttk.LabelFrame(main, text="Операції", padding=14)
        buttons_frame.pack(fill="x", pady=(0, 12))

        buttons_row = ttk.Frame(buttons_frame)
        buttons_row.pack(fill="x")

        for i in range(4):
            buttons_row.columnconfigure(i, weight=1)

        ttk.Button(
            buttons_row,
            text="Згенерувати ключі",
            command=self.generate_keys,
            style="Action.TButton"
        ).grid(row=0, column=0, padx=6, sticky="ew")

        ttk.Button(
            buttons_row,
            text="Підписати документ",
            command=self.sign_document,
            style="Action.TButton"
        ).grid(row=0, column=1, padx=6, sticky="ew")

        ttk.Button(
            buttons_row,
            text="Перевірити підпис",
            command=self.verify_document,
            style="Action.TButton"
        ).grid(row=0, column=2, padx=6, sticky="ew")

        ttk.Button(
            buttons_row,
            text="Порівняти зображення",
            command=self.compare_images_window,
            style="Action.TButton"
        ).grid(row=0, column=3, padx=6, sticky="ew")

        output_frame = ttk.LabelFrame(main, text="Результат", padding=10)
        output_frame.pack(fill="both", expand=True)

        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            font=("Courier New", 11),
            bg="#ffffff",
            fg="#222222",
            insertbackground="#222222",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=10
        )
        self.output_text.pack(fill="both", expand=True)

    def log(self, message: str) -> None:
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def browse_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Оберіть документ",
            filetypes=[
                ("Підтримувані файли", "*.docx *.png *.jpg *.jpeg"),
                ("DOCX", "*.docx"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Усі файли", "*.*"),
            ]
        )
        if file_path:
            self.selected_file.set(file_path)
            self.log(f"Обрано файл: {file_path}")

    def generate_keys(self) -> None:
        try:
            password = self.password_var.get().strip() or None

            private_key, public_key = generate_key_pair()
            self.private_key_path.parent.mkdir(parents=True, exist_ok=True)

            save_private_key(private_key, str(self.private_key_path), password=password)
            save_public_key(public_key, str(self.public_key_path))

            self.log("Ключі успішно згенеровано.")
            self.log(f"Приватний ключ: {self.private_key_path}")
            self.log(f"Відкритий ключ: {self.public_key_path}")
            self.log("-" * 70)

            messagebox.showinfo("Успіх", "Ключі успішно згенеровано.")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося згенерувати ключі:\n{e}")
            self.log(f"[ПОМИЛКА] Генерація ключів: {e}")

    def sign_document(self) -> None:
        try:
            input_file = self.selected_file.get().strip()
            if not input_file:
                messagebox.showwarning("Увага", "Спочатку оберіть файл.")
                return

            input_path = Path(input_file)
            if not input_path.exists():
                messagebox.showerror("Помилка", "Обраний файл не існує.")
                return

            validate_supported_document(input_path)

            if not self.private_key_path.exists():
                messagebox.showerror("Помилка", "Приватний ключ не знайдено. Спочатку згенеруйте ключі.")
                return

            password = self.password_var.get().strip() or None
            channels = self.channels_var.get()

            private_key = load_private_key(str(self.private_key_path), password=password)
            package = create_signature_package(str(input_path), private_key)

            output_file = build_signed_output_path(input_path)

            embed_signature_bits(
                input_file_path=str(input_path),
                output_file_path=str(output_file),
                signature_bits=package["signature_bits"],
                channels_to_use=channels,
            )

            self.last_original_file = input_path
            self.last_signed_file = output_file

            self.log("Підпис успішно сформовано та вбудовано.")
            self.log(f"Вхідний файл: {input_path}")
            self.log(f"Вихідний файл: {output_file}")
            self.log(f"SHA-256: {package['digest_hex']}")
            self.log(f"Довжина підпису (біт): {package['signature_bit_length']}")

            self.selected_file.set(str(output_file))
            self.log(f"Для подальшої перевірки автоматично вибрано файл: {output_file}")
            self.log("-" * 70)

            messagebox.showinfo("Успіх", f"Документ успішно підписано.\nЗбережено у:\n{output_file}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося підписати документ:\n{e}")
            self.log(f"[ПОМИЛКА] Підписання: {e}")

    def verify_document(self) -> None:
        try:
            input_file = self.selected_file.get().strip()
            if not input_file:
                messagebox.showwarning("Увага", "Спочатку оберіть файл.")
                return

            input_path = Path(input_file)
            if not input_path.exists():
                messagebox.showerror("Помилка", "Обраний файл не існує.")
                return

            validate_supported_document(input_path)

            if not self.public_key_path.exists():
                messagebox.showerror("Помилка", "Відкритий ключ не знайдено. Спочатку згенеруйте ключі.")
                return

            public_key = load_public_key(str(self.public_key_path))
            result = verify_document_signature(str(input_path), public_key)

            self.log("Перевірку завершено.")
            self.log(f"Файл: {result['file_path']}")
            self.log(f"SHA-256: {result['digest_hex']}")
            self.log(f"Довжина підпису (біт): {result['signature_bit_length']}")
            self.log(f"Підпис дійсний: {result['is_valid']}")
            self.log("-" * 70)

            if result["is_valid"]:
                messagebox.showinfo("Результат перевірки", "Підпис дійсний.")
            else:
                messagebox.showwarning("Результат перевірки", "Підпис недійсний.")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося перевірити документ:\n{e}")
            self.log(f"[ПОМИЛКА] Перевірка: {e}")

    def _load_preview_image(self, image_path: Path, max_size=(340, 340)) -> ImageTk.PhotoImage:
        img = Image.open(image_path).convert("RGB")
        img.thumbnail(max_size)
        return ImageTk.PhotoImage(img)

    def compare_images_window(self) -> None:
        if not self.last_original_file or not self.last_signed_file:
            messagebox.showwarning(
                "Увага",
                "Спочатку підпишіть зображення."
            )
            return

        if not is_supported_image(self.last_original_file) or not is_supported_image(self.last_signed_file):
            messagebox.showwarning(
                "Увага",
                "Порівняння доступне лише для PNG/JPEG."
            )
            return

        try:
            compare_win = tk.Toplevel(self.root)
            compare_win.title("Порівняння зображень")
            compare_win.geometry("900x500")
            compare_win.configure(bg="#f7f7f7")

            container = ttk.Frame(compare_win, padding=16)
            container.pack(fill="both", expand=True)

            title = ttk.Label(
                container,
                text="Порівняння оригінального та підписаного зображення",
                style="Title.TLabel",
                anchor="center"
            )
            title.pack(fill="x", pady=(0, 14))

            images_frame = ttk.Frame(container)
            images_frame.pack(fill="both", expand=True)

            images_frame.columnconfigure(0, weight=1)
            images_frame.columnconfigure(1, weight=1)

            original_frame = ttk.LabelFrame(images_frame, text="Оригінальне зображення", padding=10)
            original_frame.grid(row=0, column=0, sticky="nsew", padx=8)

            signed_frame = ttk.LabelFrame(images_frame, text="Підписане зображення", padding=10)
            signed_frame.grid(row=0, column=1, sticky="nsew", padx=8)

            original_preview = self._load_preview_image(self.last_original_file)
            signed_preview = self._load_preview_image(self.last_signed_file)

            original_label = tk.Label(original_frame, image=original_preview, bg="#ffffff")
            original_label.image = original_preview
            original_label.pack(pady=(0, 10))

            signed_label = tk.Label(signed_frame, image=signed_preview, bg="#ffffff")
            signed_label.image = signed_preview
            signed_label.pack(pady=(0, 10))

            ttk.Label(
                original_frame,
                text=str(self.last_original_file),
                wraplength=350,
                justify="center"
            ).pack()

            ttk.Label(
                signed_frame,
                text=str(self.last_signed_file),
                wraplength=350,
                justify="center"
            ).pack()

        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити порівняння:\n{e}")


def main() -> None:
    root = tk.Tk()
    app = HiddenEPApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()