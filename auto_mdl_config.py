import bpy
import os
import winreg
from pathlib import Path
from .utils import is_float

class CdMaterialsPropGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

def mass_text_input_update(self, context):
    self.mass_text_input_invalid = not is_float(self.mass_text_input)

class AutoMDLConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.game_select_method_is_dropdown = False
        self.temp_path = bpy.app.tempdir
        self.games_paths_list = []
        self.game_path = None
        self.steam_path = None
        self.studiomdl_path = None
        self.gameManualTextGameinfoPath = None

        self.setup_steam_path()
        bpy.app.timers.register(self.set_default_values, first_interval=1)

    def set_default_values(self):
        try:
            self.initialize_cdmaterials_list()
            if self.game_select_method_is_dropdown:
                self.select_default_game_path()
            else:
                self.on_game_manual_text_input_changed(None, bpy.context)
            print("Default values set successfully")
        except Exception as e:
            print(f"Error setting default values: {e}")

    def setup_steam_path(self):
        steam_path = self.get_steam_install_path()
        if steam_path is not None:
            self.game_select_method_is_dropdown = True
            self.steam_path = os.path.join(steam_path, "").replace("\\", "/")
            self.games_paths_list = self.get_games_list()
        else:
            self.game_select_method_is_dropdown = False
            self.steam_path = None
            bpy.types.Scene.studiomdl_manual_input = bpy.props.StringProperty(
                name="", default="", description="Path to the studiomdl.exe file", update=self.on_game_manual_text_input_changed
            )

    def get_steam_install_path(self):
        if os.name == 'nt':
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam") as key:
                    return winreg.QueryValueEx(key, "SteamPath")[0]
            except Exception as e:
                print(e)
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                    return winreg.QueryValueEx(key, "InstallPath")[0]
            except Exception as e:
                print(e)
        return None

    def get_games_list(self):
        common = Path(self.steam_path) / "steamapps/common"
        subdirectories = [x for x in common.iterdir() if x.is_dir()]
        games_list = []
        for subdir in subdirectories:
            if path_exists(subdir / "bin" / "studiomdl.exe"):
                gameinfo_path = validate_gameinfo_path(subdir)
                if gameinfo_path:
                    games_list.append(gameinfo_path)
        return games_list

    def initialize_cdmaterials_list(self):
        bpy.context.scene.cdmaterials_list.clear()
        bpy.ops.uilist.entry_add(list_path="scene.cdmaterials_list", active_index_path="scene.cdmaterials_list_active_index")
        bpy.context.scene.cdmaterials_list[0].name = "models/"

    def select_default_game_path(self):
        chosen_game_path = None
        recognized_game_path_gmod = None
        recognized_game_path_hl2 = None
        recognized_game_path_sdk = None
        
        for game_path in self.games_paths_list:
            game_path_lowercase = str(game_path).lower()
            if "mod" in game_path_lowercase and "s" in game_path_lowercase and "garry" in game_path_lowercase:
                recognized_game_path_gmod = str(game_path)
            if "2" in game_path_lowercase and "half" in game_path_lowercase and "life" in game_path_lowercase:
                recognized_game_path_hl2 = str(game_path)
            if "sdk" in game_path_lowercase and "2013" in game_path_lowercase:
                recognized_game_path_sdk = str(game_path)
        
        if recognized_game_path_sdk is not None:
            chosen_game_path = recognized_game_path_sdk
        
        elif recognized_game_path_hl2 is not None:
            chosen_game_path = recognized_game_path_hl2
        
        elif recognized_game_path_gmod is not None:
            chosen_game_path = recognized_game_path_gmod
        
        if chosen_game_path is not None:
            bpy.context.scene.game_select = chosen_game_path

        self.onGameDropdownChanged(None, bpy.context)
    
    def onGameDropdownChanged(self, context):
        pass

    def on_game_manual_text_input_changed(self, context):
        self.gameManualTextInputIsInvalid = False
        in_folder = Path(context.scene.studiomdl_manual_input)
        if not validate_studiomdl_path(in_folder):
            self.gameManualTextInputIsInvalid = True
            print("ERROR: Couldn't find studiomdl.exe in specified folder")
            return
        
        base_path = in_folder.parent
        gameinfo_path = validate_gameinfo_path(base_path)
        if not gameinfo_path:
            self.gameManualTextInputIsInvalid = True
            print("ERROR: Couldn't find gameinfo.txt in game")
            return
        self.gameManualTextGameinfoPath = gameinfo_path

    def register_custom_properties(self):
        bpy.types.Scene.surfaceprop_text_input = bpy.props.StringProperty(name="", default="")
        bpy.types.Scene.mass_text_input = bpy.props.StringProperty(
            name="", default="35",
            description="Mass in kilograms (KG). By default, the Player can +USE pick up 35KG max. The gravgun can pick up 250KG max. The portal gun can pick up 85KG max.",
            update=mass_text_input_update
        )
        bpy.types.Scene.vis_mesh = bpy.props.PointerProperty(type=bpy.types.Object, name="Selected Object", description="Select an object from the scene")
        bpy.types.Scene.phy_mesh = bpy.props.PointerProperty(type=bpy.types.Object, name="Selected Object", description="Select an object from the scene")
        bpy.types.Scene.surfaceprop = bpy.props.EnumProperty(
            name="Selected Option",
            items=[
                ("Concrete", "Concrete", ""),
                ("Chainlink", "Chainlink", ""),
                ("Canister", "Canister", ""),
                ("Crowbar", "Crowbar", ""),
                ("Metal", "Metal", ""),
                ("Metalvent", "Metalvent", ""),
                ("Popcan", "Popcan", ""),
                ("Wood", "Wood", ""),
                ("Plaster", "Plaster", ""),
                ("Dirt", "Dirt", ""),
                ("Grass", "Grass", ""),
                ("Sand", "Sand", ""),
                ("Snow", "Snow", ""),
                ("Ice", "Ice", ""),
                ("Flesh", "Flesh", ""),
                ("Glass", "Glass", ""),
                ("Tile", "Tile", ""),
                ("Paper", "Paper", ""),
                ("Cardboard", "Cardboard", ""),
                ("Plastic_Box", "Plastic_Box", ""),
                ("Plastic_barrel", "Plastic_barrel", ""),
                ("Plastic", "Plastic", ""),
                ("Rubber", "Rubber", ""),
                ("Clay", "Clay", ""),
                ("Porcelain", "Porcelain", ""),
                ("Computer", "Computer", "")
            ]
        )
        bpy.types.Scene.staticprop = bpy.props.BoolProperty(name="Static Prop", description="Enable if used as prop_static\n($staticprop in QC)", default=False)
        bpy.types.Scene.mostlyopaque = bpy.props.BoolProperty(name="Has Transparency", description="Enabling this may fix sorting issues...", default=False)
        bpy.types.Scene.cdmaterials_type = bpy.props.EnumProperty(items=(
            ('0', 'Same as MDL', ''),
            ('1', 'Other', '')
        ))
        bpy.types.Scene.cdmaterials_list = bpy.props.CollectionProperty(type=CdMaterialsPropGroup)
        bpy.types.Scene.cdmaterials_list_active_index = bpy.props.IntProperty()

    def unregister_custom_properties(self):
        try:
            del bpy.types.Scene.surfaceprop_text_input
            del bpy.types.Scene.vis_mesh
            del bpy.types.Scene.phy_mesh
            del bpy.types.Scene.surfaceprop
            del bpy.types.Scene.staticprop
            del bpy.types.Scene.mostlyopaque
            del bpy.types.Scene.mass_text_input
            if self.game_select_method_is_dropdown:
                del bpy.types.Scene.game_select
            else:
                del bpy.types.Scene.studiomdl_manual_input
            del bpy.types.Scene.cdmaterials_type
            del bpy.types.Scene.cdmaterials_list
            del bpy.types.Scene.cdmaterials_list_active_index
        except AttributeError as e:
            print(f"Error removing property: {e}")

def path_exists(path):
    return os.path.exists(path)

def validate_studiomdl_path(input_path):
    return path_exists(input_path / "studiomdl.exe")

def validate_gameinfo_path(base_path):
    return find_file_in_subdirectories(base_path, "gameinfo.txt")

def find_file_in_subdirectories(base_path, file_name):
    for subdir in base_path.iterdir():
        if subdir.is_dir() and path_exists(subdir / file_name):
            return str(subdir)
    return None
