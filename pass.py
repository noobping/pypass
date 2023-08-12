import os
import re
import subprocess

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class PassWrapper:
    def __init__(self):
        pass

    def process_passwords_tree(self, folder='.', query=None, filter_valid_files=False):
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


class PasswordApp(Gtk.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app)
        self.set_default_size(400, 300)

        # Initialize PassWrapper
        self.pass_manager = PassWrapper()

        # Create a ListBox
        self.list_box = Gtk.ListBox()
        self.list_box.connect('row-activated', self.on_row_activated)

        # Create a back button
        self.back_button = Gtk.Button(label="<")
        self.back_button.connect('clicked', self.on_back_button_clicked)

        # Create a header bar
        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_title_buttons(True)
        self.header_bar.pack_start(self.back_button)
        self.set_titlebar(self.header_bar)

        # Create the search entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("activate", self.on_search_entry_activate)

        # Create the search bar and connect it to the search entry
        self.search_bar = Gtk.SearchBar()
        self.search_bar.set_child(self.search_entry)
        self.search_bar.set_show_close_button(True)
        self.search_bar.connect_entry(self.search_entry)

        # Create a search button
        self.search_button = Gtk.Button(label="🔍")
        self.search_button.connect('clicked', self.on_search_button_clicked)
        self.header_bar.pack_start(self.search_button)

        # Create a scrolled window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_child(self.list_box)
        
        # Create a vertical box and pack the search bar and scrolled window into it
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.vbox.append(self.search_bar)
        self.vbox.append(self.scrolled_window)
        self.scrolled_window.set_vexpand(True)
        self.set_child(self.vbox)

        # Initial folder
        self.current_folder = '.'
        self.load_folder(self.current_folder)

    def on_search_button_clicked(self, button):
        # Toggle search mode
        search_mode = not self.search_bar.get_search_mode()
        self.search_bar.set_search_mode(search_mode)

        # If search mode is active, grab focus to the search entry
        if search_mode:
            self.search_entry.grab_focus()

    def on_search_entry_activate(self, entry):
        query = entry.get_text()
        self.current_folder = '.'

        self.set_title('Password Search')
        self.back_button.set_visible(True)
        self.search_button.set_visible(False)

        # Remove all children from the list box
        for row in list(self.list_box):
            self.list_box.remove(row)

        folder_contents = self.pass_manager.process_passwords_tree(self.current_folder, query, True)
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

        folder_contents = self.pass_manager.process_passwords_tree(folder)
        for item in folder_contents:
            label = Gtk.Label(label=item)
            self.list_box.append(label)

    def on_row_activated(self, list_box, row):
        selected_item = row.get_child().get_text()
        # Check if the selected item is a folder by listing its content
        item_path = self.current_folder + '/' + selected_item if self.current_folder != '.' else selected_item
        sub_items = self.pass_manager.process_passwords_tree(item_path)
        if sub_items:
            # Navigate into the folder
            self.load_folder(item_path)
        else:
            # Display the password content
            password_content = self.pass_manager.show_password(item_path)
            self.show_password_dialog(password_content, item_path)

    def show_password_dialog(self, content, title):
        dialog = Gtk.Dialog(transient_for=self, modal=True, title=title)
        dialog.set_default_size(300, 200)

        # Create a label to display the content
        label = Gtk.Label(label=content)
        label.set_selectable(True)  # Allow text selection
        label.set_wrap(True)  # Enable text wrapping
        label.set_margin_top(10)
        label.set_margin_bottom(10)
        label.set_margin_start(10)
        label.set_margin_end(10)

        # Create a scrolled window and set the label as its child
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_child(label)  # Use set_child instead of add

        # Add the scrolled window to the dialog's content
        dialog_box = dialog.get_child()
        dialog_box.append(scrolled_window)

        # Connect the response signal and show the dialog
        dialog.connect("response", lambda dlg, r: dlg.destroy())
        dialog.show()

    def on_back_button_clicked(self, button):
        parent_folder = '/'.join(self.current_folder.split('/')[:-1]) if '/' in self.current_folder else '.'
        self.load_folder(parent_folder)

class PasswordManagerApplication(Gtk.Application):

    def __init__(self):
        super().__init__()

    def do_activate(self):
        win = PasswordApp(self)
        win.present()

def main():
    pass_manager = PassWrapper()
    password_tree = pass_manager.process_passwords_tree('.', 'nick', True)
    print(password_tree)

    app = PasswordManagerApplication()
    app.run()

if __name__ == "__main__":
    main()