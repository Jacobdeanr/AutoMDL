import bpy
import os
import winreg
from pathlib import Path
from .utils import is_float, validate_studiomdl_path, validate_gameinfo_path, path_exists

class CdMaterialsPropGroup(bpy.types.PropertyGroup):
    """Property group to store $cdmaterials paths."""
    name: bpy.props.StringProperty()

def mass_text_input_update(self, context):
    """Update function for mass input validation."""
    self.mass_text_input_invalid = not is_float(self.mass_text_input)

class GamePathManager:
    def __init__(self):
        self.steam_path = None
        self.games_paths_list = []
        self.game_select_method_is_dropdown = False

    def setup_steam_path(self):
        """Setup the Steam path by querying the system's registry on Windows and reading all Steam library paths."""
        print("Setting up Steam path...")
        steam_path = self.get_steam_install_path()
        
        if steam_path:
            self.game_select_method_is_dropdown = True
            self.steam_path = os.path.join(steam_path, "").replace("\\", "/").lower()  # Normalize the case

            library_paths = [self.steam_path]

            # Retrieve additional library paths from Steam's libraryfolders.vdf file
            additional_library_paths = self.get_additional_steam_library_paths()
            if additional_library_paths:
                library_paths.extend(additional_library_paths)

            # Remove duplicates by normalizing and converting to lowercase
            library_paths = list(set([Path(p).resolve().as_posix().lower() for p in library_paths]))
            
            # Search for games across all Steam library paths
            self.games_paths_list = self.get_games_list(library_paths)
        else:
            self.game_select_method_is_dropdown = False
            self.steam_path = None
        
        print(f'Steam path: {self.steam_path}\nGames paths: {self.games_paths_list}')

    def get_additional_steam_library_paths(self):
        """Retrieve additional Steam library paths from libraryfolders.vdf."""
        library_paths = []
        try:
            library_vdf_path = os.path.join(self.steam_path, "steamapps", "libraryfolders.vdf")
            print(f'Reading library paths from: {library_vdf_path}')
            if os.path.exists(library_vdf_path):
                with open(library_vdf_path, 'r') as file:
                    for line in file:
                        if 'path' in line:
                            # Extract the path from the VDF file (assumes a format like "path" "D:\\SteamLibrary")
                            path = line.split('"')[3]
                            full_library_path = path.replace("\\", "/").lower()

                            # Check if the 'steamapps' directory exists for this library path
                            steamapps_path = Path(full_library_path) / "steamapps"
                            if steamapps_path.exists():
                                print(f'Found library path: {full_library_path}')
                                library_paths.append(full_library_path)
                            else:
                                print(f"Steamapps directory does not exist at: {steamapps_path}")
        except Exception as e:
            print(f"Failed to retrieve additional library paths: {e}")
        
        return library_paths
    
    def get_games_list(self, library_paths):
        """Get a list of Source games installed across all Steam library paths."""
        games_list = []
        
        for library_path in library_paths:
            common_path = Path(library_path).resolve() / "steamapps/common"

            # Check if 'steamapps/common' exists before proceeding
            if not common_path.exists():
                print(f"Directory does not exist: {common_path}")
                continue

            subdirectories = [x for x in common_path.iterdir() if x.is_dir()]
            
            for subdir in subdirectories:
                if path_exists(subdir / "bin" / "studiomdl.exe"):
                    gameinfo_paths = self._find_all_gameinfo_paths(subdir)
                    games_list.extend([Path(p).resolve().as_posix().lower() for p in gameinfo_paths])
        
        # Remove duplicates in the games list
        games_list = list(set(games_list))
        
        return games_list
    
    def _find_all_gameinfo_paths(self, base_path):
        """Recursively find all gameinfo.txt files in subdirectories."""
        gameinfo_paths = []
        for subdir in base_path.iterdir():
            if subdir.is_dir():
                if path_exists(subdir / "gameinfo.txt"):
                    gameinfo_paths.append(str(subdir))  # Add the path containing gameinfo.txt
                gameinfo_paths.extend(self._find_all_gameinfo_paths(subdir))
        return gameinfo_paths
    
    def get_steam_install_path(self):
        """Retrieve the Steam installation path from Windows registry."""
        if os.name == 'nt':
            reg_paths = [
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")
            ]
            for root, subkey, value in reg_paths:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        return winreg.QueryValueEx(key, value)[0]
                except Exception as e:
                    print(f"Failed to get Steam path from {subkey}: {e}")
        return None

