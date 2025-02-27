from pathlib import Path


def get_project_root():
    """Get the root directory of the project."""
    current_directory = Path.cwd()
    project_root = current_directory
    while project_root.name != "smart-crossover":
        project_root = project_root.parent
        if project_root == project_root.parent:
            raise FileNotFoundError("Project root not found.")
    return project_root


def get_data_dir_path() -> Path:
    """Get the data directory path."""
    return get_project_root() / "data"
