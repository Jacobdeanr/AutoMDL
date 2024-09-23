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