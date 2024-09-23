import os
def to_models_relative_path(file_path):
    MODELS_FOLDER_NAME = "models"
    index = file_path.rfind(MODELS_FOLDER_NAME)
    if index != -1:
        root = file_path[:index + len(MODELS_FOLDER_NAME)]
    else:
        return None
    return os.path.splitext(os.path.relpath(file_path, root))[0].replace("\\", "/")

def is_float(value):
    if value is None:
        return False
    try:
        float(value)
        return True
    except:
        return False
    
def path_exists(path):
    """Check if a given path exists."""
    return os.path.exists(path)

def validate_studiomdl_path(input_path):
    """Check if studiomdl.exe exists in the provided path."""
    return path_exists(input_path / "studiomdl.exe")

def validate_gameinfo_path(base_path):
    """Check if gameinfo.txt exists in the provided path."""
    return _find_file_in_subdirectories(base_path, "gameinfo.txt")

def _find_file_in_subdirectories(base_path, file_name):
    """Search for a specific file in subdirectories."""
    print(f"Searching for {file_name} in in {base_path}")
    for subdir in base_path.iterdir():
        if subdir.is_dir() and path_exists(subdir / file_name):
            print(f"Found {file_name} in {subdir}")
            return str(subdir)
    return None

def format_game_select_items(games_paths_list):
    """Helper function to format game paths for the dropdown using parent folder and subdirectory."""
    game_select_items_enum = []

    for game_path in games_paths_list:
        # Get the parent folder (e.g., 'Half-Life 2') and the subdirectory (e.g., 'hl2', 'ep2')
        parent_folder = os.path.basename(os.path.dirname(game_path))
        subdirectory = os.path.basename(game_path)

        # Combine parent folder and subdirectory into a title like 'Half-Life 2/hl2'
        game_name = f"{parent_folder}/{subdirectory}"

        # Append game name and path as a tuple for the enum property
        item = (game_path, game_name, "")
        game_select_items_enum.append(item)

    return game_select_items_enum