class CDMaterialsManager:
    def initialize_cdmaterials_list(self):
        """Initialize the cdmaterials list with a default entry."""
        bpy.context.scene.cdmaterials_list.clear()
        bpy.ops.uilist.entry_add(
            list_path="scene.cdmaterials_list",
            active_index_path="scene.cdmaterials_list_active_index"
        )
        bpy.context.scene.cdmaterials_list[0].name = "models/"

class UIInteractionManager:
    def __init__(self):
        """Initialize the manager with necessary attributes."""
        self.game_manual_text_input_is_invalid = False
        self.game_manual_text_gameinfo_path = None

    def on_game_dropdown_changed(self, context):
        """Handle game dropdown change."""
        pass
    
    def on_game_manual_text_input_changed(self, context):
        """Handle changes to the manual game path input."""
        self.game_manual_text_input_is_invalid = False
        in_folder = Path(context.scene.studiomdl_manual_input)
        if not validate_studiomdl_path(in_folder):
            self.game_manual_text_input_is_invalid = True
            print("ERROR: Couldn't find studiomdl.exe in the specified folder")
        else:
            base_path = in_folder.parent
            gameinfo_path = validate_gameinfo_path(base_path)
            if not gameinfo_path:
                self.game_manual_text_input_is_invalid = True
                print("ERROR: Couldn't find gameinfo.txt")
            else:
                self.game_manual_text_gameinfo_path = gameinfo_path

class AutoMDLConfig:
    """Singleton configuration class for AutoMDL."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """Initialize default settings and paths."""
        self.temp_path = bpy.app.tempdir
        self.game_path = None
        self.studiomdl_path = None
        self.game_manual_text_gameinfo_path = None

        # Initialize managers
        self.game_path_manager = GamePathManager()
        self.cdmaterials_manager = CDMaterialsManager()
        self.ui_interaction_manager = UIInteractionManager()

        # Set up Steam path and register timers
        self.game_path_manager.setup_steam_path()
        bpy.app.timers.register(self.set_default_values, first_interval=1)

    def set_default_values(self):
        """Set default values for game paths and cdmaterials."""
        try:
            self.cdmaterials_manager.initialize_cdmaterials_list()
            if self.game_path_manager.game_select_method_is_dropdown:
                self.select_default_game_path()
            else:
                self.ui_interaction_manager.on_game_manual_text_input_changed(None, bpy.context)
            print("Default values set successfully")
        except Exception as e:
            print(f"Error setting default values: {e}")

    def select_default_game_path(self):
        """Automatically select a default game path based on installed games."""
        chosen_game_path = None

        # Iterate through all game paths and prioritize based on certain conditions
        for game_path in self.game_path_manager.games_paths_list:
            game_path_str = str(game_path).lower()

            # Prioritize Garry's Mod first
            if "garrysmod" in game_path_str:
                chosen_game_path = game_path
                break  

            elif "half-life 2" in game_path_str:
                chosen_game_path = game_path

            elif "sdk" in game_path_str and "2013" in game_path_str:
                if not chosen_game_path:
                    chosen_game_path = game_path

        # Fallback: If no specific priority game was found, just pick the first game in the list
        if not chosen_game_path and self.game_path_manager.games_paths_list:
            chosen_game_path = self.game_path_manager.games_paths_list[0]

        # Set the selected game in the scene's dropdown
        if chosen_game_path:
            bpy.context.scene.game_select = chosen_game_path

        # Manually call the update on the game dropdown
        self.ui_interaction_manager.on_game_dropdown_changed(bpy.context)
