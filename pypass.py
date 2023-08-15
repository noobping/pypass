#!/bin/python

import configparser
import os
import re
import subprocess

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('GdkWayland', '4.0')
gi.require_version('Gtk', '4.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gdk, GdkWayland, Gtk, Gio, Notify


class ConfigManager:
    def __init__(self, file_name='config.ini', app_name='pypass'):
        self.config = configparser.ConfigParser()
        config_path = os.path.expanduser(f'~/.config/{app_name}')
        if not os.path.exists(config_path):
            os.makedirs(config_path)
        self.file_path = os.path.join(config_path, file_name)
        if not os.path.exists(self.file_path):
            self.create_default_config()
        self.load_config()

    def create_default_config(self):
        self.config['Settings'] = {
            'password_store_path': '~/.password-store',
            'filter_valid_files': 'False',
            'auto_sync': 'False',
            'use_folder': 'False',
        }
        self.save()

    def load_config(self):
        self.config.read(self.file_path)

    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)

    def set(self, section, key, value):
        if section not in self.config:
            self.config.add_section(section)
        self.config.set(section, key, value)

    def save(self):
        with open(self.file_path, 'w') as config_file:
            self.config.write(config_file)


class PassWrapper:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def password_store_path(self) -> str:
        return os.path.expanduser(self.config_manager.get('Settings', 'password_store_path'))
    
    def auto_sync(self) -> bool:
        return self.config_manager.get('Settings', 'auto_sync').lower() == 'true'

    def list_files(self, folder=".", query=None) -> [str]:
        if folder == '.':
            root_folder = self.password_store_path()
        else:
            root_folder = os.path.join(self.password_store_path(), folder.lstrip('.'))
        matching_files = []

        # Check if the query is provided
        if query:
            # Split the keywords string into individual keywords
            keywords = query.split()
        else:
            # If no query, set keywords to None
            keywords = None

        # Walk through the directory and its subdirectories
        for root, _, files in os.walk(root_folder):
            for filename in files:
                # Check if the file has a .gpg extension
                if filename.endswith('.gpg'):
                    # If keywords are provided, check if any of the keywords are in the filename
                    if keywords is None or any(keyword in filename for keyword in keywords):
                        # Remove the .gpg extension
                        filename_without_extension = os.path.splitext(filename)[0]

                        # Add the relative path of the matching file (excluding the root directory)
                        relative_path = os.path.relpath(os.path.join(root, filename_without_extension), root_folder)
                        matching_files.append(relative_path)
        return matching_files

    def list_passwords(self, folder='.', query=None) -> [str]:
        filter_valid_files = self.config_manager.get('Settings', 'filter_valid_files').lower() == 'true'

        if query:
            command = ['pass', 'find', query]
        else:
            command = ['pass', 'ls', folder]
            
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8') if result.returncode == 0 else None
        if output is None:
            return None

        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)

        lines = output.split('\n')[1:]  # Skip the first line
        children = []
        current_indent = None
        current_path = []
        for line in lines:
            stripped_line = line.lstrip()
            indent = len(line) - len(stripped_line)
            if current_indent is None:
                current_indent = indent
            if indent == current_indent and (stripped_line.startswith("├──") or stripped_line.startswith("└──")):
                item_name = stripped_line.replace("├──", "").replace("└──", "").strip()
                if folder != '.':
                    item_path = os.path.join(self.password_store_path(), folder.lstrip('.'), item_name)
                else:
                    item_path = os.path.join(self.password_store_path(), item_name)
                    
                if filter_valid_files:
                    file_command = ['file', item_path]
                    file_result = subprocess.run(file_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    file_output = file_result.stdout.decode('utf-8') if file_result.returncode == 0 else None
                    if file_output and ("PGP RSA encrypted session key" in file_output or "directory" in file_output):
                        children.append(item_name)
                else:
                    children.append(item_name)
            elif indent < current_indent:
                break
            elif query and stripped_line.endswith("/"):
                # Update the current path for search results
                current_path.append(stripped_line.rstrip("/"))
            elif query and stripped_line and current_path:
                # Append the item to the current path for search results
                full_path = os.path.join(*current_path, stripped_line)
                children.append(full_path)
                
        return children

    def show_password(self, path) -> str | None:
        command = ['pass', 'show', path]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8') if result.returncode == 0 else None

    def get_otp(self, otp_uri) -> str:
        # Run the pass otp command and return the result
        result = subprocess.run(['pass', 'otp', otp_uri], stdout=subprocess.PIPE)
        return result.stdout.decode().strip()

    def sync(self) -> None:
        if self.auto_sync():
            result = subprocess.run(['pass', 'git', 'fetch'])
            if result.returncode == 0:
                result = subprocess.run(['pass', 'git', 'pull'])
            if result.returncode != 0:
                self.notification('Synchronization failed')

    def save(self, path: str, content: str) -> None:
        process = subprocess.Popen(['pass', 'insert', '--multiline', path], stdin=subprocess.PIPE)
        process.communicate(input=content.encode('utf-8'))
        if process.returncode != 0:
            self.notification('Failed to save the password')
        elif self.auto_sync():
            result = subprocess.run(['pass', 'git', 'push'])
            if result.returncode != 0:
                self.notification('Failed to synchronise the saved password')

    def notification(self, message: str, type: str = 'warning') -> None:
        # Initialize the Notify library if not already done
        if not Notify.is_initted():
            Notify.init("com.github.noobping.pypass")

        # Create and show the notification
        notification = Notify.Notification.new("Password Store", message, f"dialog-{type}")
        notification.show()

    def add_password(path, content) -> bool:
        try:
            proc = subprocess.Popen(['pass', 'insert', '--multiline', path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(input=content.encode('utf-8'))
            
            # Check the return code of the process
            if proc.returncode != 0:
                # This will display the error from the 'pass' command
                notification(stderr.decode('utf-8'), "error")
                return False
            return True
        except Exception as e:
            print(f"Error: {e}")
            notification(f"Error adding password: {e}", "error")
            return False


class Dialog(Gtk.Dialog):
    def __init__(self, parent, title, content, pass_manager):    
        Gtk.Dialog.__init__(self, title=title, transient_for=parent, modal=True)
        self.set_default_size(280, 250)
        self.pass_manager = pass_manager
        self.content = content

        # Header
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)
        self.set_titlebar(header_bar)

        # Edit or view mode
        self.edit_mode = False
        self.edit_button = Gtk.Button()
        self.edit_button.set_icon_name("edit-symbolic")
        self.edit_button.connect("clicked", self.on_edit_button_clicked)
        header_bar.pack_start(self.edit_button)

        # Create a stack to manage the two views
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # Add the grid view to the stack
        self.grid_scrolled_window = self.build_grid(content, parent.pass_manager)
        self.stack.add_titled(self.grid_scrolled_window, "grid", "Grid View")
        self.stack.set_visible_child_name("grid")

        # Create a text view for edit mode
        self.edit_view = Gtk.TextView()
        self.edit_view.get_buffer().set_text(content)
        self.edit_view.set_wrap_mode(Gtk.WrapMode.WORD)

        # Create a scrolled window for the text editor
        text_scrolled_window = Gtk.ScrolledWindow()
        text_scrolled_window.set_vexpand(True)
        text_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        text_scrolled_window.set_child(self.edit_view)

        # Add the text editor to the stack
        self.stack.add_titled(text_scrolled_window, "text", "Text Editor")

        # Add the stack to the dialog box
        dialog_box = self.get_child()
        dialog_box.append(self.stack)

        # Connect the response signal and show the dialog
        self.connect("response", lambda dlg, r: dlg.destroy())

    def build_grid(self, content: str, pass_manager: PassWrapper) -> Gtk.ScrolledWindow:
        grid = Gtk.Grid()
        grid.set_row_spacing(3)
        grid.set_column_spacing(3)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)
        grid.set_margin_start(6)
        grid.set_margin_end(6)
        grid.set_margin_top(6)
        grid.set_margin_bottom(6)

        # Create a scrolled window for the grid view
        grid_scrolled_window = Gtk.ScrolledWindow()
        grid_scrolled_window.set_vexpand(True)
        grid_scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        grid_scrolled_window.set_child(grid)

        # Split the content by lines
        lines = content.split('\n')

        # Handle the first line as the password
        password_label = Gtk.Label(label=lines[0])
        password_label.set_selectable(True)
        password_label.set_wrap(True)
        password_label.set_visible(False)
        grid.attach(password_label, 0, 0, 2, 1)

        show_password_button = Gtk.Button(label=self.to_asterisks(password_label.get_label()))
        show_password_button.connect("clicked", self.on_show_button_clicked, password_label)
        grid.attach(show_password_button, 0, 0, 2, 1)

        copy_password_button = Gtk.Button()
        copy_password_button.set_icon_name("edit-copy-symbolic")
        copy_password_button.connect("clicked", self.on_copy_button_clicked, password_label)
        grid.attach(copy_password_button, 2, 0, 1, 1)

        # Check for OTP and display it
        otp_line = next((line for line in lines[1:] if 'otpauth://' in line), None)
        if otp_line:
            otp = pass_manager.get_otp(self.get_title())
            label_text = Gtk.Label(label="OTP:")
            otp_label = Gtk.Label(label=otp)
            copy_button = Gtk.Button()
            copy_button.set_icon_name("edit-copy-symbolic")
            copy_button.connect("clicked", self.on_copy_button_clicked, otp_label)
            grid.attach(label_text,  0, 1, 1, 1)
            grid.attach(otp_label,   1, 1, 1, 1)
            grid.attach(copy_button, 2, 1, 1, 1)

        # Determine the line ranges for SSH and PGP keys
        ssh_key_start = ssh_key_end = pgp_key_start = pgp_key_end = None

        for i, line in enumerate(lines):
            if "-----BEGIN OPENSSH PRIVATE KEY-----" in line:
                ssh_key_start = i
            if "-----END OPENSSH PRIVATE KEY-----" in line:
                ssh_key_end = i
            if "-----BEGIN PGP PRIVATE KEY BLOCK-----" in line:
                pgp_key_start = i
            if "-----END PGP PRIVATE KEY BLOCK-----" in line:
                pgp_key_end = i

        # Handle SSH key if present
        if ssh_key_start is not None and ssh_key_end is not None:
            self.add_key_widget(grid, '\n'.join(lines[ssh_key_start:ssh_key_end + 1]), len(lines) + 1)

        # Handle PGP key if present
        if pgp_key_start is not None and pgp_key_end is not None:
            self.add_key_widget(grid, '\n'.join(lines[pgp_key_start:pgp_key_end + 1]), len(lines) + 2)

        # Handle the rest of the lines (excluding the OTP line and keys)
        for i, line in enumerate((line for index, line in enumerate(lines[1:]) if line != otp_line and (ssh_key_start is None or not ssh_key_start <= index <= ssh_key_end) and (pgp_key_start is None or not pgp_key_start <= index <= pgp_key_end)), start=2):

            if ':' in line and "otpauth://" not in line:
                # Check if the line follows the "label: value" pattern
                label_text, value_text = line.split(':', 1)
                label_widget = Gtk.Label(label=label_text.strip() + ':', halign=Gtk.Align.END)
                grid.attach(label_widget, 0, i, 1, 1)

                # Create a label for view mode
                value_label = Gtk.Label(label=value_text.strip())
                value_label.set_selectable(True)
                value_label.set_wrap(True)
                value_label.set_visible(False)
                grid.attach(value_label, 1, i, 1, 1)

                show_button = Gtk.Button(label=self.to_asterisks(value_label.get_label()))
                show_button.connect("clicked", self.on_show_button_clicked, value_label)
                grid.attach(show_button, 1, i, 1, 1)

                # Copy button
                copy_button = Gtk.Button()
                copy_button.set_icon_name("edit-copy-symbolic")
                copy_button.connect("clicked", self.on_copy_button_clicked, value_label)
                grid.attach(copy_button, 2, i, 1, 1)
            elif "-----" not in line and "otpauth" not in line:
                label_widget = Gtk.Label(label=line)
                label_widget.set_selectable(True)
                label_widget.set_wrap(True)
                grid.attach(label_widget, 0, i, 2, 1)
        return grid_scrolled_window

    def add_key_widget(self, grid, key_content, row) -> None:
        text_view = Gtk.TextView()
        text_view.get_buffer().set_text(key_content)
        text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        text_view.set_editable(False)
        text_view.set_visible(False)
        grid.attach(text_view, 0, row, 2, 1)

        # Extract the key type from the content
        key_type = "SSH" if "OPENSSH" in key_content else "PGP"

        show_button = Gtk.Button(label=f"Show {key_type} Key")
        show_button.connect("clicked", self.on_show_button_clicked, text_view)
        grid.attach(show_button, 0, row, 2, 1)

        # Copy key
        copy_button = Gtk.Button()
        copy_button.set_icon_name("edit-copy-symbolic")
        copy_button.connect("clicked", self.on_copy_button_clicked, text_view)
        grid.attach(copy_button, 2, row, 1, 1)

    def to_asterisks(self, value) -> str:
        num_asterisks = min(len(value), 25)
        return "*" * num_asterisks

    def on_show_button_clicked(self, button, label) -> None:
        value = not label.get_visible()
        label.set_visible(value)
        button.set_visible(not value)

    def on_copy_button_clicked(self, button, widget) -> None:
        clipboard = Gdk.Display.get_default().get_clipboard()
        if isinstance(widget, Gtk.Label):
            text = widget.get_label()
        elif isinstance(widget, Gtk.TextView):
            buf = widget.get_buffer()
            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        clipboard.set(text)

    def on_edit_button_clicked(self, button) -> None:
        self.edit_button.set_sensitive(False)
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.edit_button.set_icon_name("emblem-ok-symbolic")
            self.stack.set_visible_child_name("text")
        else:
            # If exiting edit mode, save the changes
            buf = self.edit_view.get_buffer()
            updated_content = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            if self.content != updated_content:
                self.pass_manager.save(self.get_title(), updated_content)

                # Rebuild the grid with the updated content
                new_grid_scrolled_window = self.build_grid(updated_content, self.pass_manager)

                # Replace the old grid in the stack
                self.stack.remove(self.grid_scrolled_window)
                self.grid_scrolled_window = new_grid_scrolled_window
                self.stack.add_titled(self.grid_scrolled_window, "grid", "Grid View")

                # Replace the old content
                self.content = updated_content

            # switch to the grid view if not already visible
            self.edit_button.set_icon_name("edit-symbolic")
            self.stack.set_visible_child_name("grid")
        self.edit_button.set_sensitive(True)


class Window(Gtk.ApplicationWindow):
    def __init__(self, pass_manager, config_manager, application, **kwargs):
        super().__init__(application=application, **kwargs)
        self.pass_manager = pass_manager
        self.config_manager = config_manager

        self.set_default_size(300, 300)
        application.create_action('search', self.on_search_button_clicked, ['<primary>f'])

        # Create a ListBox
        self.list_box = Gtk.ListBox()
        self.list_box.connect('row-activated', self.on_row_activated)

        # Create a back button
        self.back_button = Gtk.Button()
        self.back_button.connect('clicked', self.on_back_button_clicked)
        self.back_button.set_icon_name("go-previous-symbolic")

        # Create a header bar
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)
        header_bar.pack_start(self.back_button)
        self.set_titlebar(header_bar)

        # Create the search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("activate", self.on_search_entry_activate)

        # Create the search bar and connect it to the search entry
        self.search_bar = Gtk.SearchBar()
        self.search_bar.set_child(self.search_entry)
        self.search_bar.connect_entry(self.search_entry)

        # Create a search button
        self.search_button = Gtk.ToggleButton()
        self.search_button.connect('toggled', self.on_search_button_clicked)
        self.search_button.set_icon_name("edit-find-symbolic")
        header_bar.pack_start(self.search_button)

        # Create menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        header_bar.pack_end(menu_button)

        # Create menu model
        menu_model = Gio.Menu()
        menu_model.append("Synchronise", "app.synchronise")
        menu_model.append("Preferences", "app.preferences")
        menu_model.append("About", "app.about")
        menu_model.append("Quit", "app.quit")
        menu_button.set_menu_model(menu_model)

        # Create a scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self.list_box)
        
        # Create a vertical box and pack the search bar and scrolled window into it
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.append(self.search_bar)
        vbox.append(scrolled_window)
        scrolled_window.set_vexpand(True)
        self.set_child(vbox)

        # Initial folder
        self.current_folder = '.'
        self.load_folder(self.current_folder)
        application.create_action('reload', lambda *_: self.load_folder(self.current_folder), ['<primary>r'])

    def on_back_button_clicked(self, _):
        parent_folder = '/'.join(self.current_folder.split('/')[:-1]) if '/' in self.current_folder else '.'
        self.load_folder(parent_folder)

    def on_search_button_clicked(self, button, _ = None):
        # Toggle search mode
        search_mode = not self.search_bar.get_search_mode()
        self.search_bar.set_search_mode(search_mode)

        # If search mode is active, grab focus to the search entry
        if search_mode:
            self.search_entry.grab_focus()
            self.back_button.set_icon_name("go-previous-symbolic")
        else:
            self.search_button.set_icon_name("edit-find-symbolic")

    def on_search_entry_activate(self, entry):
        query = entry.get_text()
        self.current_folder = '.'
        self.search_button.set_icon_name("edit-find-symbolic")
        self.search_button.set_visible(False)
        self.search_button.set_active(False)
        self.search_bar.set_search_mode(False)
        self.back_button.set_visible(True)
        self.set_title('Password Search')

        # Remove all children from the list box
        for row in list(self.list_box):
            self.list_box.remove(row)

        use_folder = self.config_manager.get('Settings', 'use_folder').lower() == 'true'
        if use_folder:
            folder_contents = self.pass_manager.list_files(self.current_folder, query)
        else:
            folder_contents = self.pass_manager.list_passwords(self.current_folder, query)

        for item in folder_contents:
            label = Gtk.Label(label=item)
            self.list_box.append(label)

    def load_folder(self, folder):
        self.current_folder = folder
        self.set_title(folder if folder != '.' else 'Password Store')

        # Hide or show the back button based on whether on root
        is_root = folder == '.'
        self.back_button.set_visible(not is_root)
        self.search_button.set_visible(is_root)

        # Remove all children from the list box
        for row in list(self.list_box):
            self.list_box.remove(row)

        folder_contents = self.pass_manager.list_passwords(folder)
        for item in folder_contents:
            label = Gtk.Label(label=item)
            self.list_box.append(label)

    def on_row_activated(self, list_box, row):
        selected_item = row.get_child().get_text()
        # Check if the selected item is a folder by listing its content
        item_path = self.current_folder + '/' + selected_item if self.current_folder != '.' else selected_item
        sub_items = self.pass_manager.list_passwords(item_path)
        if sub_items:
            # Navigate into the folder
            self.load_folder(item_path)
        else:
            # Display the password content
            password_content = self.pass_manager.show_password(item_path)
            self.show_password_dialog(password_content, item_path)

    def show_password_dialog(self, content, title):
        dialog = Dialog(self, title, content, self.pass_manager)
        dialog.set_visible(True)


