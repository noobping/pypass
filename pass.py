import subprocess
import re

class PassWrapper:
    def __init__(self):
        pass

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
        paths = []
        current_path = []

        for line in lines:
            indentation = len(re.match(r'^[│\s]*', line).group())
            level = indentation // 4
            name = line.split(' ')[-1].strip()
            if not name:
                continue

            current_path = current_path[:level]
            current_path.append(name)
            path_string = '/'.join(current_path)
            paths.append(path_string)

        return paths

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

# Example usage
pass_manager = PassWrapper()
password_tree = pass_manager.list_passwords('.')  # List all passwords
print(password_tree)
