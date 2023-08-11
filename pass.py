import re
import subprocess

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class PassWrapper:
    def __init__(self):
        pass

    import re

class PassWrapper:
    # ... other methods ...

    import re

class PassWrapper:
    # ... other methods ...

    def list_passwords(self, folder=''):
        command = ['pass', 'ls', folder]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode('utf-8') if result.returncode == 0 else None
        if output is None:
            return None

        # Remove ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)

        lines = output.split('\n')[1:]  # Skip the first line that shows the folder name
        tree = []
        stack = [tree]

        for line in lines:
            indentation = len(re.match(r'^[│\s]*', line).group())
            level = indentation // 4
            name = line.strip().split(' ')[-1]
            if not name:
                continue

            while len(stack) - 1 > level:
                stack.pop()

            node = stack[-1]
            if '/' in name:  # Indicates a folder
                folder_name = name[:-1]
                new_node = []
                node.append({folder_name: new_node})
                stack.append(new_node)
            else:
                node.append(name)

        return tree

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


class PasswordApp(Gtk.Window):

    def __init__(self):
        super(PasswordApp, self).__init__(title="Password Manager")
        self.set_border_width(10)

        # Initialize PassWrapper
        self.pass_manager = PassWrapper()

        # Create a TreeView
        self.treeview = Gtk.TreeView()
        self.store = Gtk.TreeStore(str)
        self.treeview.set_model(self.store)
        self.renderer = Gtk.CellRendererText()
        self.column = Gtk.TreeViewColumn("Passwords", self.renderer, text=0)
        self.treeview.append_column(self.column)
        
        # Create a scrolled window
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.add(self.treeview)
        self.add(self.scrolled_window)

        # Get passwords and populate the tree
        self.password_tree = self.pass_manager.list_passwords('.')
        self.populate_tree(self.password_tree, None)

    def populate_tree(self, tree, parent_iter):
        for item in tree:
            if isinstance(item, dict):
                for folder_name, folder_contents in item.items():
                    folder_iter = self.store.append(parent_iter, [folder_name])
                    self.populate_tree(folder_contents, folder_iter)
            else:
                self.store.append(parent_iter, [item])

def main():
    app = PasswordApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()