class Preferences(Gtk.Dialog):
    def __init__(self, parent, config_manager):
        Gtk.Dialog.__init__(self, title="Preferences", transient_for=parent, modal=True)
        self.config_manager = config_manager

        # Get the content area directly
        box = self.get_child()
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)
        grid.set_margin_start(6)
        grid.set_margin_end(6)
        grid.set_margin_top(6)
        grid.set_margin_bottom(6)

        # Password Store Path
        logo1 = Gtk.Image.new_from_icon_name("folder-symbolic")
        grid.attach(logo1, 0, 0, 1, 1)

        path_label = Gtk.Label(label="Password Store Path:")
        grid.attach(path_label, 1, 0, 1, 1)

        self.path_entry = Gtk.Entry()
        self.path_entry.set_text(self.config_manager.get('Settings', 'password_store_path'))
        self.path_entry.connect("changed", self.save_preferences)
        grid.attach(self.path_entry, 0, 1, 6, 1)

        # Filter Valid Files
        logo2 = Gtk.Image.new_from_icon_name("security-medium-symbolic")
        grid.attach(logo2, 0, 2, 1, 1)

        filter_label = Gtk.Label(label="Hide invalid files:")
        grid.attach(filter_label, 1, 2, 1, 1)

        self.filter_switch = Gtk.Switch()
        self.filter_switch.set_active(self.config_manager.get('Settings', 'filter_valid_files') == 'True')
        self.filter_switch.connect("state-set", self.save_preferences)
        grid.attach(self.filter_switch, 2, 2, 2, 1)

        # auto sync
        logo3 = Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic")
        grid.attach(logo3, 0, 3, 1, 1)

        sync_label = Gtk.Label(label="automatically synchronize:")
        grid.attach(sync_label, 1, 3, 1, 1)

        self.sync_switch = Gtk.Switch()
        self.sync_switch.set_active(self.config_manager.get('Settings', 'auto_sync') == 'True')
        self.sync_switch.connect("state-set", self.save_preferences)
        grid.attach(self.sync_switch, 2, 3, 2, 1)

        # Use filesystem instead of pass
        logo4 = Gtk.Image.new_from_icon_name("edit-find-symbolic")
        grid.attach(logo4, 0, 4, 1, 1)

        folder_label = Gtk.Label(label="Use improved search:")
        grid.attach(folder_label, 1, 4, 1, 1)

        self.folder_switch = Gtk.Switch()
        self.folder_switch.set_active(self.config_manager.get('Settings', 'use_folder') == 'True')
        self.folder_switch.connect("state-set", self.save_preferences)
        grid.attach(self.folder_switch, 2, 4, 2, 1)

        box.append(grid)

    def save_preferences(self, *args):
        self.config_manager.set('Settings', 'password_store_path', self.path_entry.get_text())
        self.config_manager.set('Settings', 'filter_valid_files', str(self.filter_switch.get_active()))
        self.config_manager.set('Settings', 'auto_sync', str(self.sync_switch.get_active()))
        self.config_manager.set('Settings', 'use_folder', str(self.folder_switch.get_active()))
        self.config_manager.save()


class Application(Gtk.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='com.github.noobping.pypass',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.create_action('quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action('about', self.on_about_action, ['<primary>a'])
        self.create_action('preferences', self.on_preferences_action, ['<primary>p'])

        # Initialize PassWrapper
        self.config_manager = ConfigManager()
        self.pass_manager = PassWrapper(self.config_manager)
        self.create_action('synchronise', lambda *_: self.pass_manager.sync(), ['<primary>s'])

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = Window(pass_manager=self.pass_manager, config_manager=self.config_manager, application=self)
        win.present()
        self.pass_manager.sync()

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Gtk.AboutDialog(transient_for=self.props.active_window,
                                modal=True,
                                program_name='Password Store',
                                logo_icon_name='com.github.noobping.pypass',
                                version='0.1.0',
                                license_type=Gtk.License.GPL_3_0,
                                authors=['noobping', 'ChatGPT-4'],
                                copyright='© 2023 noobping')
        about.present()

    def on_preferences_action(self, widget, _):
        dialog = Preferences(self.props.active_window, self.config_manager)
        dialog.set_visible(True)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main():
    app = Application()
    app.run()

if __name__ == "__main__":
    main()
