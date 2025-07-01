# time_tracker.py

import os
import sys
import json
import shutil
from datetime import datetime, date, timedelta

# ==============================================================================
# BEGIN: Embedded Python Tkinter Fix
# ==============================================================================
site_packages_path = None
for path in sys.path:
    if 'site-packages' in path and os.path.isdir(path):
        site_packages_path = path
        break

if site_packages_path:
    tcl_lib_path = os.path.join(site_packages_path, 'tcl')
    if os.path.isdir(tcl_lib_path):
        os.environ['TCL_LIBRARY'] = os.path.join(tcl_lib_path, 'tcl8.6')
        os.environ['TK_LIBRARY'] = os.path.join(tcl_lib_path, 'tk8.6')
# ==============================================================================
# END: Embedded Python Tkinter Fix
# ==============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import ttkbootstrap as bs
from ttkbootstrap.constants import *
from ttkbootstrap.toast import ToastNotification
from ttkbootstrap.tooltip import ToolTip

DATA_FILE = "time_tracker_data.json"

class CollapsibleFrame(ttk.Frame):
    def __init__(self, parent, text="", bootstyle=DEFAULT, collapsed=True, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.columnconfigure(1, weight=1)
        self.text = text
        self.bootstyle = bootstyle
        
        self.header_frame = ttk.Frame(self, bootstyle=self.bootstyle)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky=EW)
        
        self.toggle_button = ttk.Button(self.header_frame, text="▶", width=4, command=self.toggle, bootstyle=f"{self.bootstyle}-link")
        self.toggle_button.pack(side=LEFT)
        
        self.header_label = ttk.Label(self.header_frame, text=self.text, bootstyle=f"{self.bootstyle}inverse")
        self.header_label.pack(side=LEFT, fill=X, expand=YES)
        self.header_label.bind("<Button-1>", self.toggle)
        
        self.content_frame = ttk.Frame(self, padding=(15, 10))
        
        self.is_collapsed = collapsed
        if not self.is_collapsed:
            self.content_frame.grid(row=1, column=0, columnspan=2, sticky=NSEW)
            self.toggle_button.configure(text="▼")
        else:
             self.toggle_button.configure(text="▶")


    def toggle(self, event=None):
        if self.is_collapsed:
            self.content_frame.grid(row=1, column=0, columnspan=2, sticky=NSEW)
            self.toggle_button.configure(text="▼")
            self.is_collapsed = False
        else:
            self.content_frame.grid_forget()
            self.toggle_button.configure(text="▶")
            self.is_collapsed = True

