import requests
import sys
import platform
from datetime import datetime
from colorama import init, Fore
import tkinter as tk
from tkinter import messagebox
import os

# مقداردهی اولیه colorama
init()

def validate_license(license_key, api_url="https://kma-tools-panel.onrender.com/check_license"):
    device_id = platform.node()  # شناسه منحصربه‌فرد دستگاه
    print(f"Validating license: {license_key} on device: {device_id}")
    try:
        # ارسال درخواست به‌صورت form data
        response = requests.post(api_url, data={'license_key': license_key, 'device_id': device_id}, timeout=10)
        print(f"Response status code: {response.status_code}")  # دیباگ کد وضعیت
        print(f"Response headers: {response.headers}")  # دیباگ هدرها
        data = response.json()
        print(f"Server response: {data}")  # دیباگ کامل
        if data.get('valid'):  # استفاده از get برای جلوگیری از KeyError
            if 'expiry_date' in data and datetime.strptime(data['expiry_date'], '%Y-%m-%d') >= datetime.now():
                if data.get('device_allowed', True):  # چک کردن دستگاه مجاز
                    print(f"{Fore.GREEN}The license is valid. Expiry date:{Fore.LIGHTGREEN_EX} {data['expiry_date']}{Fore.WHITE}")
                    return True
                else:
                    print(f"{Fore.RED}This license is already in use on another device.{Fore.WHITE}")
                    return False
            else:
                print(f"{Fore.RED}The license has expired or is invalid.{Fore.WHITE}")
                return False
        else:
            print(f"{Fore.RED}The license is invalid. Message:{Fore.LIGHTGREEN_EX} {data.get('message', 'No message')}{Fore.WHITE}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"{Fore.CYAN}Error connecting to the server: {e}")
        print(f"Full exception details: {str(e)}")  # دیباگ جزئیات
        return False
    except ValueError as e:
        print(f"{Fore.CYAN}Error parsing server response: {e} - Response text: {response.text if 'response' in locals() else 'No response'}")
        return False
    except Exception as e:
        print(f"{Fore.CYAN}Unexpected error: {e}")
        return False

def apply_theme(window, title_label, license_label, license_entry, paste_button, submit_button, theme_button, bg_color, fg_color, entry_bg):
    window.configure(bg=bg_color)
    title_label.configure(bg=bg_color, fg=fg_color)
    license_label.configure(bg=bg_color, fg=fg_color)
    license_entry.configure(bg=entry_bg, fg=fg_color)
    paste_button.configure(bg=bg_color, fg=fg_color)
    submit_button.configure(bg=bg_color, fg=fg_color)
    theme_button.configure(bg=bg_color, fg=fg_color)

def license_input_window():
    def on_submit():
        license_key = license_entry.get()
        print(f"Submitted license: {license_key}")
        if not license_key:
            messagebox.showerror("Error", "Please enter a license key.")
            return
        if validate_license(license_key):
            with open("license.txt", "w") as f:
                f.write(license_key)
            license_window.destroy()
            # اینجا کد اپلیکیشنت رو قرار بده
            # مثلاً: your_app_code_here()
        else:
            messagebox.showerror("Error", "Invalid license or already in use. Please enter a new license.")

    def on_paste():
        try:
            pasted_text = license_window.clipboard_get()
            license_entry.delete(0, tk.END)
            license_entry.insert(0, pasted_text)
            print(f"Pasted license: {pasted_text}")
        except tk.TclError:
            messagebox.showerror("Error", "Clipboard is empty or inaccessible.")

    def toggle_theme():
        current_theme = license_window.cget("bg")
        if current_theme == "#2E2E2E":  # دارک تم
            apply_theme(license_window, title_label, license_label, license_entry, paste_button, submit_button, theme_button, "#F0F0F0", "#000000", "#FFFFFF")  # لایت تم
        else:  # لایت تم
            apply_theme(license_window, title_label, license_label, license_entry, paste_button, submit_button, theme_button, "#2E2E2E", "#FFFFFF", "#D3D3D3")  # دارک تم

    def on_closing():
        license_window.destroy()
        sys.exit()  # بستن کل برنامه

    license_window = tk.Tk()
    license_window.title("License Activation")
    license_window.geometry("300x200")
    # اضافه کردن آیکون
    try:
        license_window.iconbitmap("icon.ico")  # برای Windows
    except tk.TclError:
        try:
            license_window.iconphoto(True, tk.PhotoImage(file="Nova.png"))  # برای دیگر سیستم‌ها
        except tk.TclError:
            print("Warning: Icon file not found. Please add icon.ico or Nova.png.")

    # اعمال تم اولیه (دارک تم)
    title_label = tk.Label(license_window, text="Enter License Key", font=("Arial", 14, "bold"))
    license_label = tk.Label(license_window, text="License Key:")
    license_entry = tk.Entry(license_window, width=30)
    paste_button = tk.Button(license_window, text="Paste", command=on_paste)
    submit_button = tk.Button(license_window, text="Submit", command=on_submit)
    theme_button = tk.Button(license_window, text="Toggle Theme", command=toggle_theme)

    apply_theme(license_window, title_label, license_label, license_entry, paste_button, submit_button, theme_button, "#2E2E2E", "#FFFFFF", "#D3D3D3")

    title_label.pack(pady=10)
    license_label.pack()
    license_entry.pack(pady=5)
    license_entry.focus_set()
    paste_button.pack(pady=5)
    submit_button.pack(pady=10)
    theme_button.pack(pady=5)

    # مدیریت بستن پنجره
    license_window.protocol("WM_DELETE_WINDOW", on_closing)

    license_window.mainloop()

def check_license_file():
    if os.path.exists("license.txt"):
        with open("license.txt", "r") as f:
            license_key = f.read().strip()
            print(f"Found license in file: {license_key}")
            if validate_license(license_key):
                return True
            else:
                print(f"{Fore.RED}License in file is invalid, clearing file.")
                with open("license.txt", "w") as f:
                    f.write("")
                return False
    return False

if __name__ == "__main__":
    if check_license_file():
        # اینجا کد اپلیکیشنت رو قرار بده، چون لایسنس معتبره
        # مثلاً: your_app_code_here()
        pass  # placeholder تا کد اپلیکیشنت رو بدی
    else:
        license_input_window()
