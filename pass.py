import re
import subprocess

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class PassWrapper:
    def __init__(self):
        pass

    def list_passwords(self, folder='.'):
        command = ['pass', 'ls', folder]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8') if result.returncode == 0 else None
        if output is None:
            return None

        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)

        lines = output.split('\n')
        children = []
        current_indent = None
        for line in lines[1:]:  # Skip the first line
            stripped_line = line.lstrip()
            indent = len(line) - len(stripped_line)
            if current_indent is None:
                current_indent = indent
            elif indent == current_indent and stripped_line.startswith("├──"):
                item_name = stripped_line.lstrip("├── ").strip('/')
                children.append(item_name)
            elif indent < current_indent:
                break
        return children

    def get_folder_contents(self, folder):
        # List all passwords and folders recursively
        password_tree = self.list_passwords(folder)
        return password_tree

    def show_password(self, path):
        command = ['pass', 'show', path]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8') if result.returncode == 0 else None

    def get_password(self, path):
        command = ['pass', path]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8').strip() if result.returncode == 0 else None

    def insert_password(self, path, password):
        command = ['pass', 'insert', '--multiline', path]
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate(input=password.encode('utf-8'))
        return process.returncode == 0

    def remove_password(self, path):
        command = ['pass', 'rm', path]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0


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
        self.back_button = Gtk.Button(label="Back")
        self.back_button.connect('clicked', self.on_back_button_clicked)

        # Create a header bar
        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_title_buttons(True)
        self.header_bar.pack_start(self.back_button)
        self.set_titlebar(self.header_bar)

        # Create a scrolled window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_child(self.list_box)
        self.set_child(self.scrolled_window)

        # Initial folder
        self.current_folder = '.'
        self.load_folder(self.current_folder)

    def load_folder(self, folder):
        self.current_folder = folder
        self.set_title(folder if folder != '.' else 'Password Manager')

        # Remove all children from the list box
        for row in list(self.list_box):
            self.list_box.remove(row)

        folder_contents = self.pass_manager.get_folder_contents(folder)
        for item in folder_contents:
            label = Gtk.Label(label=item)
            self.list_box.append(label)

    def on_row_activated(self, list_box, row):
        selected_item = row.get_child().get_text()
        new_path = self.current_folder + '/' + selected_item if self.current_folder != '.' else selected_item
        if selected_item.endswith('/'):  # If the item is a folder
            self.load_folder(new_path)
        else:
            # Show the contents of the selected password file
            password_content = self.pass_manager.show_password(new_path)
            self.show_password_dialog(password_content)

    def show_password_dialog(self, content):
        dialog = Gtk.Dialog(transient_for=self, modal=True)
        dialog.set_default_size(300, 200)
        dialog.set_title("Password Content")

        # Create a label to display the content
        label = Gtk.Label(label=content)
        label.set_selectable(True)  # Allow text selection
        label.set_margin_top(10)
        label.set_margin_bottom(10)
        label.set_margin_start(10)
        label.set_margin_end(10)

        # Add the label to the dialog's content
        dialog_box = dialog.get_child()
        dialog_box.append(label)

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
    app = PasswordManagerApplication()
    app.run()

if __name__ == "__main__":
    main()