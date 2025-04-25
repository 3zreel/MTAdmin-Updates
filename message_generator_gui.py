import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import pyperclip
import requests
from PIL import Image
import sys
import os
import json
import csv
import validators
from packaging import version
import subprocess
import shutil
from translations import translations
from appdirs import user_data_dir  # Added for safe config path

# Define a safe directory to store config.json in the user's data directory
CONFIG_DIR = user_data_dir("MTAdmin", "MT")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# Function to get the correct path for resources after converting to .exe
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    full_path = os.path.join(base_path, relative_path)
    print(f"Attempting to load resource from: {full_path}")
    if not os.path.exists(full_path):
        print(f"Resource not found: {full_path}")
    return full_path

# Function to send message to Webhook with retry mechanism
def send_to_webhook(message, webhook_url, retries=3, delay=2):
    if not webhook_url:
        print("Webhook URL is empty!")
        return False
    for attempt in range(retries):
        try:
            payload = {"content": message}
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                return True
            else:
                print(f"Failed to send message to Webhook! Status Code: {response.status_code}")
        except Exception as e:
            print(f"Error sending message to Webhook (Attempt {attempt + 1}/{retries}): {str(e)}")
        if attempt < retries - 1:
            import time
            time.sleep(delay)
    return False

# Main application class
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Current version of the application
        self.current_version = "1.0.2"  # Updated to 1.0.2
        self.update_url = "https://raw.githubusercontent.com/3zreel/MTAdmin-Updates/main/update.json"

        # Check for updates on startup
        self.check_for_updates()

        # Default language
        self.lang = "en"
        self.trans = translations[self.lang]

        # Window settings
        self.title(self.trans["title"])
        self.geometry("1000x700")
        self.primary_color = "#FF8F00"  # Warm Orange (Logo-inspired)
        self.secondary_color = "#FFA726"  # Lighter Orange for hover effects
        self.bg_color = "#212121"  # Dark background
        self.frame_bg = "#2D2D2D"  # Frame background
        self.text_color = "#E0E0E0"  # Primary text color
        self.text_color_secondary = "#B0BEC5"  # Secondary text color

        # Make the main window resizable
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Set background color
        self.configure(fg_color=self.bg_color)

        # Load icon
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Error loading icon: {e}")
        else:
            print(f"Icon file not found: {icon_path}")

        # Load complaints and webhooks
        self.complaints = self.load_complaints()
        self.webhooks = self.load_webhooks()
        self.current_complaint = None

        # Header frame
        self.header_frame = ctk.CTkFrame(self, fg_color=self.frame_bg, height=60, corner_radius=0)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header_frame.grid_propagate(False)

        # Load logo and title in header
        try:
            logo_image = Image.open(resource_path("logo.png"))
            logo_image = logo_image.resize((40, 40), Image.Resampling.LANCZOS)
            self.logo_image = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(40, 40))
            logo_label = ctk.CTkLabel(self.header_frame, image=self.logo_image, text="")
            logo_label.grid(row=0, column=0, padx=10, pady=10)
        except Exception as e:
            print(f"Error loading logo: {e}")
            logo_label = ctk.CTkLabel(self.header_frame, text="MT", font=("Cairo", 16, "bold"), text_color=self.primary_color)
            logo_label.grid(row=0, column=0, padx=10, pady=10)

        header_title = ctk.CTkLabel(self.header_frame, text="MT Admin", font=("Cairo", 18, "bold"), text_color=self.text_color)
        header_title.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # Sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self, fg_color=self.frame_bg, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        self.sidebar_frame.grid_rowconfigure(7, weight=1)  # Push version info to bottom

        # Section title
        self.section_title = ctk.CTkLabel(self.sidebar_frame, text=self.trans["home"],
                                          font=("Cairo", 20, "bold"), text_color=self.primary_color)
        self.section_title.pack(pady=(20, 10))

        # Sidebar buttons with updated design
        button_style = {"font": ("Cairo", 14), "fg_color": self.primary_color, "hover_color": self.secondary_color, "corner_radius": 20, "height": 40}
        self.home_button = ctk.CTkButton(self.sidebar_frame, text=self.trans["home"], **button_style, command=self.show_home)
        self.home_button.pack(fill="x", padx=20, pady=10)

        self.warning_button = ctk.CTkButton(self.sidebar_frame, text=self.trans["support_warn"], **button_style, command=self.show_warning_section)
        self.warning_button.pack(fill="x", padx=20, pady=10)

        self.technical_button = ctk.CTkButton(self.sidebar_frame, text=self.trans["record_technical"], **button_style, command=self.show_technical_section)
        self.technical_button.pack(fill="x", padx=20, pady=10)

        self.management_button = ctk.CTkButton(self.sidebar_frame, text=self.trans["management"], **button_style, command=self.show_management_section)
        self.management_button.pack(fill="x", padx=20, pady=10)

        self.complaints_button = ctk.CTkButton(self.sidebar_frame, text=self.trans["complaints_list"], **button_style, command=self.show_complaints_list)
        self.complaints_button.pack(fill="x", padx=20, pady=10)

        self.webhook_button = ctk.CTkButton(self.sidebar_frame, text="Webhook Settings", **button_style, command=self.show_webhook_section)
        self.webhook_button.pack(fill="x", padx=20, pady=10)

        # Version and designer info at the bottom of the sidebar
        version_label = ctk.CTkLabel(self.sidebar_frame, text="Version 1.0.2 | Designed by MT | KHALID",  # Updated version
                                     font=("Cairo", 12), text_color=self.text_color_secondary)
        version_label.pack(side="bottom", pady=20)

        # Main content frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent", border_color=self.primary_color, border_width=1, corner_radius=10)
        self.content_frame.grid(row=1, column=1, padx=30, pady=30, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Create sections
        self.create_home_section()
        self.create_warning_section()
        self.create_technical_section()
        self.create_management_section()
        self.create_complaints_list_section()
        self.create_complaint_edit_section()
        self.create_webhook_section()

        # Show home page by default
        self.show_home()

    def check_for_updates(self):
        try:
            # Fetch update information from the server
            response = requests.get(self.update_url, timeout=5)
            response.raise_for_status()
            update_info = response.json()

            # Compare versions
            latest_version = update_info["version"]
            if version.parse(latest_version) > version.parse(self.current_version):
                # Prompt user to update
                if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available.\nDo you want to update now?"):
                    self.download_and_install_update(update_info["download_url"])
        except Exception as e:
            print(f"Error checking for updates: {e}")

    def download_and_install_update(self, download_url):
        try:
            # Download the new version
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            # Determine the path to the current executable
            current_exe = sys.executable
            temp_exe = current_exe + ".new"

            # Save the new executable temporarily
            with open(temp_exe, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Replace the current executable with the new one
            # Create a batch file to handle the replacement
            bat_file = "update.bat"
            with open(bat_file, "w") as f:
                f.write(f"""
@echo off
timeout /t 2 /nobreak >nul
move /Y "{temp_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")

            # Run the batch file and close the current application
            subprocess.Popen([bat_file], shell=True)
            sys.exit(0)

        except Exception as e:
            print(f"Error during update: {e}")
            messagebox.showerror("Update Error", f"Failed to update the application: {str(e)}")

    # Function to create input fields with updated design
    def create_field(self, parent, label_text, width=300, placeholder="", row=None, column=1):
        if row is not None:
            label = ctk.CTkLabel(parent, text=label_text, font=("Cairo", 11), text_color=self.text_color)
            label.grid(row=row, column=column * 2, padx=20, pady=5, sticky="w")
            entry = ctk.CTkEntry(parent, width=width, font=("Cairo", 11), placeholder_text=placeholder,
                                 fg_color=self.frame_bg, border_color=self.primary_color, text_color=self.text_color)
            entry.grid(row=row, column=column * 2 + 1, padx=20, pady=5, sticky="ew")
            return entry
        else:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", padx=20, pady=5)
            label = ctk.CTkLabel(frame, text=label_text, font=("Cairo", 11), text_color=self.text_color)
            label.pack(side="left", padx=5)
            entry = ctk.CTkEntry(frame, width=width, font=("Cairo", 11), placeholder_text=placeholder,
                                 fg_color=self.frame_bg, border_color=self.primary_color, text_color=self.text_color)
            entry.pack(side="left", fill="x", expand=True)
            return entry

    def create_home_section(self):
        self.home_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.home_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.home_frame.grid_forget()

        # Welcome label with shadow effect
        shadow_offset = 1
        welcome_label_shadow = ctk.CTkLabel(self.home_frame, text="Welcome to MT Admin",
                                            font=("Cairo", 36, "bold"), text_color="#000000")
        welcome_label_shadow.place(relx=0.5, rely=0.4, x=shadow_offset, y=shadow_offset, anchor="center")

        welcome_label = ctk.CTkLabel(self.home_frame, text="Welcome to MT Admin",
                                     font=("Cairo", 36, "bold"), text_color=self.primary_color)
        welcome_label.place(relx=0.5, rely=0.4, anchor="center")

        # Sub-label with shadow effect
        sub_label_shadow = ctk.CTkLabel(self.home_frame, text="Please select a section from the sidebar",
                                        font=("Cairo", 18), text_color="#000000")
        sub_label_shadow.place(relx=0.5, rely=0.5, x=shadow_offset, y=shadow_offset, anchor="center")

        sub_label = ctk.CTkLabel(self.home_frame, text="Please select a section from the sidebar",
                                 font=("Cairo", 18), text_color=self.text_color_secondary)
        sub_label.place(relx=0.5, rely=0.5, anchor="center")

    def create_warning_section(self):
        self.warning_frame = ctk.CTkFrame(self.content_frame, fg_color=self.frame_bg, corner_radius=10)
        self.warning_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.warning_frame.grid_forget()

        self.entry_discord_id = self.create_field(self.warning_frame, self.trans["discord_id"], placeholder=self.trans["discord_id"], row=0, column=0)
        self.entry_person_info = self.create_field(self.warning_frame, self.trans["person_info"], placeholder=self.trans["person_info"], row=0, column=1)
        self.entry_violation = self.create_field(self.warning_frame, self.trans["violation_type"], placeholder=self.trans["violation_type"], row=1, column=0)
        self.entry_decision_source = self.create_field(self.warning_frame, self.trans["decision_source"], placeholder=self.trans["decision_source"], row=1, column=1)

        self.warn_ban_var = ctk.StringVar(value="warn 1 + ban 1d")
        warn_ban_options = ["warn 1 + ban 1d", "warn 2 + ban 3d", "warn 3 + ban 7d + إعادة تفعيل", "نهائي", "Banned Perm"]
        warn_ban_label = ctk.CTkLabel(self.warning_frame, text=self.trans["warn_ban_type"],
                                      font=("Cairo", 11), text_color=self.text_color)
        warn_ban_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        self.warn_ban_menu = ctk.CTkOptionMenu(self.warning_frame, variable=self.warn_ban_var, values=warn_ban_options,
                                               font=("Cairo", 11), fg_color=self.primary_color, button_color=self.secondary_color,
                                               button_hover_color=self.secondary_color, dropdown_fg_color=self.frame_bg,
                                               dropdown_text_color=self.text_color, text_color=self.text_color)
        self.warn_ban_menu.grid(row=2, column=1, padx=20, pady=5, sticky="w")

        self.person_id_var = ctk.StringVar(value="Offline")
        person_id_options = ["Offline", "Manual Entry"]
        person_id_label = ctk.CTkLabel(self.warning_frame, text=self.trans["person_status"],
                                       font=("Cairo", 11), text_color=self.text_color)
        person_id_label.grid(row=2, column=2, padx=20, pady=5, sticky="w")
        self.person_id_menu = ctk.CTkOptionMenu(self.warning_frame, variable=self.person_id_var, values=person_id_options,
                                                font=("Cairo", 11), fg_color=self.primary_color, button_color=self.secondary_color,
                                                button_hover_color=self.secondary_color, dropdown_fg_color=self.frame_bg,
                                                dropdown_text_color=self.text_color, text_color=self.text_color,
                                                command=self.toggle_person_id_entry)
        self.person_id_menu.grid(row=2, column=3, padx=20, pady=5, sticky="w")
        self.entry_person_id_manual = ctk.CTkEntry(self.warning_frame, width=300, font=("Cairo", 11),
                                                  placeholder_text="Enter ID manually", fg_color=self.frame_bg,
                                                  border_color=self.primary_color, text_color=self.text_color)

        self.generate_warning_button = ctk.CTkButton(self.warning_frame, text=self.trans["generate_save"],
                                                     font=("Cairo", 14, "bold"), fg_color=self.primary_color,
                                                     hover_color=self.secondary_color, corner_radius=20, width=200,
                                                     command=self.generate_warning_message)
        self.generate_warning_button.grid(row=3, column=0, columnspan=4, pady=20)

        self.entry_person_id_manual.grid_forget()

    def create_technical_section(self):
        self.technical_frame = ctk.CTkFrame(self.content_frame, fg_color=self.frame_bg, corner_radius=10)
        self.technical_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.technical_frame.grid_forget()

        self.entry_complainant_mention = self.create_field(self.technical_frame, self.trans["complainant_mention"],
                                                          placeholder=self.trans["complainant_mention"], row=0, column=0)
        self.entry_complainant_clip = self.create_field(self.technical_frame, self.trans["complainant_clip"],
                                                        placeholder=self.trans["complainant_clip"], row=0, column=1)
        self.entry_accused_mention = self.create_field(self.technical_frame, self.trans["accused_mention"],
                                                       placeholder=self.trans["accused_mention"], row=1, column=0)
        self.entry_accused_clip = self.create_field(self.technical_frame, self.trans["accused_clip"],
                                                    placeholder=self.trans["accused_clip"], row=1, column=1)
        self.entry_ban_link = self.create_field(self.technical_frame, self.trans["ban_link"],
                                                placeholder=self.trans["ban_link"], row=2, column=0)

        self.generate_technical_button = ctk.CTkButton(self.technical_frame, text=self.trans["generate_save"],
                                                       font=("Cairo", 14, "bold"), fg_color=self.primary_color,
                                                       hover_color=self.secondary_color, corner_radius=20, width=200,
                                                       command=self.generate_technical_message)
        self.generate_technical_button.grid(row=3, column=0, columnspan=4, pady=20)

    def create_management_section(self):
        self.management_frame = ctk.CTkFrame(self.content_frame, fg_color=self.frame_bg, corner_radius=10)
        self.management_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.management_frame.grid_forget()
        self.management_frame.grid_rowconfigure(0, weight=1)
        self.management_frame.grid_columnconfigure(0, weight=1)

        # Subsections for Management
        self.create_warn_frame = ctk.CTkFrame(self.management_frame, fg_color=self.frame_bg)
        self.create_warn_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.create_warn_frame.grid_forget()

        self.create_ban_frame = ctk.CTkFrame(self.management_frame, fg_color=self.frame_bg)
        self.create_ban_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.create_ban_frame.grid_forget()

        # CreateWarn Section
        title_label = ctk.CTkLabel(self.create_warn_frame, text=self.trans["create_warn"],
                                   font=("Cairo", 20, "bold"), text_color=self.primary_color)
        title_label.grid(row=0, column=0, columnspan=4, pady=15)

        self.entry_player_discord_id = self.create_field(self.create_warn_frame, self.trans["player_discord_id"],
                                                         placeholder="Discord ID", row=1, column=0)
        self.entry_player_info = self.create_field(self.create_warn_frame, self.trans["player_info"],
                                                   placeholder="Enter Player Info", row=1, column=1)
        self.entry_reason = self.create_field(self.create_warn_frame, self.trans["reason"],
                                              placeholder="Enter Reason For Ban", row=2, column=0)

        self.ban_time_var = ctk.StringVar(value="1H")
        ban_time_options = ["1H", "1D", "3D", "1W"]
        ban_time_label = ctk.CTkLabel(self.create_warn_frame, text=self.trans["ban_time"],
                                      font=("Cairo", 11), text_color=self.text_color)
        ban_time_label.grid(row=2, column=2, padx=20, pady=5, sticky="w")
        self.ban_time_menu = ctk.CTkOptionMenu(self.create_warn_frame, variable=self.ban_time_var, values=ban_time_options,
                                               font=("Cairo", 11), fg_color=self.primary_color, button_color=self.secondary_color,
                                               button_hover_color=self.secondary_color, dropdown_fg_color=self.frame_bg,
                                               dropdown_text_color=self.text_color, text_color=self.text_color)
        self.ban_time_menu.grid(row=2, column=3, padx=20, pady=5, sticky="w")

        self.is_banned_var = ctk.StringVar(value="Yes")
        is_banned_options = ["Yes", "No"]
        is_banned_label = ctk.CTkLabel(self.create_warn_frame, text=self.trans["is_player_banned"],
                                       font=("Cairo", 11), text_color=self.text_color)
        is_banned_label.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.is_banned_menu = ctk.CTkOptionMenu(self.create_warn_frame, variable=self.is_banned_var, values=is_banned_options,
                                                font=("Cairo", 11), fg_color=self.primary_color, button_color=self.secondary_color,
                                                button_hover_color=self.secondary_color, dropdown_fg_color=self.frame_bg,
                                                dropdown_text_color=self.text_color, text_color=self.text_color)
        self.is_banned_menu.grid(row=3, column=1, padx=20, pady=5, sticky="w")

        self.generate_create_warn_button = ctk.CTkButton(self.create_warn_frame, text=self.trans["generate_save"],
                                                         font=("Cairo", 14, "bold"), fg_color=self.primary_color,
                                                         hover_color=self.secondary_color, corner_radius=20, width=200,
                                                         command=self.generate_create_warn_message)
        self.generate_create_warn_button.grid(row=4, column=0, columnspan=4, pady=20)

        # CreateBan Section
        ban_title_label = ctk.CTkLabel(self.create_ban_frame, text=self.trans["create_ban"],
                                       font=("Cairo", 20, "bold"), text_color=self.primary_color)
        ban_title_label.grid(row=0, column=0, columnspan=4, pady=15)

        self.entry_ban_player_discord_id = self.create_field(self.create_ban_frame, self.trans["player_discord_id"],
                                                             placeholder="Discord ID", row=1, column=0)
        self.entry_ban_player_info = self.create_field(self.create_ban_frame, self.trans["player_info"],
                                                       placeholder="Enter Player Info", row=1, column=1)
        self.entry_ban_reason = self.create_field(self.create_ban_frame, self.trans["reason"],
                                                  placeholder="Enter Reason For Ban", row=2, column=0)
        self.entry_ban_evidence = self.create_field(self.create_ban_frame, "Evidence",
                                                    placeholder="Enter Evidence", row=2, column=1)

        self.ban_is_banned_var = ctk.StringVar(value="Yes")
        ban_is_banned_options = ["Yes", "No"]
        ban_is_banned_label = ctk.CTkLabel(self.create_ban_frame, text=self.trans["is_player_banned"],
                                           font=("Cairo", 11), text_color=self.text_color)
        ban_is_banned_label.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        self.ban_is_banned_menu = ctk.CTkOptionMenu(self.create_ban_frame, variable=self.ban_is_banned_var, values=ban_is_banned_options,
                                                    font=("Cairo", 11), fg_color=self.primary_color, button_color=self.secondary_color,
                                                    button_hover_color=self.secondary_color, dropdown_fg_color=self.frame_bg,
                                                    dropdown_text_color=self.text_color, text_color=self.text_color)
        self.ban_is_banned_menu.grid(row=3, column=1, padx=20, pady=5, sticky="w")

        self.generate_create_ban_button = ctk.CTkButton(self.create_ban_frame, text=self.trans["generate_save"],
                                                        font=("Cairo", 14, "bold"), fg_color=self.primary_color,
                                                        hover_color=self.secondary_color, corner_radius=20, width=200,
                                                        command=self.generate_create_ban_message)
        self.generate_create_ban_button.grid(row=4, column=0, columnspan=4, pady=20)

        # Management subsection navigation
        nav_frame = ctk.CTkFrame(self.management_frame, fg_color="transparent")
        nav_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        nav_frame.grid_columnconfigure(0, weight=1)
        nav_frame.grid_columnconfigure(1, weight=1)
        nav_frame.grid_columnconfigure(2, weight=1)

        self.create_warn_button = ctk.CTkButton(nav_frame, text=self.trans["create_warn"],
                                                font=("Cairo", 14), fg_color=self.primary_color,
                                                hover_color=self.secondary_color, corner_radius=20,
                                                command=self.show_create_warn_section)
        self.create_warn_button.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.create_ban_button = ctk.CTkButton(nav_frame, text=self.trans["create_ban"],
                                               font=("Cairo", 14), fg_color=self.primary_color,
                                               hover_color=self.secondary_color, corner_radius=20,
                                               command=self.show_create_ban_section)
        self.create_ban_button.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        back_button = ctk.CTkButton(nav_frame, text=self.trans["back"],
                                    font=("Cairo", 14), fg_color="#37474F",
                                    hover_color="#546E7A", corner_radius=20, command=self.show_home)
        back_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")

    def create_complaints_list_section(self):
        self.complaints_frame = ctk.CTkScrollableFrame(self.content_frame, fg_color=self.frame_bg, corner_radius=10)
        self.complaints_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.complaints_frame.grid_forget()

        title_label = ctk.CTkLabel(self.complaints_frame, text=self.trans["complaints_list"],
                                   font=("Cairo", 20, "bold"), text_color=self.primary_color)
        title_label.pack(pady=15)

        self.complaints_list_container = ctk.CTkFrame(self.complaints_frame, fg_color="transparent")
        self.complaints_list_container.pack(fill="both", expand=True, padx=20)

        export_button = ctk.CTkButton(self.complaints_frame, text=self.trans["export_csv"],
                                      font=("Cairo", 14), fg_color=self.primary_color,
                                      hover_color=self.secondary_color, corner_radius=20,
                                      command=self.export_to_csv)
        export_button.pack(pady=15)

        back_button = ctk.CTkButton(self.complaints_frame, text=self.trans["back"],
                                    font=("Cairo", 14), fg_color="#37474F",
                                    hover_color="#546E7A", corner_radius=20, command=self.show_home)
        back_button.pack(pady=15)

    def create_complaint_edit_section(self):
        self.edit_frame = ctk.CTkFrame(self.content_frame, fg_color=self.frame_bg, corner_radius=10)
        self.edit_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.edit_frame.grid_forget()

        self.edit_title = ctk.CTkLabel(self.edit_frame, text=self.trans["edit_complaint"],
                                       font=("Cairo", 20, "bold"), text_color=self.primary_color)
        self.edit_title.grid(row=0, column=0, columnspan=4, pady=15)

        self.edit_fields = {}
        fields = [
            ("discord_id", self.trans["discord_id"]),
            ("person_info", self.trans["person_info"]),
            ("violation", self.trans["violation_type"]),
            ("decision_source", self.trans["decision_source"]),
            ("complainant_mention", self.trans["complainant_mention"]),
            ("complainant_clip", self.trans["complainant_clip"]),
            ("accused_mention", self.trans["accused_mention"]),
            ("accused_clip", self.trans["accused_clip"]),
            ("ban_link", self.trans["ban_link"])
        ]

        for idx, (field_name, label_text) in enumerate(fields):
            self.edit_fields[field_name] = self.create_field(self.edit_frame, label_text, placeholder=label_text, row=(idx // 2) + 1, column=idx % 2)

        # Warn/Ban Type
        warn_ban_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        warn_ban_frame.grid(row=len(fields) // 2 + 1, column=0, columnspan=4, padx=20, pady=5, sticky="ew")
        warn_ban_label = ctk.CTkLabel(warn_ban_frame, text=self.trans["warn_ban_type"],
                                      font=("Cairo", 11), text_color=self.text_color)
        warn_ban_label.pack(side="left", padx=5)
        self.edit_warn_ban_var = ctk.StringVar(value="warn 1 + ban 1d")
        warn_ban_options = ["warn 1 + ban 1d", "warn 2 + ban 3d", "warn 3 + ban 7d + إعادة تفعيل", "نهائي", "Banned Perm"]
        self.edit_warn_ban_menu = ctk.CTkOptionMenu(warn_ban_frame, variable=self.edit_warn_ban_var, values=warn_ban_options,
                                                    font=("Cairo", 11), fg_color=self.primary_color, button_color=self.secondary_color,
                                                    button_hover_color=self.secondary_color, dropdown_fg_color=self.frame_bg,
                                                    dropdown_text_color=self.text_color, text_color=self.text_color)
        self.edit_warn_ban_menu.pack(side="left")

        # Person ID
        person_id_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        person_id_frame.grid(row=len(fields) // 2 + 2, column=0, columnspan=4, padx=20, pady=5, sticky="ew")
        person_id_label = ctk.CTkLabel(person_id_frame, text=self.trans["person_status"],
                                       font=("Cairo", 11), text_color=self.text_color)
        person_id_label.pack(side="left", padx=5)
        self.edit_person_id_var = ctk.StringVar(value="Offline")
        person_id_options = ["Offline", "Manual Entry"]
        self.edit_person_id_menu = ctk.CTkOptionMenu(person_id_frame, variable=self.edit_person_id_var, values=person_id_options,
                                                     font=("Cairo", 11), fg_color=self.primary_color, button_color=self.secondary_color,
                                                     button_hover_color=self.secondary_color, dropdown_fg_color=self.frame_bg,
                                                     dropdown_text_color=self.text_color, text_color=self.text_color,
                                                     command=self.toggle_edit_person_id_entry)
        self.edit_person_id_menu.pack(side="left")
        self.edit_person_id_manual = ctk.CTkEntry(person_id_frame, width=300, font=("Cairo", 11),
                                                  placeholder_text="Enter ID manually", fg_color=self.frame_bg,
                                                  border_color=self.primary_color, text_color=self.text_color)
        self.edit_person_id_manual.pack_forget()

        # Buttons
        btn_frame = ctk.CTkFrame(self.edit_frame, fg_color="transparent")
        btn_frame.grid(row=len(fields) // 2 + 3, column=0, columnspan=4, pady=20, sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        save_button = ctk.CTkButton(btn_frame, text=self.trans["save_changes"],
                                    font=("Cairo", 14), fg_color=self.primary_color,
                                    hover_color=self.secondary_color, corner_radius=20,
                                    command=self.save_edited_complaint)
        save_button.grid(row=0, column=0, padx=10, sticky="e")
        back_button = ctk.CTkButton(btn_frame, text=self.trans["back"],
                                    font=("Cairo", 14), fg_color="#37474F",
                                    hover_color="#546E7A", corner_radius=20,
                                    command=self.show_complaints_list)
        back_button.grid(row=0, column=1, padx=10, sticky="w")

    def create_webhook_section(self):
        self.webhook_frame = ctk.CTkFrame(self.content_frame, fg_color=self.frame_bg, corner_radius=10)
        self.webhook_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.webhook_frame.grid_forget()

        title_label = ctk.CTkLabel(self.webhook_frame, text="Webhook Settings",
                                   font=("Cairo", 20, "bold"), text_color=self.primary_color)
        title_label.grid(row=0, column=0, columnspan=2, pady=15)

        # Warning Webhook URL
        self.entry_warning_webhook = self.create_field(self.webhook_frame, "Warning Webhook URL",
                                                       placeholder="Enter Warning Webhook URL", row=1, column=0)
        self.entry_warning_webhook.delete(0, "end")
        self.entry_warning_webhook.insert(0, self.webhooks.get("warning", ""))

        # Technical Webhook URL
        self.entry_technical_webhook = self.create_field(self.webhook_frame, "Technical Webhook URL",
                                                         placeholder="Enter Technical Webhook URL", row=2, column=0)
        self.entry_technical_webhook.delete(0, "end")
        self.entry_technical_webhook.insert(0, self.webhooks.get("technical", ""))

        # Create Warn Webhook URL
        self.entry_createwarn_webhook = self.create_field(self.webhook_frame, "Create Warn Webhook URL",
                                                          placeholder="Enter Create Warn Webhook URL", row=3, column=0)
        self.entry_createwarn_webhook.delete(0, "end")
        self.entry_createwarn_webhook.insert(0, self.webhooks.get("create_warn", ""))

        # Create Ban Webhook URL
        self.entry_createban_webhook = self.create_field(self.webhook_frame, "Create Ban Webhook URL",
                                                         placeholder="Enter Create Ban Webhook URL", row=4, column=0)
        self.entry_createban_webhook.delete(0, "end")
        self.entry_createban_webhook.insert(0, self.webhooks.get("create_ban", ""))

        # Save Webhooks Button
        self.save_webhooks_button = ctk.CTkButton(self.webhook_frame, text="Save Webhooks",
                                                  font=("Cairo", 14, "bold"), fg_color=self.primary_color,
                                                  hover_color=self.secondary_color, corner_radius=20, width=200,
                                                  command=self.save_webhooks)
        self.save_webhooks_button.grid(row=5, column=0, columnspan=2, pady=20)

        # Back Button
        back_button = ctk.CTkButton(self.webhook_frame, text=self.trans["back"],
                                    font=("Cairo", 14), fg_color="#37474F",
                                    hover_color="#546E7A", corner_radius=20, command=self.show_home)
        back_button.grid(row=6, column=0, columnspan=2, pady=10)

    def toggle_person_id_entry(self, value):
        if value == "Manual Entry":
            self.entry_person_id_manual.grid(row=2, column=3, padx=20, pady=5, sticky="ew")
        else:
            self.entry_person_id_manual.grid_forget()

    def toggle_edit_person_id_entry(self, value):
        if value == "Manual Entry":
            self.edit_person_id_manual.pack(side="left", fill="x", expand=True, padx=5)
        else:
            self.edit_person_id_manual.pack_forget()

    def show_home(self):
        self.warning_frame.grid_forget()
        self.technical_frame.grid_forget()
        self.management_frame.grid_forget()
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid_forget()
        self.complaints_frame.grid_forget()
        self.edit_frame.grid_forget()
        self.webhook_frame.grid_forget()
        self.home_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=self.trans["home"])

    def show_warning_section(self):
        self.home_frame.grid_forget()
        self.technical_frame.grid_forget()
        self.management_frame.grid_forget()
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid_forget()
        self.complaints_frame.grid_forget()
        self.edit_frame.grid_forget()
        self.webhook_frame.grid_forget()
        self.warning_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=self.trans["support_warn"])

    def show_technical_section(self):
        self.home_frame.grid_forget()
        self.warning_frame.grid_forget()
        self.management_frame.grid_forget()
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid_forget()
        self.complaints_frame.grid_forget()
        self.edit_frame.grid_forget()
        self.webhook_frame.grid_forget()
        self.technical_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=self.trans["record_technical"])

    def show_management_section(self):
        self.home_frame.grid_forget()
        self.warning_frame.grid_forget()
        self.technical_frame.grid_forget()
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid_forget()
        self.complaints_frame.grid_forget()
        self.edit_frame.grid_forget()
        self.webhook_frame.grid_forget()
        self.management_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=self.trans["management"])
        self.show_create_warn_section()

    def show_create_warn_section(self):
        self.create_ban_frame.grid_forget()
        self.create_warn_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=self.trans["create_warn"])

    def show_create_ban_section(self):
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=self.trans["create_ban"])

    def show_complaints_list(self):
        self.home_frame.grid_forget()
        self.warning_frame.grid_forget()
        self.technical_frame.grid_forget()
        self.management_frame.grid_forget()
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid_forget()
        self.edit_frame.grid_forget()
        self.webhook_frame.grid_forget()
        self.complaints_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=self.trans["complaints_list"])
        self.update_complaints_list()

    def show_webhook_section(self):
        self.home_frame.grid_forget()
        self.warning_frame.grid_forget()
        self.technical_frame.grid_forget()
        self.management_frame.grid_forget()
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid_forget()
        self.complaints_frame.grid_forget()
        self.edit_frame.grid_forget()
        self.webhook_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text="Webhook Settings")

    def show_edit_complaint(self, complaint):
        self.current_complaint = complaint
        self.home_frame.grid_forget()
        self.warning_frame.grid_forget()
        self.technical_frame.grid_forget()
        self.management_frame.grid_forget()
        self.create_warn_frame.grid_forget()
        self.create_ban_frame.grid_forget()
        self.complaints_frame.grid_forget()
        self.webhook_frame.grid_forget()
        self.edit_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.section_title.configure(text=f"{self.trans['edit_complaint']}: {complaint.get('id', 'Not Specified')}")
        
        self.edit_fields["discord_id"].delete(0, "end")
        self.edit_fields["discord_id"].insert(0, complaint.get("discord_id", ""))
        self.edit_fields["person_info"].delete(0, "end")
        self.edit_fields["person_info"].insert(0, complaint.get("person_info", ""))
        self.edit_warn_ban_var.set(complaint.get("warn_ban", "warn 1 + ban 1d"))
        self.edit_person_id_var.set(complaint.get("person_id", "Offline"))
        if complaint.get("person_id", "Offline") != "Offline":
            self.edit_person_id_manual.delete(0, "end")
            self.edit_person_id_manual.insert(0, complaint.get("person_id", ""))
            self.toggle_edit_person_id_entry("Manual Entry")
        else:
            self.toggle_edit_person_id_entry("Offline")
        self.edit_fields["violation"].delete(0, "end")
        self.edit_fields["violation"].insert(0, complaint.get("violation", ""))
        self.edit_fields["decision_source"].delete(0, "end")
        self.edit_fields["decision_source"].insert(0, complaint.get("decision_source", ""))
        self.edit_fields["complainant_mention"].delete(0, "end")
        self.edit_fields["complainant_mention"].insert(0, complaint.get("complainant_mention", ""))
        self.edit_fields["complainant_clip"].delete(0, "end")
        self.edit_fields["complainant_clip"].insert(0, complaint.get("complainant_clip", ""))
        self.edit_fields["accused_mention"].delete(0, "end")
        self.edit_fields["accused_mention"].insert(0, complaint.get("accused_mention", ""))
        self.edit_fields["accused_clip"].delete(0, "end")
        self.edit_fields["accused_clip"].insert(0, complaint.get("accused_clip", ""))
        self.edit_fields["ban_link"].delete(0, "end")
        self.edit_fields["ban_link"].insert(0, complaint.get("ban_link", ""))

    def generate_warning_message(self):
        discord_id = self.entry_discord_id.get()
        person_info = self.entry_person_info.get()
        warn_ban = self.warn_ban_var.get()
        person_id = self.person_id_var.get() if self.person_id_var.get() == "Offline" else self.entry_person_id_manual.get()
        violation_type = self.entry_violation.get()
        decision_source_id = self.entry_decision_source.get()

        # Validate inputs
        if not discord_id or not warn_ban or not person_id or not violation_type or not decision_source_id:
            messagebox.showerror(self.trans["error"], self.trans["required_fields"])
            return
        if not discord_id.isdigit():
            messagebox.showerror(self.trans["error"], self.trans["invalid_discord_id"])
            return
        if not decision_source_id.isdigit():
            messagebox.showerror(self.trans["error"], self.trans["invalid_discord_id"])
            return

        current_datetime = datetime.now().strftime("%m/%d %I:%M %p").lower()
        message = f"<@{discord_id}>\n"
        if person_info:
            message += f"{person_info}\n"
        message += f"discord : (discord:{discord_id})\n"
        message += f"\n{warn_ban}\n"
        message += f"id : {person_id}\n"
        message += f"{violation_type}\n"
        message += f"\nby : <@{decision_source_id}>\n"
        message += f"{current_datetime}"

        pyperclip.copy(message)

        complaint = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "type": "warning",
            "discord_id": discord_id,
            "person_info": person_info,
            "warn_ban": warn_ban,
            "person_id": person_id,
            "violation": violation_type,
            "decision_source": decision_source_id,
            "timestamp": current_datetime
        }
        self.complaints.append(complaint)
        self.save_complaints()

        success = send_to_webhook(message, self.webhooks.get("warning", ""))
        messagebox.showinfo(self.trans["success"] if success else self.trans["partial_success"],
                            self.trans["message_generated_copied"] + (self.trans["sent_to_webhook"] if success else ""))

    def generate_technical_message(self):
        complainant_mention = self.entry_complainant_mention.get().strip()
        complainant_clip = self.entry_complainant_clip.get()
        accused_mention = self.entry_accused_mention.get().strip()
        accused_clip = self.entry_accused_clip.get()
        ban_link = self.entry_ban_link.get()

        # Validate inputs
        if not complainant_mention or not complainant_clip or not accused_mention or not accused_clip:
            messagebox.showerror(self.trans["error"], self.trans["required_fields"])
            return
        if not complainant_mention.isdigit() or not accused_mention.isdigit():
            messagebox.showerror(self.trans["error"], self.trans["invalid_discord_id"])
            return
        if not validators.url(complainant_clip) or not validators.url(accused_clip):
            messagebox.showerror(self.trans["error"], self.trans["invalid_url"])
            return
        if ban_link and not validators.url(ban_link):
            messagebox.showerror(self.trans["error"], self.trans["invalid_url"])
            return

        complainant_mention = f"<@{complainant_mention}>"
        accused_mention = f"<@{accused_mention}>"

        message = (
            f"**{self.trans['complainant_mention']}**\n{complainant_mention}\n"
            f"**{self.trans['complainant_clip']}**\n{complainant_clip}\n\n"
            f"**{self.trans['accused_mention']}**\n{accused_mention}\n"
            f"**{self.trans['accused_clip']}**\n{accused_clip}\n\n"
            f"**{self.trans['ban_link']}**\n{ban_link if ban_link else 'Not Available'}"
        )

        pyperclip.copy(message)

        complaint = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "type": "technical",
            "complainant_mention": complainant_mention.strip('<@>'),
            "complainant_clip": complainant_clip,
            "accused_mention": accused_mention.strip('<@>'),
            "accused_clip": accused_clip,
            "ban_link": ban_link,
            "timestamp": datetime.now().strftime("%m/%d %I:%M %p").lower()
        }
        self.complaints.append(complaint)
        self.save_complaints()

        success = send_to_webhook(message, self.webhooks.get("technical", ""))
        messagebox.showinfo(self.trans["success"] if success else self.trans["partial_success"],
                            self.trans["message_generated_copied"] + (self.trans["sent_to_webhook"] if success else ""))

    def generate_create_warn_message(self):
        player_discord_id = self.entry_player_discord_id.get()
        player_info = self.entry_player_info.get()
        reason = self.entry_reason.get()
        ban_time = self.ban_time_var.get()
        is_banned = self.is_banned_var.get()

        # Validate inputs
        if not player_discord_id or not player_info or not reason or not ban_time or not is_banned:
            messagebox.showerror(self.trans["error"], self.trans["required_fields"])
            return
        if not player_discord_id.isdigit():
            messagebox.showerror(self.trans["error"], self.trans["invalid_discord_id"])
            return

        # Format the message with triple backticks around values
        message = (
            "Player Discord ID\n"
            f"```{player_discord_id}```\n"
            "Player Info\n"
            f"```{player_info}```\n"
            "Reason\n"
            f"```{reason}```\n"
            "Ban Time\n"
            f"```{ban_time}```\n"
            "is Player Banned ?\n"
            f"```{is_banned}```"
        )

        pyperclip.copy(message)

        complaint = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "type": "create_warn",
            "player_discord_id": player_discord_id,
            "player_info": player_info,
            "reason": reason,
            "ban_time": ban_time,
            "is_banned": is_banned,
            "timestamp": datetime.now().strftime("%m/%d %I:%M %p").lower()
        }
        self.complaints.append(complaint)
        self.save_complaints()

        success = send_to_webhook(message, self.webhooks.get("create_warn", ""))
        messagebox.showinfo(self.trans["success"] if success else self.trans["partial_success"],
                            self.trans["message_generated_copied"] + (self.trans["sent_to_webhook"] if success else ""))

    def generate_create_ban_message(self):
        player_discord_id = self.entry_ban_player_discord_id.get()
        player_info = self.entry_ban_player_info.get()
        reason = self.entry_ban_reason.get()
        evidence = self.entry_ban_evidence.get()
        is_banned = self.ban_is_banned_var.get()

        # Validate inputs
        if not player_discord_id or not player_info or not reason or not evidence or not is_banned:
            messagebox.showerror(self.trans["error"], self.trans["required_fields"])
            return
        if not player_discord_id.isdigit():
            messagebox.showerror(self.trans["error"], self.trans["invalid_discord_id"])
            return

        # Format the message with triple backticks around values
        message = (
            "Player Discord ID\n"
            f"```{player_discord_id}```\n"
            "Player Info\n"
            f"```{player_info}```\n"
            "Reason\n"
            f"```{reason}```\n"
            "Evidence\n"
            f"```{evidence}```\n"
            "is Player Banned ?\n"
            f"```{is_banned}```"
        )

        pyperclip.copy(message)

        complaint = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "type": "create_ban",
            "player_discord_id": player_discord_id,
            "player_info": player_info,
            "reason": reason,
            "evidence": evidence,
            "is_banned": is_banned,
            "timestamp": datetime.now().strftime("%m/%d %I:%M %p").lower()
        }
        self.complaints.append(complaint)
        self.save_complaints()

        success = send_to_webhook(message, self.webhooks.get("create_ban", ""))
        messagebox.showinfo(self.trans["success"] if success else self.trans["partial_success"],
                            self.trans["message_generated_copied"] + (self.trans["sent_to_webhook"] if success else ""))

    def save_webhooks(self):
        self.webhooks["warning"] = self.entry_warning_webhook.get()
        self.webhooks["technical"] = self.entry_technical_webhook.get()
        self.webhooks["create_warn"] = self.entry_createwarn_webhook.get()
        self.webhooks["create_ban"] = self.entry_createban_webhook.get()

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as file:
                json.dump(self.webhooks, file, ensure_ascii=False, indent=4)
            messagebox.showinfo("Success", "Webhooks saved successfully!")
        except Exception as e:
            print(f"Error saving webhooks: {e}")
            messagebox.showerror("Error", f"Failed to save webhooks: {str(e)}")

    def update_complaints_list(self):
        for widget in self.complaints_list_container.winfo_children():
            widget.destroy()

        if not self.complaints:
            no_complaints_label = ctk.CTkLabel(self.complaints_list_container,
                                               text=self.trans["no_complaints"],
                                               font=("Cairo", 18), text_color=self.text_color)
            no_complaints_label.pack(pady=20)
            return

        for complaint in self.complaints:
            frame = ctk.CTkFrame(self.complaints_list_container, fg_color=self.frame_bg, corner_radius=10)
            frame.pack(fill="x", pady=10)

            complaint_id = complaint.get("id", "Not Specified")
            complaint_type = self.trans["support_warn"] if complaint.get("type") == "warning" else self.trans["record_technical"] if complaint.get("type") == "technical" else self.trans["create_warn"] if complaint.get("type") == "create_warn" else self.trans["create_ban"]
            label = ctk.CTkLabel(frame, text=f"{complaint_type} - ID: {complaint_id}",
                                 font=("Cairo", 14), text_color=self.primary_color)
            label.pack(side="left", padx=10)

            edit_button = ctk.CTkButton(frame, text=self.trans["edit_complaint"],
                                        font=("Cairo", 14), fg_color=self.primary_color,
                                        hover_color=self.secondary_color, corner_radius=20, width=100,
                                        command=lambda c=complaint: self.show_edit_complaint(c))
            edit_button.pack(side="right", padx=10)

            delete_button = ctk.CTkButton(frame, text=self.trans["delete"],
                                          font=("Cairo", 14), fg_color="#EF5350",
                                          hover_color="#F06292", corner_radius=20, width=100,
                                          command=lambda c=complaint: self.delete_complaint(c))
            delete_button.pack(side="right", padx=10)

    def save_edited_complaint(self):
        if not self.current_complaint:
            return

        self.current_complaint["discord_id"] = self.edit_fields["discord_id"].get()
        self.current_complaint["person_info"] = self.edit_fields["person_info"].get()
        self.current_complaint["warn_ban"] = self.edit_warn_ban_var.get()
        self.current_complaint["person_id"] = self.edit_person_id_var.get() if self.edit_person_id_var.get() == "Offline" else self.edit_person_id_manual.get()
        self.current_complaint["violation"] = self.edit_fields["violation"].get()
        self.current_complaint["decision_source"] = self.edit_fields["decision_source"].get()
        self.current_complaint["complainant_mention"] = self.edit_fields["complainant_mention"].get()
        self.current_complaint["complainant_clip"] = self.edit_fields["complainant_clip"].get()
        self.current_complaint["accused_mention"] = self.edit_fields["accused_mention"].get()
        self.current_complaint["accused_clip"] = self.edit_fields["accused_clip"].get()
        self.current_complaint["ban_link"] = self.edit_fields["ban_link"].get()

        self.save_complaints()
        messagebox.showinfo(self.trans["success"], self.trans["changes_saved"])
        self.show_complaints_list()

    def delete_complaint(self, complaint):
        if messagebox.askyesno(self.trans["confirm_delete"], self.trans["confirm_delete"]):
            self.complaints.remove(complaint)
            self.save_complaints()
            self.update_complaints_list()

    def export_to_csv(self):
        if not self.complaints:
            messagebox.showinfo(self.trans["error"], self.trans["no_complaints"])
            return

        filename = f"complaints_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.complaints[0].keys())
            writer.writeheader()
            writer.writerows(self.complaints)
        messagebox.showinfo(self.trans["success"], f"Exported to {filename}")

    def load_complaints(self):
        file_path = "complaints.json"
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    return json.load(file)
            except Exception as e:
                print(f"Error loading complaints: {e}")
        return []

    def save_complaints(self):
        file_path = "complaints.json"
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(self.complaints, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving complaints: {e}")

    def load_webhooks(self):
        default_webhooks = {
            "warning": "",
            "technical": "",
            "create_warn": "",
            "create_ban": ""
        }
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as file:
                    return json.load(file)
            except Exception as e:
                print(f"Error loading webhooks: {e}")
        return default_webhooks

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = App()
    app.mainloop()