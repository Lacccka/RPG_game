import os

EXCLUDED_DIRS = {".vscode", "__pycache__"}


def print_tree(directory, indent=""):
    try:
        items = sorted(os.listdir(directory))
    except PermissionError:
        print(f"{indent}[Permission Denied]")
        return

    for i, name in enumerate(items):
        path = os.path.join(directory, name)
        is_last = i == len(items) - 1
        branch = "└── " if is_last else "├── "

        # Пропустить скрытые файлы и исключённые директории
        if name in EXCLUDED_DIRS or name.startswith("."):
            continue

        print(indent + branch + name)

        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            print_tree(path, indent + extension)


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.abspath(__file__))
    # parent_dir = os.path.dirname(root_dir)
    print(f"Иерархия файлов в: {root_dir}\n")
    print_tree(root_dir)
