#!/bin/python

import configparser
import os
import re
import subprocess

import gi

gi.require_version('Gdk', '4.0')
gi.require_version('GdkWayland', '4.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gdk, GdkWayland, Gtk, Gio


class ConfigManager:
    def __init__(self, file_name='config.ini', app_name='gpass'):
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
            'auto_sync': 'False'
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
        self.password_store_path = config_manager.get('Settings', 'password_store_path')
        self.filter_valid_files = config_manager.get('Settings', 'filter_valid_files').lower() == 'true'
        self.auto_sync = config_manager.get('Settings', 'auto_sync').lower() == 'true'

    def list_passwords(self, folder='.', query=None):
        filter_valid_files = self.filter_valid_files

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
        password_store_path = os.path.expanduser('~/.password-store') # Default password store path
        for line in lines:
            stripped_line = line.lstrip()
            indent = len(line) - len(stripped_line)
            if current_indent is None:
                current_indent = indent
            if indent == current_indent and (stripped_line.startswith("├──") or stripped_line.startswith("└──")):
                item_name = stripped_line.replace("├──", "").replace("└──", "").strip()
                if folder != '.':
                    item_path = os.path.join(password_store_path, folder.lstrip('.'), item_name)
                else:
                    item_path = os.path.join(password_store_path, item_name)
                    
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

    def show_password(self, path):
        command = ['pass', 'show', path]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8') if result.returncode == 0 else None

    def get_otp(self, otp_uri):
        # Run the pass otp command and return the result
        result = subprocess.run(['pass', 'otp', otp_uri], stdout=subprocess.PIPE)
        return result.stdout.decode().strip()

    def sync(self):
        if self.auto_sync:
            subprocess.run(['pass', 'git', 'fetch'])
            subprocess.run(['pass', 'git', 'pull'])
        else:
            print('Automatic syncing is disabled.')


class Dialog(Gtk.Dialog):
    def __init__(self, parent, title, content):    
        Gtk.Dialog.__init__(self, title=title, transient_for=parent, modal=True)
        self.set_default_size(280, 250)

        # Header
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_title_buttons(True)
        self.set_titlebar(header_bar)

        # # Edit or view mode
        # edit_button = Gtk.Button()
        # edit_button.set_icon_name("edit-symbolic")
        # edit_button.connect("clicked", self.on_edit_button_clicked)
        # header_bar.pack_start(edit_button)

        # Create a scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        # Create a grid layout
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        # Split the content by lines
        lines = content.split('\n')

        # Handle the first line as the password
        password_label = Gtk.Label(label=lines[0])
        password_label.set_selectable(True)
        password_label.set_wrap(True)
        password_label.set_visible(False)
        grid.attach(password_label, 0, 0, 2, 1)

        show_password_button = Gtk.Button(label="Show password")
        show_password_button.connect("clicked", self.on_show_button_clicked, password_label)
        grid.attach(show_password_button, 0, 0, 2, 1)

        copy_password_button = Gtk.Button()
        copy_password_button.set_icon_name("edit-copy-symbolic")
        copy_password_button.connect("clicked", self.on_copy_button_clicked, password_label)
        grid.attach(copy_password_button, 2, 0, 1, 1)

        # Check for OTP and display it
        otp_line = next((line for line in lines[1:] if 'otpauth://' in line), None)
        if otp_line:
            otp = parent.app.get_otp(title)
            label_text = Gtk.Label(label="OTP:")
            otp_label = Gtk.Label(label=otp)
            copy_button = Gtk.Button()
            copy_button.set_icon_name("edit-copy-symbolic")
            copy_button.connect("clicked", self.on_copy_button_clicked, otp_label)
            grid.attach(label_text, 0, 1, 1, 1)  # Adjust the row index here
            grid.attach(otp_label, 1, 1, 1, 1)   # Adjust the row index here
            grid.attach(copy_button, 2, 1, 1, 1) # Adjust the row index here

        # Handle the rest of the lines (excluding the OTP line)
        for i, line in enumerate((line for line in lines[1:] if line != otp_line), start=2):
            if ':' in line:
                # Check if the line follows the "label: value" pattern
                label_text, value_text = line.split(':', 1)
                label_widget = Gtk.Label(label=label_text.strip() + ':', halign=Gtk.Align.END)
                value_widget = Gtk.Label(label=value_text.strip())
                value_widget.set_selectable(True)
                value_widget.set_wrap(True)
                value_widget.set_visible(False)

                show_button = Gtk.Button(label=f"Show {label_text.strip()}")
                show_button.connect("clicked", self.on_show_button_clicked, value_widget)
                grid.attach(show_button, 1, i, 1, 1)

                copy_button = Gtk.Button()
                copy_button.set_icon_name("edit-copy-symbolic")
                copy_button.connect("clicked", self.on_copy_button_clicked, value_widget)
                grid.attach(copy_button, 2, i, 1, 1)

                grid.attach(label_widget, 0, i, 1, 1)
                grid.attach(value_widget, 1, i, 1, 1)
            else:
                label_widget = Gtk.Label(label=line)
                label_widget.set_selectable(True)
                label_widget.set_wrap(True)
                grid.attach(label_widget, 0, i, 2, 1)

        scrolled_window.set_child(grid)
        dialog_box = self.get_child()
        dialog_box.append(scrolled_window)

        # Connect the response signal and show the dialog
        self.connect("response", lambda dlg, r: dlg.destroy())

    def on_edit_button_clicked(self, button):
        print("edit mode")

    def on_show_button_clicked(self, button, label):
        value = not label.get_visible()
        label.set_visible(value)
        button.set_visible(not value)

    def on_copy_button_clicked(self, button, label):
        clipboard = Gdk.Display.get_default().get_clipboard()
        text = label.get_label()
        clipboard.set(text)


class Window(Gtk.ApplicationWindow):

    def __init__(self, application, **kwargs):
        super().__init__(application=application, **kwargs)
        self.app = application.pass_manager

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

    def on_back_button_clicked(self, button):
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

        folder_contents = self.app.list_passwords(self.current_folder, query)
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

        folder_contents = self.app.list_passwords(folder)
        for item in folder_contents:
            label = Gtk.Label(label=item)
            self.list_box.append(label)

    def on_row_activated(self, list_box, row):
        selected_item = row.get_child().get_text()
        # Check if the selected item is a folder by listing its content
        item_path = self.current_folder + '/' + selected_item if self.current_folder != '.' else selected_item
        sub_items = self.app.list_passwords(item_path)
        if sub_items:
            # Navigate into the folder
            self.load_folder(item_path)
        else:
            # Display the password content
            password_content = self.app.show_password(item_path)
            self.show_password_dialog(password_content, item_path)

    def show_password_dialog(self, content, title):
        dialog = Dialog(self, title, content)
        dialog.set_visible(True)


class Preferences(Gtk.Dialog):
    def __init__(self, parent, config_manager):
        Gtk.Dialog.__init__(self, title="Preferences", transient_for=parent, modal=True)
        self.config_manager = config_manager

        # Get the content area directly
        box = self.get_child()
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        # Password Store Path
        path_row = Gtk.ListBoxRow()
        path_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        path_label = Gtk.Label(label="Password Store Path:")
        self.path_entry = Gtk.Entry()
        self.path_entry.set_text(self.config_manager.get('Settings', 'password_store_path'))
        self.path_entry.connect("changed", self.save_preferences)

        path_box.append(path_label)
        path_box.append(self.path_entry)
        path_row.set_child(path_box)
        list_box.append(path_row)

        # Filter Valid Files
        filter_row = Gtk.ListBoxRow()
        filter_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        filter_label = Gtk.Label(label="Filter Valid Files:")

        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.filter_switch = Gtk.Switch()
        self.filter_switch.set_active(self.config_manager.get('Settings', 'filter_valid_files') == 'True')
        self.filter_switch.connect("state-set", self.save_preferences)
        switch_box.prepend(self.filter_switch)

        filter_box.append(filter_label)
        filter_box.append(switch_box)
        filter_row.set_child(filter_box)

        list_box.append(filter_row)
        box.append(list_box)

    def save_preferences(self, *args):
        self.config_manager.set('Settings', 'password_store_path', self.path_entry.get_text())
        self.config_manager.set('Settings', 'filter_valid_files', str(self.filter_switch.get_active()))
        self.config_manager.save()


class Application(Gtk.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='com.github.noobping.gpass',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.create_action('quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action('about', self.on_about_action, ['<primary>a'])
        self.create_action('preferences', self.on_preferences_action, ['<primary>p'])

        # Initialize PassWrapper
        self.config_manager = ConfigManager()
        self.pass_manager = PassWrapper(self.config_manager)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = Window(application=self)
        win.present()
        self.pass_manager.sync()

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Gtk.AboutDialog(transient_for=self.props.active_window,
                                modal=True,
                                program_name='Password Store',
                                logo_icon_name='com.github.noobping.gpass',
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