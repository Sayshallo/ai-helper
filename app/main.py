from dotenv import load_dotenv
import os
from google import genai

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from llm_service import validate_ai_response, generate_product_card, validate_product_characteristics

import threading

root = tk.Tk()
root.title("AI-помощник")
root.geometry("600x400")
selected_file = tk.StringVar(value="Файл не выбран")
result_text = None
generate_button = None
status_label = None

load_dotenv(dotenv_path="../.env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key: raise ValueError("Не найден GEMINI_API_KEY в файле .env")
ai_client = genai.Client(api_key=api_key)
chat = None

def create_tth_window():
    global result_text, generate_button, status_label
    frm = ttk.Frame(root, padding=15)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="AI-помощник").pack(pady=(0, 20))
    ttk.Label(frm, text="Выберите JSON файл:").pack(anchor="w")
    file_frame = ttk.Frame(frm)
    file_frame.pack(fill="x", pady=5)
    ttk.Entry(file_frame, textvariable=selected_file, state="readonly").pack(side="left", fill="x", expand=True)
    ttk.Button(file_frame, text="Обзор", command=open_file).pack(side="left", padx=(10, 0))
    generate_button = ttk.Button(frm, text="Сгенерировать карточку", command=generate)
    generate_button.pack(pady=15)
    status_label = ttk.Label(frm, text="")
    status_label.pack()
    ttk.Label(frm, text="Результат генерации:").pack(anchor="w")
    result_text = tk.Text(frm, height=20, wrap="word")
    result_text.pack(fill="both", expand=True, pady=5)

def open_file():
    filepath = filedialog.askopenfilename(
        title="Выберите JSON-файл",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")])

    if filepath:
        selected_file.set(filepath)

def generate():
    filepath = selected_file.get()

    if filepath == "Файл не выбран":
        messagebox.showwarning("Файл не выбран","Сначала выберите JSON-файл.")
        return

    generate_button.config(state="disabled")
    status_label.config(text="Генерация карточки...")
    result_text.delete("1.0", tk.END)

    thread = threading.Thread(target = generate_worker, args = (filepath,), daemon = True)
    thread.start()

def generate_worker(filepath):
    try:
        attempt_count = 0
        ai_response, chat = generate_product_card(ai_client, filepath)
        if chat is None:
            root.after(0, finish_error, ai_response)
            return

        errors = validate_ai_response(ai_response)
        if not errors: errors = validate_product_characteristics(ai_response, filepath)

        while errors and attempt_count < 5:
            ai_response = chat.send_message(f"Были обнаружены ошибки: {errors}. "
                                            f"Исправь их и пришли мне обновленный ответ. Исправь только ошибки, остальное - не трогай.").text
            errors = validate_ai_response(ai_response)
            if not errors: errors = validate_product_characteristics(ai_response, filepath)

            attempt_count += 1

        if errors:
            error_message = "Ошибка генерации: не удалось получить корректный результат за 5 попыток."
            root.after(0, finish_error, error_message)
            return

        root.after(0, finish_success, ai_response)
    except Exception as ex:
        root.after(0, finish_error, "Во время генерации возникла ошибка: " + str(ex))

def finish_success(ai_response):
    result_text.delete("1.0", tk.END)
    result_text.insert("1.0", ai_response)
    status_label.config(text="Генерация завершена.")
    generate_button.config(state="normal")

def finish_error(error_message):
    status_label.config(text="Ошибка генерации.")
    generate_button.config(state="normal")
    messagebox.showerror("Ошибка генерации", error_message)


def main():
    create_tth_window()
    root.mainloop()

main()