class TimeTracker(bs.Window):
    @staticmethod
    def _load_initial_settings():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('settings', {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def __init__(self):
        settings = TimeTracker._load_initial_settings()
        theme = settings.get("theme", "darkly")

        super().__init__(themename=theme)
        
        self.title("Simple Time Tracker")
        self.geometry(settings.get("window_geometry", "600x700"))
        self.minsize(500, 550)
        
        self.bracket_style = settings.get("bracket_style", "full_width") # "full_width" for 【】 or "square" for []

        self.timer_running = False
        self.start_time = None
        self.all_categories = {}
        self.all_activities = {}
        self.current_date = date.today()
        self.current_category_filter = "All"
        self.current_timer_category = None
        
        self.pomodoro_mode_on = tk.BooleanVar(value=False)
        self.pomodoro_state = "Idle"
        self.pomodoro_work_minutes = tk.IntVar(value=25)
        self.pomodoro_break_minutes = tk.IntVar(value=5)
        self.pomodoro_end_time = None
        
        self.after_id = None
        self.tree_item_to_activity_index = {}

        self._create_menu(settings)
        self._create_widgets()
        self._setup_styles()
        
        self.load_data(settings)
        
        display_columns = settings.get('display_columns')
        if isinstance(display_columns, (list, tuple)) and all(c in self.columns_map for c in display_columns):
            self.activity_tree["displaycolumns"] = tuple(display_columns)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_live_timer_display()
        self.bind_shortcuts()
        self.select_category_filter(self.current_category_filter)

    def _create_menu(self, settings):
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Data...", command=self.backup_data)
        file_menu.add_command(label="Restore from Backup...", command=self.restore_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=lambda: self.on_closing())

        view_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="View", menu=view_menu)
        
        self.theme_var = tk.StringVar(value=settings.get("theme", "darkly"))
        theme_submenu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_submenu)
        theme_submenu.add_radiobutton(label="Dark", variable=self.theme_var, value="darkly", command=self.toggle_theme)
        theme_submenu.add_radiobutton(label="Light", variable=self.theme_var, value="litera", command=self.toggle_theme)

    def toggle_theme(self):
        new_theme = self.theme_var.get()
        self.style.theme_use(new_theme)
        self._setup_styles()
        self.canvas.config(background=self.style.colors.bg)

    def _create_widgets(self):
        container = ttk.Frame(self)
        container.pack(fill=BOTH, expand=YES)
        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=20)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.scrollable_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        
        self.canvas.bind_all("<MouseWheel>", self.handle_mousewheel)
        
        main_frame = self.scrollable_frame
        
        date_nav_frame = ttk.Frame(main_frame)
        date_nav_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Button(date_nav_frame, text="◄ Prev", command=self.prev_day, bootstyle="secondary").pack(side=LEFT, padx=(0, 5))
        self.date_var = tk.StringVar()
        self.date_entry = ttk.Entry(date_nav_frame, textvariable=self.date_var, width=12, justify='center')
        self.date_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(date_nav_frame, text="Go", command=self.on_date_go, bootstyle="info-outline").pack(side=LEFT, padx=5)
        ttk.Button(date_nav_frame, text="Next ►", command=self.next_day, bootstyle="secondary").pack(side=LEFT, padx=5)
        ttk.Button(date_nav_frame, text="Today", command=self.go_to_today, bootstyle="info").pack(side=LEFT, padx=(5, 0))

        timer_frame = ttk.LabelFrame(main_frame, text="Timer", padding=15)
        timer_frame.pack(fill=X, pady=10)

        top_input_frame = ttk.Frame(timer_frame)
        top_input_frame.pack(fill=X, expand=True, pady=(0, 10))
        top_input_frame.columnconfigure(1, weight=1)

        ttk.Label(top_input_frame, text="Category:").grid(row=0, column=0, sticky=W, padx=(0, 5))
        self.timer_category_var = tk.StringVar()
        self.timer_category_menu = ttk.Combobox(top_input_frame, textvariable=self.timer_category_var, state="readonly", width=15)
        self.timer_category_menu.grid(row=1, column=0, sticky=EW, pady=(2, 0))
        self.timer_category_menu.bind("<<ComboboxSelected>>", self.on_timer_category_select)

        ttk.Label(top_input_frame, text="What are you working on?").grid(row=0, column=1, sticky=W, padx=(10, 0))
        self.activity_name_entry = ttk.Entry(top_input_frame, font=("Helvetica", 12))
        self.activity_name_entry.grid(row=1, column=1, sticky=EW, padx=(10, 0), pady=(2, 0))

        self.timer_label = ttk.Label(timer_frame, text="00:00:00", font=("Segment7", 48), bootstyle="success")
        self.timer_label.pack(pady=5)

        self.start_stop_button = ttk.Button(timer_frame, text="Start", bootstyle="success", command=self.toggle_timer, width=15)
        self.start_stop_button.pack(pady=5)
        
        self.pomo_collapsible_frame = CollapsibleFrame(main_frame, text="Pomodoro Timer", bootstyle=SECONDARY)
        self.pomo_collapsible_frame.pack(fill=X, pady=10)
        pomo_frame = self.pomo_collapsible_frame.content_frame

        pomo_top_frame = ttk.Frame(pomo_frame)
        pomo_top_frame.pack(fill=X, expand=YES, pady=5)
        ttk.Checkbutton(pomo_top_frame, text="Enable Pomodoro Mode", variable=self.pomodoro_mode_on, bootstyle="round-toggle", command=self.on_pomodoro_toggle).pack(side=LEFT)
        self.pomo_status_label = ttk.Label(pomo_top_frame, text="Status: Idle", font=("Helvetica", 10, "italic"))
        self.pomo_status_label.pack(side=RIGHT)
        pomo_settings_frame = ttk.Frame(pomo_frame)
        pomo_settings_frame.pack(fill=X, expand=YES, pady=5)
        ttk.Label(pomo_settings_frame, text="Work (min):").pack(side=LEFT, padx=(0, 5))
        self.pomo_work_spinbox = ttk.Spinbox(pomo_settings_frame, from_=1, to=120, textvariable=self.pomodoro_work_minutes, width=5)
        self.pomo_work_spinbox.pack(side=LEFT, padx=(0, 20))
        ttk.Label(pomo_settings_frame, text="Break (min):").pack(side=LEFT, padx=(0, 5))
        self.pomo_break_spinbox = ttk.Spinbox(pomo_settings_frame, from_=1, to=60, textvariable=self.pomodoro_break_minutes, width=5)
        self.pomo_break_spinbox.pack(side=LEFT)

        self.category_collapsible_frame = CollapsibleFrame(main_frame, text="Category Management", bootstyle=SECONDARY)
        self.category_collapsible_frame.pack(fill=X, pady=10)
        category_section = self.category_collapsible_frame.content_frame

        add_cat_frame = ttk.Frame(category_section)
        add_cat_frame.pack(fill=X, pady=(10, 10))
        self.category_entry = ttk.Entry(add_cat_frame, bootstyle="info", width=20)
        self.category_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        self.category_entry.insert(0, "Add a new category")
        self.category_entry.bind("<FocusIn>", self.clear_placeholder)
        self.category_entry.bind("<FocusOut>", self.set_placeholder)
        
        self.bracket_toggle_button = ttk.Button(
            add_cat_frame, 
            text="", 
            command=self.toggle_bracket_style, 
            bootstyle="outline-secondary", 
            width=3
        )
        self.bracket_toggle_button.pack(side=LEFT, padx=(0, 5))
        self._update_bracket_button_display() # Set initial state
        ToolTip(self.bracket_toggle_button, "Click to toggle display format between 【】 and []")
        
        ttk.Button(add_cat_frame, text="Add", command=self.add_category, bootstyle="info").pack(side=LEFT)
        self.category_buttons_frame = ttk.Frame(category_section)
        self.category_buttons_frame.pack(fill=X, pady=5)

        activities_section = ttk.LabelFrame(main_frame, text="Activities Log", padding=15)
        activities_section.pack(fill=BOTH, expand=YES, pady=10)
        activities_header = ttk.Frame(activities_section)
        activities_header.pack(fill=X, pady=(0, 10))
        ttk.Button(activities_header, text="Copy All", command=self.copy_all_activities, bootstyle="link").pack(side=LEFT)
        ttk.Button(activities_header, text="+ Add Manually", command=self.open_manual_add_window, bootstyle="info-link").pack(side=LEFT, padx=10)
        ttk.Button(activities_header, text="Export to TXT", command=self.export_to_txt, bootstyle="success-link").pack(side=LEFT, padx=10)
        total_time_frame = ttk.Frame(activities_header)
        total_time_frame.pack(side=RIGHT)
        self.total_time_label = ttk.Label(total_time_frame, text="0s", font=("Helvetica", 12, "bold"), bootstyle="primary", cursor="hand2")
        self.total_time_label.pack(side=RIGHT)
        self.total_time_text_label = ttk.Label(total_time_frame, text="Total Time: ", cursor="hand2")
        self.total_time_text_label.pack(side=RIGHT)
        total_time_frame.bind("<Button-1>", self.copy_category_total_time)
        self.total_time_label.bind("<Button-1>", self.copy_category_total_time)
        self.total_time_text_label.bind("<Button-1>", self.copy_category_total_time)
        
        tree_container = ttk.Frame(activities_section)
        tree_container.pack(fill=BOTH, expand=YES)

        self.columns_map = {"time": "Time Range", "activity": "Activity", "duration": "Duration", "copy": "Copy"}
        self.activity_tree = ttk.Treeview(tree_container, columns=list(self.columns_map.keys()), show="headings", height=10)

        x_scrollbar = ttk.Scrollbar(tree_container, orient=HORIZONTAL, command=self.activity_tree.xview)
        self.activity_tree.configure(xscrollcommand=x_scrollbar.set)
        
        x_scrollbar.pack(side=BOTTOM, fill=X)
        self.activity_tree.pack(side=LEFT, fill=BOTH, expand=YES)
        
        self.setup_activity_tree()

    def _setup_styles(self):
        theme_name = self.style.theme.name
        if theme_name == 'darkly':
            heading_bg_color = "#333333"
        else: 
            heading_bg_color = "#E5E5E5"

        self.style.configure("Treeview.Heading", background=heading_bg_color, font=('Helvetica', 10, 'bold'))
        self.style.configure("Treeview", rowheight=25)

    def setup_activity_tree(self):
        for col_id, col_text in self.columns_map.items():
            self.activity_tree.heading(col_id, text=col_text)

        self.activity_tree.column("time", anchor=W, width=120, stretch=False)
        self.activity_tree.column("activity", anchor=W, width=250, stretch=False)
        self.activity_tree.column("duration", anchor=E, width=100, stretch=False)
        self.activity_tree.column("copy", anchor=CENTER, width=50, stretch=False, minwidth=50)
        
        self.activity_context_menu = tk.Menu(self, tearoff=0)
        self.activity_context_menu.add_command(label="Edit Activity", command=self.edit_selected_activity)
        self.activity_context_menu.add_separator()
        
        self.activity_context_menu.add_command(label="Display: Time First", command=lambda: self.reorder_columns(time_first=True))
        self.activity_context_menu.add_command(label="Display: Activity First", command=lambda: self.reorder_columns(time_first=False))
        self.activity_context_menu.add_separator()
        
        self.activity_context_menu.add_command(label="Delete", command=self.delete_selected_activity)
        
        self.activity_tree.bind("<Button-3>", self.show_activity_context_menu)
        self.activity_tree.bind("<Button-1>", self.on_tree_click)

    def _update_bracket_button_display(self):
        if self.bracket_style == "square":
            self.bracket_toggle_button.config(text="[]", bootstyle="success")
        else:
            self.bracket_toggle_button.config(text="【】", bootstyle="secondary")

    def toggle_bracket_style(self):
        if self.bracket_style == "square":
            self.bracket_style = "full_width"
        else:
            self.bracket_style = "square"
        self._update_bracket_button_display()
        self.display_data_for_date(self.current_date)

    def on_closing(self):
        if self.timer_running:
            if not messagebox.askokcancel("Timer Running", "A timer is running. Are you sure you want to quit?"):
                return
            self.force_stop_timer()
        
        self.save_all_data()
        self.destroy()
        
    def save_all_data(self):
        data_to_save = {
            'categories': [name for name in self.all_categories if name != 'All'], 
            'activities': self.all_activities,
            'settings': {
                'theme': self.style.theme.name,
                'window_geometry': self.geometry(),
                'display_columns': self._get_current_display_columns(),
                'bracket_style': self.bracket_style,
            }
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

    def load_data(self, settings):
        self._create_category_button('All', allow_delete=False)
        if not os.path.exists(DATA_FILE):
            default_cats = ["学习", "工作", "个人", "午休"]
            for cat in default_cats:
                self._create_category_button(cat)
            self.save_all_data()
        else:
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for name in data.get('categories', []):
                    if name not in self.all_categories:
                        self._create_category_button(name)
                self.all_activities = data.get('activities', {})
                
            except (json.JSONDecodeError, KeyError) as e:
                messagebox.showerror("Load Error", f"Could not load data file. It might be corrupted. Error: {e}")
        
        self.update_timer_category_menu()
        self.go_to_today()

    def backup_data(self):
        if not os.path.exists(DATA_FILE):
            messagebox.showwarning("No Data", "There is no data file to back up.")
            return

        initial_filename = f"time_tracker_backup_{date.today().strftime('%Y%m%d')}.json"
        backup_path = filedialog.asksaveasfilename(
            title="Save Backup As",
            initialfile=initial_filename,
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if backup_path:
            try:
                self.save_all_data()
                shutil.copy(DATA_FILE, backup_path)
                ToastNotification(title="Backup Successful", message=f"Data backed up to {os.path.basename(backup_path)}", bootstyle=SUCCESS).show_toast()
            except Exception as e:
                messagebox.showerror("Backup Error", f"Failed to create backup.\nError: {e}")

    def restore_data(self):
        if not messagebox.askokcancel( "Confirm Restore", "This will overwrite all current data with the backup file.\nThis action CANNOT be undone.\n\nAre you sure you want to continue?"):
            return

        backup_path = filedialog.askopenfilename( title="Select Backup File to Restore", filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        
        if backup_path:
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                
                shutil.copy(backup_path, DATA_FILE)
                
                messagebox.showinfo("Restore Successful", "Data has been restored.\nPlease restart the application for the changes to take effect.")
                self.destroy()
                
            except json.JSONDecodeError:
                messagebox.showerror("Restore Error", "The selected file is not a valid JSON backup file.")
            except Exception as e:
                messagebox.showerror("Restore Error", f"Failed to restore data.\nError: {e}")
                
    def reorder_columns(self, time_first=True):
        if time_first:
            self.activity_tree["displaycolumns"] = ("time", "activity", "duration", "copy")
        else:
            self.activity_tree["displaycolumns"] = ("activity", "time", "duration", "copy")

    def bind_shortcuts(self):
        self.bind("<Control-s>", lambda event: self.toggle_timer()); self.bind("<Control-S>", lambda event: self.toggle_timer())
        self.bind("<Control-n>", lambda event: self.category_entry.focus_set()); self.bind("<Control-N>", lambda event: self.category_entry.focus_set())
        self.bind("<Control-m>", lambda event: self.open_manual_add_window()); self.bind("<Control-M>", lambda event: self.open_manual_add_window())

    def on_pomodoro_toggle(self):
        if self.timer_running: self.force_stop_timer()
        self.timer_label.config(text="00:00:00", bootstyle="success")

    def handle_mousewheel(self, event):
        if self.scrollbar.winfo_ismapped(): self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        _, _, _, content_height = self.canvas.bbox("all"); canvas_height = self.canvas.winfo_height()
        if content_height > canvas_height:
            if not self.scrollbar.winfo_ismapped(): self.scrollbar.pack(side=RIGHT, fill=Y)
        else:
            if self.scrollbar.winfo_ismapped(): self.scrollbar.pack_forget()

    def on_canvas_configure(self, event): self.canvas.itemconfig(self.canvas_window, width=event.width)

    def on_date_go(self):
        date_str = self.date_var.get()
        try:
            new_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            self.display_data_for_date(new_date)
        except ValueError:
            messagebox.showerror("Invalid Format", "Please enter the date in YYYY-MM-DD format.")

    def change_day(self, days_delta):
        self.current_date += timedelta(days=days_delta)
        self.display_data_for_date(self.current_date)

    def prev_day(self): self.change_day(-1)
    def next_day(self): self.change_day(1)
    def go_to_today(self): self.display_data_for_date(date.today())
    
    def display_data_for_date(self, target_date):
        self.current_date = target_date
        self.date_var.set(self.current_date.strftime("%Y-%m-%d"))
        date_str = self.current_date.strftime("%Y-%m-%d")
        activities_for_day = self.all_activities.get(date_str, [])
        self.recalculate_totals_for_day(activities_for_day)
        self._populate_activities_tree(activities_for_day, self.current_category_filter)
        self.update_total_time_display()

    def recalculate_totals_for_day(self, activities):
        for cat_data in self.all_categories.values(): cat_data['total'] = timedelta(0)
        for activity in activities:
            duration = timedelta(seconds=activity.get('duration_seconds', 0))
            category = activity.get('category')
            if category in self.all_categories and category != "All": 
                self.all_categories[category]['total'] += duration
            self.all_categories['All']['total'] += duration
        self.update_category_buttons()

    def add_category(self):
        new_cat_name = self.category_entry.get().strip()
        if not new_cat_name or new_cat_name == "Add a new category":
            return
        
        if new_cat_name in self.all_categories:
            messagebox.showwarning("Duplicate Category", f"The category '{new_cat_name}' already exists.")
            return

        self.all_categories[new_cat_name] = {'total': timedelta(0)}
        self._create_category_button(new_cat_name)
        self.update_timer_category_menu()
        self.category_entry.delete(0, END)
        self.set_placeholder(None)
        self.save_all_data()
    
    def _create_category_button(self, name, allow_delete=True):
        if 'frame' in self.all_categories.get(name, {}): return
        
        button_frame = ttk.Frame(self.category_buttons_frame)
        button_frame.pack(side=LEFT, padx=3, pady=3, anchor='nw') 
        
        button = ttk.Button(button_frame, text=f"{name} 0s", bootstyle="secondary-outline",
                            command=lambda n=name: self.select_category_filter(n))
        button.pack(side=LEFT, fill=X, expand=YES)

        if allow_delete:
            delete_button = ttk.Button(button_frame, text="X", bootstyle="danger-link", width=2, command=lambda n=name: self.delete_category(n))
            delete_button.pack(side=LEFT)
            
        if name not in self.all_categories:
            self.all_categories[name] = {'total': timedelta(0)}
            
        self.all_categories[name]['button'] = button
        self.all_categories[name]['frame'] = button_frame


    def delete_category(self, name):
        if name == 'All' or name not in self.all_categories: return
        if self.timer_running and self.current_timer_category == name: messagebox.showwarning("Warning", "Cannot delete the currently active category."); return
        
        has_activities = any(act['category'] == name for day_activities in self.all_activities.values() for act in day_activities)
        if has_activities: messagebox.showwarning("Warning", f"Cannot delete category '{name}' because it has recorded activities. Please re-assign or delete those activities first."); return
        
        if messagebox.askokcancel("Confirm Delete", f"Are you sure you want to permanently delete the '{name}' category?"):
            self.all_categories[name]['frame'].destroy()
            del self.all_categories[name]
            self.update_timer_category_menu()
            if self.current_category_filter == name: self.select_category_filter('All')
            self.save_all_data()

    def select_category_filter(self, name):
        self.current_category_filter = name
        if name in self.all_categories:
            self.timer_category_var.set(name)
        self.update_category_button_styles()

        date_str = self.current_date.strftime("%Y-%m-%d")
        activities_for_day = self.all_activities.get(date_str, [])
        self._populate_activities_tree(activities_for_day, self.current_category_filter)
        self.update_total_time_display()

    def on_timer_category_select(self, event=None):
        selected_cat = self.timer_category_var.get()
        if self.timer_running:
            self.current_timer_category = selected_cat if selected_cat != "All" else None
        self.select_category_filter(selected_cat)
        
    def update_category_button_styles(self):
        active_filter = self.current_category_filter
        
        for name, data in self.all_categories.items():
            if 'button' not in data: continue
            
            if self.timer_running and name == self.current_timer_category:
                data['button'].config(bootstyle="info")
            elif name == active_filter:
                data['button'].config(bootstyle="success")
            else:
                data['button'].config(bootstyle="secondary-outline")


    def log_activity(self, category, name, start, end, duration, date_to_log, notes=""):
        activity_data = {'category': category, 'name': name, 'start': start.strftime('%H:%M'), 'end': end.strftime('%H:%M'), 'duration_seconds': duration.total_seconds(), 'notes': notes}
        date_str = date_to_log.strftime("%Y-%m-%d")
        if date_str not in self.all_activities: self.all_activities[date_str] = []
        self.all_activities[date_str].append(activity_data)
        self.display_data_for_date(date_to_log)

    def edit_selected_activity(self):
        selection = self.activity_tree.selection()
        if not selection: return
        item_id = selection[0]
        if item_id in self.tree_item_to_activity_index:
            activity_index = self.tree_item_to_activity_index[item_id]
            activity_data = self.all_activities[self.current_date.strftime("%Y-%m-%d")][activity_index]
            ManualAddWindow(self, edit_mode=True, activity_index=activity_index, activity_data=activity_data, activity_date=self.current_date)

    def delete_selected_activity(self):
        selection = self.activity_tree.selection()
        if not selection: return
        item_id = selection[0]
        if not messagebox.askokcancel("Confirm Delete", "Are you sure you want to permanently delete this activity record?"): return
        
        if item_id in self.tree_item_to_activity_index:
            activity_index = self.tree_item_to_activity_index[item_id]
            date_str = self.current_date.strftime("%Y-%m-%d")
            self.all_activities[date_str].pop(activity_index)
            if not self.all_activities[date_str]: del self.all_activities[date_str]
            self.display_data_for_date(self.current_date)
            self.save_all_data()

    def toggle_timer(self):
        if self.timer_running: 
            self.force_stop_timer()
        else:
            if self.pomodoro_mode_on.get(): 
                self.start_pomodoro_work()
            else: 
                self.start_standard_timer()

    def force_stop_timer(self):
        if not self.timer_running: return
        start_date = self.start_time.date()
        
        if not self.pomodoro_mode_on.get():
            end_time = datetime.now()
            duration = end_time - self.start_time
            activity_name = self.activity_name_entry.get().strip()
            self.log_activity(self.current_timer_category, activity_name, self.start_time, end_time, duration, start_date)
        elif self.pomodoro_state == 'Work':
            end_time = datetime.now()
            duration = end_time - self.start_time
            if duration.total_seconds() > 1:
                activity_name = f"{self.activity_name_entry.get().strip()} (Pomodoro)"
                self.log_activity(self.current_timer_category, activity_name, self.start_time, end_time, duration, start_date)
        
        self.timer_running = False
        self.current_timer_category = None
        self.pomodoro_state = "Idle"
        self.pomodoro_end_time = None
        if self.after_id: 
            self.after_cancel(self.after_id)
            self.after_id = None
            
        self.update_live_timer_display()
        self.timer_label.config(bootstyle="success", text="00:00:00")
        self.start_stop_button.config(text="Start", bootstyle="success")
        self.pomo_status_label.config(text="Status: Idle")
        self.update_category_button_styles()
        self.save_all_data()

    def start_standard_timer(self):
        self.current_timer_category = self.timer_category_var.get()
        if self.current_timer_category == "All":
            messagebox.showwarning("No Category Selected", "Please select a specific category (not 'All') to start tracking."); return
        if not self.activity_name_entry.get().strip(): 
            messagebox.showwarning("No Activity Name", "Please enter what you are working on."); return
        
        self.timer_running = True
        self.start_time = datetime.now()
        self.start_stop_button.config(text="Stop", bootstyle="danger")
        self.timer_label.config(bootstyle="info")
        self.update_category_button_styles()
        self.update_live_timer_display()

    def start_pomodoro_work(self):
        self.current_timer_category = self.timer_category_var.get()
        if self.current_timer_category == "All": 
            messagebox.showwarning("No Category Selected", "Please select a category for the Pomodoro session."); return
        if not self.activity_name_entry.get().strip(): 
            messagebox.showwarning("No Activity Name", "Please enter what you are working on."); return

        self.pomodoro_state = "Work"
        self.pomo_status_label.config(text="Status: Work")
        self.timer_running = True
        self.start_time = datetime.now()
        duration = timedelta(minutes=self.pomodoro_work_minutes.get())
        self.pomodoro_end_time = self.start_time + duration
        self.start_stop_button.config(text="Stop", bootstyle="danger")
        self.timer_label.config(bootstyle="info")
        self.update_category_button_styles()
        self.update_live_timer_display()

    def start_pomodoro_break(self):
        self.pomodoro_state = "Break"
        self.pomo_status_label.config(text="Status: Break")
        self.timer_running = True
        self.start_time = datetime.now()
        duration = timedelta(minutes=self.pomodoro_break_minutes.get())
        self.pomodoro_end_time = self.start_time + duration
        self.start_stop_button.config(text="Skip Break", bootstyle="warning")
        self.timer_label.config(bootstyle="success")
        self.current_timer_category = None
        self.update_category_button_styles()
        self.update_live_timer_display()

    def update_live_timer_display(self):
        if self.after_id: 
            self.after_cancel(self.after_id)
            self.after_id = None
            
        if self.timer_running:
            if self.pomodoro_mode_on.get() and self.pomodoro_end_time:
                remaining = self.pomodoro_end_time - datetime.now()
                if remaining.total_seconds() < 0:
                    self.bell()
                    if self.pomodoro_state == 'Work':
                        activity_name = f"{self.activity_name_entry.get().strip()} (Pomodoro)"
                        duration = timedelta(minutes=self.pomodoro_work_minutes.get())
                        end_time = self.start_time + duration
                        self.log_activity(self.current_timer_category, activity_name, self.start_time, end_time, duration, self.start_time.date())
                        self.save_all_data()
                        self.start_pomodoro_break()
                    elif self.pomodoro_state == 'Break': 
                        self.force_stop_timer()
                    return
                display_text = self.format_timedelta_colon(remaining)
            else:
                elapsed_time = datetime.now() - self.start_time
                display_text = self.format_timedelta_colon(elapsed_time)
            
            self.timer_label.config(text=display_text)
            title_state = self.pomodoro_state if self.pomodoro_mode_on.get() and self.pomodoro_state != "Idle" else "Tracking"
            self.title(f"{display_text} - {title_state}")
        else: 
            self.title("Simple Time Tracker")
            
        self.after_id = self.after(200, self.update_live_timer_display)
    
    def _get_current_display_columns(self):
        display_columns = self.activity_tree["displaycolumns"]
        if '#all' in display_columns or not display_columns:
            return self.activity_tree["columns"]
        else:
            return display_columns

    def _populate_activities_tree(self, activities_for_day, category_filter):
        self.tree_item_to_activity_index.clear()
        for item in self.activity_tree.get_children(): self.activity_tree.delete(item)
        
        indexed_activities = list(enumerate(activities_for_day))
        sorted_indexed_activities = sorted(indexed_activities, key=lambda x: datetime.strptime(x[1]['start'], '%H:%M'))
        
        original_columns_order = self.activity_tree["columns"]
        
        prefix, suffix = ("[", "]") if self.bracket_style == "square" else ("【", "】")

        for original_index, activity in sorted_indexed_activities:
            if category_filter == 'All' or activity['category'] == category_filter:
                note_icon = " 📝" if activity.get("notes") else ""
                
                activity_text = f"{prefix}{activity['category']}{suffix} {activity['name']}{note_icon}"
                time_range_text = f"{activity['start']} - {activity['end']}"
                duration_text = self.format_timedelta_hms(timedelta(seconds=activity['duration_seconds']))
                
                values_map = {"time": time_range_text, "activity": activity_text, "duration": duration_text, "copy": "📋"}
                ordered_values = tuple(values_map[col_id] for col_id in original_columns_order)

                item_id = self.activity_tree.insert("", END, values=ordered_values)
                self.tree_item_to_activity_index[item_id] = original_index

                if note_icon:
                    ToolTip(self.activity_tree, text=activity.get("notes", ""), bootstyle=(INFO, INVERSE), for_item=item_id)

    def update_total_time_display(self):
        category_name = self.current_category_filter
        if category_name in self.all_categories:
            total_time = self.all_categories[category_name]['total']
            self.total_time_label.config(text=self.format_timedelta_hms(total_time))
            if category_name == "All": self.total_time_text_label.config(text="Total Time: ")
            else: self.total_time_text_label.config(text=f"{category_name} Total: ")

    def update_category_buttons(self):
        for name, data in self.all_categories.items():
            formatted_time = self.format_timedelta_hms(data['total'])
            if 'button' in data: data['button'].config(text=f"{name} {formatted_time}")
        self.update_category_button_styles()
            
    def update_timer_category_menu(self):
        cat_list = ["All"] + sorted([name for name in self.all_categories if name != 'All'])
        self.timer_category_menu['values'] = cat_list
        if self.timer_category_var.get() not in cat_list:
            self.timer_category_var.set("All")
            self.current_category_filter = "All"
            self.current_timer_category = None

    def open_manual_add_window(self): ManualAddWindow(self, activity_date=self.current_date)
        
    def show_activity_context_menu(self, event):
        item_id = self.activity_tree.identify_row(event.y)
        if item_id: self.activity_tree.selection_set(item_id); self.activity_context_menu.post(event.x_root, event.y_root)

    def on_tree_click(self, event):
        region = self.activity_tree.identify_region(event.x, event.y)
        if region != "cell": return
        
        column_identifier = self.activity_tree.identify_column(event.x)
        column_id = self.activity_tree.column(column_identifier, "id")

        if column_id != "copy": return
        
        item_id = self.activity_tree.identify_row(event.y)
        if item_id in self.tree_item_to_activity_index:
            activity_index = self.tree_item_to_activity_index[item_id]
            date_str = self.current_date.strftime("%Y-%m-%d")
            act = self.all_activities.get(date_str, [])[activity_index]
            copy_text = self.get_formatted_activity_string(act)
            self.clipboard_clear(); self.clipboard_append(copy_text)
            ToastNotification(title="Copied", message=f"Activity '{act['name']}' copied.", duration=2000, bootstyle=SUCCESS).show_toast()
    
    def get_formatted_activity_string(self, activity_data):
        display_order = self._get_current_display_columns()
        prefix, suffix = ("[", "]") if self.bracket_style == "square" else ("【", "】")

        time_str = f"{activity_data['start']}-{activity_data['end']}"
        activity_str = f"{prefix}{activity_data['category']}{suffix} {activity_data['name']}"
        
        try:
            time_index = list(display_order).index('time')
            activity_index = list(display_order).index('activity')
            if time_index < activity_index:
                return f"{time_str} {activity_str}"
            else:
                return f"{activity_str} {time_str}"
        except ValueError:
            return f"{time_str} {activity_str}"

    def copy_category_total_time(self, event=None):
        category_name = self.current_category_filter
        if category_name not in self.all_categories: return
        total_seconds_td = self.all_categories[category_name]['total']
        hours = total_seconds_td.total_seconds() / 3600
        formatted_time_for_copy = f"{hours:.2f}h"
        if category_name == "All": 
            copy_text = f"Total Time：{formatted_time_for_copy}"
        else: 
            copy_text = f"{category_name}时间：{formatted_time_for_copy}"
        self.clipboard_clear(); self.clipboard_append(copy_text)
        ToastNotification(title="Total Time Copied", message=f"Copied as '{copy_text}'", duration=2000, bootstyle=INFO).show_toast()
        
    def export_to_txt(self):
        date_str = self.current_date.strftime("%Y-%m-%d"); activities_for_day = self.all_activities.get(date_str, [])
        if not activities_for_day: messagebox.showinfo("Nothing to Export", "There are no activities on this date to export."); return
        initial_filename = f"{date_str}_report.txt"
        filepath = filedialog.asksaveasfilename(initialfile=initial_filename, defaultextension=".txt", filetypes=[("Text Documents", "*.txt"), ("All Files", "*.*")])
        if not filepath: return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Daily Activities for {date_str}\n\n")
                for act in sorted(activities_for_day, key=lambda x: datetime.strptime(x['start'], '%H:%M')):
                    f.write(self.get_formatted_activity_string(act) + "\n")
                    notes = act.get('notes')
                    if notes: f.write(f"  Notes: {notes}\n")
                f.write("\n" + "="*50 + "\n\n"); f.write("Summary\n\n")
                
                total_time_h = self.all_categories['All']['total'].total_seconds() / 3600
                f.write(f"Total Time：{total_time_h:.2f}h\n")
                
                day_categories = sorted(list({act['category'] for act in activities_for_day}))
                for cat_name in day_categories:
                    if cat_name in self.all_categories:
                        cat_total_h = self.all_categories[cat_name]['total'].total_seconds() / 3600
                        if cat_total_h > 0:
                            f.write(f"{cat_name}时间：{cat_total_h:.2f}h\n")

            ToastNotification("Export Successful", f"Report saved to {os.path.basename(filepath)}", bootstyle=SUCCESS).show_toast()
        except Exception as e: messagebox.showerror("Export Error", f"Failed to save the file.\nError: {e}")

    def copy_all_activities(self):
        date_str = self.current_date.strftime("%Y-%m-%d"); activities_for_day = self.all_activities.get(date_str, [])
        category_filter = self.current_category_filter
        if category_filter == "All": activities_to_copy = activities_for_day
        else: activities_to_copy = [act for act in activities_for_day if act['category'] == category_filter]
        if not activities_to_copy: messagebox.showinfo("Nothing to Copy", f"There are no activities in this view to copy."); return
        
        sorted_activities = sorted(activities_to_copy, key=lambda x: datetime.strptime(x['start'], '%H:%M'))
        report_lines = [self.get_formatted_activity_string(act) for act in sorted_activities]
        
        report = "\n".join(report_lines); self.clipboard_clear(); self.clipboard_append(report)
        ToastNotification(title="Activities Copied", message=f"{len(activities_to_copy)} activities copied.", duration=2000, bootstyle=INFO).show_toast()

    def clear_placeholder(self, event):
        if self.category_entry.get() == "Add a new category": self.category_entry.delete(0, END); self.category_entry.config(bootstyle="primary")

    def set_placeholder(self, event):
        if not self.category_entry.get(): self.category_entry.insert(0, "Add a new category"); self.category_entry.config(bootstyle="info")
            
    @staticmethod
    def format_timedelta_colon(td):
        if td.total_seconds() < 0: td = timedelta(0)
        total_seconds = int(td.total_seconds()); hours, remainder = divmod(total_seconds, 3600); minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
        
    @staticmethod
    def format_timedelta_hms(td):
        total_seconds = int(td.total_seconds())
        if total_seconds <= 0: return "0s"
        hours, remainder = divmod(total_seconds, 3600); minutes, seconds = divmod(remainder, 60); parts = []
        if hours > 0: parts.append(f"{hours}h")
        if minutes > 0: parts.append(f"{minutes}min")
        if seconds > 0: parts.append(f"{seconds}s")
        return "".join(parts) if parts else "0s"

class ManualAddWindow(tk.Toplevel):
    def __init__(self, parent, edit_mode=False, activity_index=None, activity_data=None, activity_date=None):
        super().__init__(parent)
        self.parent = parent; self.edit_mode = edit_mode; self.activity_index = activity_index
        self.activity_data = activity_data; self.activity_date = activity_date
        title = "Edit Activity" if self.edit_mode else "Add Activity Manually"
        self.title(title); self.transient(parent); self.grab_set()
        frame = ttk.Frame(self, padding=20); frame.pack(fill=BOTH, expand=YES)
        self.setup_form(frame); self.center_window()
        if self.edit_mode and self.activity_data: self.populate_fields()
        elif hasattr(self, 'categories') and self.categories:
             self.category_menu.set(self.categories[0])
        self.name_entry.focus_set()

    def setup_form(self, frame):
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Category:").grid(row=0, column=0, sticky=W, pady=5)
        self.category_var = tk.StringVar(); self.categories = [cat for cat in self.parent.all_categories if cat != 'All']
        self.category_menu = ttk.Combobox(frame, textvariable=self.category_var, values=self.categories, state="readonly")
        self.category_menu.grid(row=0, column=1, sticky=EW, pady=5); ttk.Label(frame, text="Activity Name:").grid(row=1, column=0, sticky=W, pady=5)
        self.name_entry = ttk.Entry(frame); self.name_entry.grid(row=1, column=1, sticky=EW, pady=5)
        
        time_frame = ttk.Frame(frame); time_frame.grid(row=2, column=0, columnspan=2, sticky=EW, pady=5)
        time_frame.columnconfigure((0, 2), weight=1); ttk.Label(time_frame, text="Start (HH:MM):").pack(side=LEFT)
        self.start_entry = ttk.Entry(time_frame, width=8); self.start_entry.pack(side=LEFT, padx=5)
        ttk.Label(time_frame, text="End (HH:MM):").pack(side=LEFT)
        self.end_entry = ttk.Entry(time_frame, width=8); self.end_entry.pack(side=LEFT, padx=5)
        
        notes_frame = ttk.LabelFrame(frame, text="Notes", padding=10); notes_frame.grid(row=3, column=0, columnspan=2, sticky=NSEW, pady=10)
        notes_frame.rowconfigure(0, weight=1); notes_frame.columnconfigure(0, weight=1)
        self.notes_text = tk.Text(notes_frame, height=4, wrap=WORD); self.notes_text.grid(row=0, column=0, sticky=NSEW)
        
        frame.rowconfigure(3, weight=1)
        
        button_frame = ttk.Frame(frame); button_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0))
        ttk.Button(button_frame, text="Save", command=self.save_activity, bootstyle="success").pack(side=LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.destroy, bootstyle="secondary").pack(side=LEFT, padx=10)

    def center_window(self):
        self.update_idletasks(); self.minsize(400, 350)
        parent_x, parent_y = self.parent.winfo_x(), self.parent.winfo_y()
        parent_w, parent_h = self.parent.winfo_width(), self.parent.winfo_height()
        win_w, win_h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = parent_x + (parent_w // 2) - (win_w // 2); y = parent_y + (parent_h // 2) - (win_h // 2)
        self.geometry(f"+{x}+{y}")

    def populate_fields(self):
        self.category_var.set(self.activity_data.get('category')); self.name_entry.insert(0, self.activity_data.get('name'))
        self.start_entry.insert(0, self.activity_data.get('start')); self.end_entry.insert(0, self.activity_data.get('end'))
        self.notes_text.insert(END, self.activity_data.get('notes', ''))

    def save_activity(self):
        category, name = self.category_var.get(), self.name_entry.get().strip()
        start_str, end_str = self.start_entry.get().strip(), self.end_entry.get().strip()
        notes = self.notes_text.get("1.0", END).strip()
        
        if not all([category, name, start_str, end_str]): messagebox.showerror("Input Error", "All fields are required.", parent=self); return
        try:
            start_time_obj = datetime.strptime(start_str, "%H:%M").time(); end_time_obj = datetime.strptime(end_str, "%H:%M").time()
        except ValueError: messagebox.showerror("Input Error", "Invalid time format. Please use HH:MM.", parent=self); return
        
        start_dt = datetime.combine(self.activity_date, start_time_obj); end_dt = datetime.combine(self.activity_date, end_time_obj)
        if end_dt <= start_dt: end_dt += timedelta(days=1)
        
        duration = end_dt - start_dt
        new_activity_data = {'category': category, 'name': name, 'start': start_dt.strftime('%H:%M'), 'end': end_dt.strftime('%H:%M'), 'duration_seconds': duration.total_seconds(), 'notes': notes}

        date_str = self.activity_date.strftime("%Y-%m-%d")
        if self.edit_mode:
            self.parent.all_activities[date_str][self.activity_index] = new_activity_data
        else:
            if date_str not in self.parent.all_activities: self.parent.all_activities[date_str] = []
            self.parent.all_activities[date_str].append(new_activity_data)
        
        self.parent.display_data_for_date(self.activity_date)
        self.parent.save_all_data(); self.destroy()

if __name__ == "__main__":
    app = None
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
    except NameError:
        pass
        
    try:
        app = TimeTracker()
        app.mainloop()
    except Exception as e:
        import traceback
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Fatal Error",
            f"An unexpected error occurred and the application must close.\n\nError: {e}\n\nTraceback:\n{traceback.format_exc()}"
        )
        if app:
            app.destroy()