bl_info = {
    "name": "AutoMDL",
    "author": "NvC_DmN_CH",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > AutoMDL",
    "description": "Compiles models for Source where the blend project file is",
    "warning": "",
    "wiki_url": "",
    "category": "3D View"
}

import bpy
import os
import subprocess
import shutil
from pathlib import Path
import mathutils
import winreg
from bl_ui.generic_ui_list import draw_ui_list
import threading
from io import StringIO
from .qc_writer import QCWriter
from .mesh_exporter import MeshExporter
from .material_manager import MaterialManager

game_select_method_is_dropdown = None
temp_path = bpy.app.tempdir
games_paths_list = []
game_path = None
steam_path = None
studiomdl_path = None
gameManualTextGameinfoPath = None
gameManualTextInputIsInvalid = False
massTextInputIsInvalid = False
visMeshInputIsInvalid = False
phyMeshInputIsInvalid = False

def defineGameSelectDropdown(self, context):
    # game_select
    game_select_items_enum = []
    for i in range(len(games_paths_list)):
        game_name = str(os.path.basename(os.path.dirname(games_paths_list[i])))
        game_path = str(games_paths_list[i])
        item = (game_path, game_name, "")
        game_select_items_enum.append(item)
    
    
    bpy.types.Scene.game_select = bpy.props.EnumProperty(
        name = "Selected Option",
        items = game_select_items_enum,
        update = onGameDropdownChanged
    )

def onGameDropdownChanged(self, context):
    pass

#Unused. Why?
def refreshGameSelectDropdown(self, context):
    del bpy.types.Scene.game_select
    defineGameSelectDropdown(None, context)
    
def onMassTextInputChanged(self, context):
    """
    Validates the user-provided input for the mass text field.
    
    This function sets the `massTextInputIsInvalid` global variable to `True` if the input value is not a valid float, or `False` if the input is a valid float.
    
    Args:
        self (object): The current object instance.
        context (bpy.types.Context): The Blender context object.
    
    Returns:
        None
    """
        
    global massTextInputIsInvalid
    massTextInputIsInvalid = not is_float(context.scene.mass_text_input)

def on_game_manual_text_input_changed(context):
    """
    Validates the user-provided path for the studiomdl.exe file and the containing gameinfo.txt file.
    
    Args:
        self (object): The current object instance.
        context (bpy.types.Context): The Blender context object.
    
    Returns:
        None
    """
    global gameManualTextInputIsInvalid
    gameManualTextInputIsInvalid = False
    
    in_folder = Path(context.scene.studiomdl_manual_input)
    if not validate_studiomdl_path(in_folder):
        gameManualTextInputIsInvalid = True
        print("ERROR: Couldn't find studiomdl.exe in specified folder")
        return

    base_path = in_folder.parent
    gameinfo_path = validate_gameinfo_path(base_path)

    if not gameinfo_path:
        gameManualTextInputIsInvalid = True
        print("ERROR: Couldn't find gameinfo.txt in game")
        return

    global gameManualTextGameinfoPath
    gameManualTextGameinfoPath = gameinfo_path

class AutoMDLOperator(bpy.types.Operator):
    bl_idname = "wm.automdl"
    bl_label = "Update MDL"
    bl_description = "Compile model"

    def execute(self, context):
        if not self.set_game_path(context):
            return {'CANCELLED'}

        blend_path = bpy.data.filepath
        if not self.check_blend_file(blend_path):
            return {'CANCELLED'}

        has_collision, vis_mesh_valid, phy_mesh_valid = self.check_meshes(context)
        if not vis_mesh_valid or (has_collision and not phy_mesh_valid):
            return {'CANCELLED'}

        if not self.validate_meshes(context):
            return {'CANCELLED'}

        qc_modelpath, qc_vismesh, qc_phymesh, qc_path = self.prepare_qc_paths(blend_path)
        if not qc_modelpath:
            self.report({'ERROR'}, "Please save the project inside a models folder")
            return {'CANCELLED'}

        mesh_exporter = initialize_mesh_exporter_from_context(context, bpy.app.tempdir, qc_vismesh, qc_phymesh)
        context_mode_snapshot = switch_to_object_mode()
        mesh_exporter.export_meshes(has_collision)
        restore_mode(context_mode_snapshot)

        qc_cdmaterials_list, has_materials = self.setup_qc_materials(context, qc_modelpath)
        qc_writer = initialize_qc_writer_from_context(context, qc_path, qc_modelpath, qc_vismesh, qc_phymesh, qc_cdmaterials_list, has_collision, has_materials)
        qc_writer.write_qc_file()

        self.compile_qc(qc_path)
        self.move_compiled_files(qc_modelpath, blend_path)
        
        material_manager = MaterialManager(context)
        material_manager.create_material_folders(blend_path, qc_cdmaterials_list, has_materials)

        self.report({'INFO'}, f"If compile was successful, output should be in \"{os.path.dirname(blend_path)}\"")
        return {'FINISHED'}

    def set_game_path(self, context):
        """Set the game path based on user selection."""
        if game_select_method_is_dropdown:
            setGamePath(context.scene.game_select)
        else:
            setGamePath(gameManualTextGameinfoPath)
        return True

    def check_blend_file(self, blend_path):
        """Check if the blend file is saved in the correct location."""
        if not blend_path:
            self.report({'ERROR'}, "Please save the project inside a models folder")
            return False
        return True

    def check_meshes(self, context):
        """Check the validity of the meshes and whether collision meshes are present."""
        has_collision = False
        phy_mesh_obj = context.scene.phy_mesh
        if phy_mesh_obj and phy_mesh_obj.name in bpy.data.objects:
            has_collision = True

        vis_mesh_valid = checkVisMeshHasMesh(context)
        phy_mesh_valid = checkPhyMeshHasMesh(context)

        if not vis_mesh_valid:
            self.report({'ERROR'}, "Please select a mesh for Visual mesh")

        if has_collision and not phy_mesh_valid:
            self.report({'ERROR'}, "Please select a mesh for Collision mesh")

        return has_collision, vis_mesh_valid, phy_mesh_valid

    def validate_meshes(self, context):
        """Ensure that selected meshes are not deleted."""
        if context.scene.vis_mesh and context.scene.vis_mesh.name not in bpy.context.scene.objects:
            self.report({'ERROR'}, "Visual mesh points to a deleted object!")
            return False

        if context.scene.phy_mesh and context.scene.phy_mesh.name not in bpy.context.scene.objects:
            self.report({'ERROR'}, "Collision mesh points to a deleted object!")
            return False

        return True

    def prepare_qc_paths(self, blend_path):
        """Prepare necessary paths for the QC file and model."""
        qc_path = os.path.join(temp_path, "qc.qc")

        qc_modelpath = to_models_relative_path(blend_path)
        if qc_modelpath is None:
            return None, None, None, None

        qc_vismesh = os.path.basename(qc_modelpath) + "_ref"
        qc_phymesh = os.path.basename(qc_modelpath) + "_phy"
        
        return qc_modelpath, qc_vismesh, qc_phymesh, qc_path

    def setup_qc_materials(self, context, qc_modelpath):
        """Set up the list of materials to be used in the QC file."""
        qc_cdmaterials_list = []
        has_materials = context.scene.vis_mesh.material_slots

        if has_materials:
            if context.scene.cdmaterials_type == '1':  # manual
                for material in context.scene.cdmaterials_list:
                    material_path = os.path.join(material.name, '', '').replace("\\", "/")
                    qc_cdmaterials_list.append(material_path)
            else:  # auto
                auto_path = "models/" + os.path.dirname(qc_modelpath)
                qc_cdmaterials_list.append(auto_path)

        return qc_cdmaterials_list, has_materials

    def compile_qc(self, qc_path):
        """Compile the QC file using the external studiomdl tool."""
        studiomdl_args = [studiomdl_path, "-game", game_path, "-nop4", "-quiet", "-nowarnings", "-nox360", qc_path]
        subprocess.run(studiomdl_args)

    def move_compiled_files(self, qc_modelpath, blend_path):
        """Move the compiled files to the appropriate directory."""
        compile_path = os.path.join(game_path, "models", os.path.dirname(qc_modelpath))
        move_path = os.path.dirname(blend_path)
        compiled_model_name = Path(os.path.basename(qc_modelpath)).stem
        compiled_exts = [".dx80.vtx", ".dx90.vtx", ".mdl", ".phy", ".sw.vtx", ".vvd"]

        for ext in compiled_exts:
            src = os.path.join(compile_path, compiled_model_name + ext)
            dest = os.path.join(move_path, compiled_model_name + ext)
            if os.path.isfile(src):
                shutil.move(src, dest)

        if os.path.isdir(compile_path) and not os.listdir(compile_path):
            os.rmdir(compile_path)

class AutoMDLPanel(bpy.types.Panel):
    bl_label = "AutoMDL"
    bl_idname = "VIEW3D_PT_automdl_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AutoMDL'
    
    def draw(self, context):
        layout = self.layout
        
        vis_mesh_valid = checkVisMeshHasMesh(context)
        phy_mesh_valid = checkPhyMeshHasMesh(context)
        
        row = layout.row()
        global steam_path
        if(steam_path is not None):
            row.label(text= "Choose compiler:")
            row = layout.row()
            row.prop(context.scene, "game_select", text="")
        else:
            row.label(text= "Directory containing studiomdl.exe:")
            row = layout.row()
            row.alert = gameManualTextInputIsInvalid
            row.prop(context.scene, "studiomdl_manual_input")
            
        row = layout.row()
        
        row = layout.row()
        row.enabled = vis_mesh_valid
        row.operator("wm.automdl")
        row = layout.row()
        
        row = layout.row()
        row.label(text= "Visual mesh:")
        row.prop_search(context.scene, "vis_mesh", bpy.context.scene, "objects", text="")
        
        row = layout.row()
        row.label(text= "Collision mesh:")
        row.prop_search(context.scene, "phy_mesh", bpy.context.scene, "objects", text="")
        
        row = layout.row()
        
        if vis_mesh_valid:
            if phy_mesh_valid:
                row = layout.row()
                row.enabled = phy_mesh_valid
                row.label(text= "Surface type:")
                row.prop(context.scene, "surfaceprop", text="")
                
                row = layout.row()
                if( not context.scene.staticprop):
                    row.label(text= "Mass:")
                    row.alert = massTextInputIsInvalid
                    row.prop(context.scene, "mass_text_input")
                else:
                    row.label(text= "No mass")
        
                #row = layout.row()
                #row.enabled = phy_mesh_valid
                #row.prop(context.scene, "concave", text="Concave");     
        
        row = layout.row()
        row.label(text= " ")
        row = layout.row()
        

        if vis_mesh_valid:
            if context.scene.vis_mesh.material_slots:
                row.label(text= "Path to VMT files will be:")
                row = layout.row()
                row.prop(context.scene, 'cdmaterials_type', expand=True)
                row = layout.row()
                
                if context.scene.cdmaterials_type == '0':
                    if len(bpy.data.filepath) != 0:
                        modelpath = to_models_relative_path(bpy.data.filepath)
                        if modelpath != None:
                            if vis_mesh_valid:
                                modelpath_dirname = os.path.dirname(modelpath)
                                for slot in context.scene.vis_mesh.material_slots:
                                    row = layout.row()
                                    row.label(text=os.path.join("materials/models/", modelpath_dirname, slot.name).replace("\\", "/") + ".vmt", icon='MATERIAL')
                        else:
                            row.label(text="Blend file is not inside a models folder", icon='ERROR')
                    else:
                        row.label(text="Blend file not saved", icon='ERROR')
                else:
                    draw_ui_list(
                        layout,
                        context,
                        list_path="scene.cdmaterials_list",
                        active_index_path="scene.cdmaterials_list_active_index",
                        unique_id="cdmaterials_list_id",
                    )
            else:
                row.label(text="Visual mesh has no materials", icon='INFO')
                
        row = layout.row()
        row.label(text="")
        row = layout.row()
        row.label(text="General options:")
        row = layout.row()
        row.prop(context.scene, "mostlyopaque", text="Has Transparent Materials")
        
        row = layout.row()
        row.prop(context.scene, "staticprop", text="Static Prop")

# for cdmaterials list
class CdMaterialsPropGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()

class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__
    
    do_make_folders_for_cdmaterials: bpy.props.BoolProperty(
        name="Make Folders",
        description="On compile, make the appropriate folders in the materials folder (make folders for each $cdmaterials)",
        default=True
    )
    
    do_make_vmts: bpy.props.BoolProperty(
        name="Make placeholder VMTs",
        description="On compile, make placeholder VMT files named after the model's materials, placed inside appropriate folder inside the materials folder\nThis won't replace existing VMTs",
        default=True
    )
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, "do_make_folders_for_cdmaterials", text="Automatically make folders for materials locations")
        row = layout.row()
        row.enabled = self.do_make_folders_for_cdmaterials
        row.prop(self, "do_make_vmts", text="Also make placeholder VMTs (Only when compiling with the \"Same as MDL\" option)")

classes = [
    AutoMDLOperator,
    AutoMDLPanel,
    QCWriter,
    MeshExporter,
    MaterialManager,
    CdMaterialsPropGroup,
    AddonPrefs
]

class_register, class_unregister = bpy.utils.register_classes_factory(classes)

def register():
    from bpy.utils import register_class

    # Register classes
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(f"Error registering class {cls.__name__}: {e}")
    
    # Define custom properties for the addon
    register_custom_properties()

    # Initialize Steam path and game paths list
    setup_steam_path()

    # Set default values after a short delay to allow context initialization
    bpy.app.timers.register(set_default_values, first_interval=1)

    print("AutoMDL addon registered successfully")

def unregister():
    from bpy.utils import unregister_class

    # Unregister classes
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering class {cls.__name__}: {e}")

    # Remove custom properties
    unregister_custom_properties()

    print("AutoMDL addon unregistered successfully")

def set_default_values():
    try:
        # Initialize default values for custom properties
        initialize_cdmaterials_list()
        
        if game_select_method_is_dropdown:
            select_default_game_path()
        else:
            on_game_manual_text_input_changed(None, bpy.context)

        print("Default values set successfully")
    except Exception as e:
        print(f"Error setting default values: {e}")

def register_custom_properties():
    bpy.types.Scene.surfaceprop_text_input = bpy.props.StringProperty(name="", default="")
    bpy.types.Scene.mass_text_input = bpy.props.StringProperty(
        name="", default="35",
        description="Mass in kilograms (KG). By default, the Player can +USE pick up 35KG max. The gravgun can pick up 250KG max. The portal gun can pick up 85KG max.",
        update=onMassTextInputChanged
    )
    bpy.types.Scene.vis_mesh = bpy.props.PointerProperty(type=bpy.types.Object, name="Selected Object", description="Select an object from the scene")
    bpy.types.Scene.phy_mesh = bpy.props.PointerProperty(type=bpy.types.Object, name="Selected Object", description="Select an object from the scene")
    bpy.types.Scene.surfaceprop = bpy.props.EnumProperty(
        name="Selected Option",
        items = [
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
    bpy.types.Scene.cdmaterials_type = bpy.props.EnumProperty(items =
        (
            ('0','Same as MDL',''),
            ('1','Other','')
        )
    )
    bpy.types.Scene.cdmaterials_list = bpy.props.CollectionProperty(type=CdMaterialsPropGroup)
    bpy.types.Scene.cdmaterials_list_active_index = bpy.props.IntProperty()

def unregister_custom_properties():
    try:
        del bpy.types.Scene.surfaceprop_text_input
        del bpy.types.Scene.vis_mesh
        del bpy.types.Scene.phy_mesh
        del bpy.types.Scene.surfaceprop
        del bpy.types.Scene.staticprop
        del bpy.types.Scene.mostlyopaque
        del bpy.types.Scene.mass_text_input
        if game_select_method_is_dropdown:
            del bpy.types.Scene.game_select
        else:
            del bpy.types.Scene.studiomdl_manual_input
        del bpy.types.Scene.cdmaterials_type
        del bpy.types.Scene.cdmaterials_list
        del bpy.types.Scene.cdmaterials_list_active_index
    except AttributeError as e:
        print(f"Error removing property: {e}")

def setup_steam_path():
    global steam_path, games_paths_list, game_select_method_is_dropdown
    steam_path = getSteamInstallationPath()
    if steam_path is not None:
        game_select_method_is_dropdown = True
        steam_path = os.path.join(steam_path, "").replace("\\", "/")
        games_paths_list = get_games_list()
        defineGameSelectDropdown(None, bpy.context)
    else:
        game_select_method_is_dropdown = False
        steam_path = None
        bpy.types.Scene.studiomdl_manual_input = bpy.props.StringProperty(
            name="", default="", description="Path to the studiomdl.exe file", update=on_game_manual_text_input_changed
        )

def initialize_cdmaterials_list():
    bpy.context.scene.cdmaterials_list.clear()
    bpy.ops.uilist.entry_add(list_path="scene.cdmaterials_list", active_index_path="scene.cdmaterials_list_active_index")
    bpy.context.scene.cdmaterials_list[0].name = "models/"

def select_default_game_path():
    chosen_game_path = None
    recognized_game_path_gmod = None
    recognized_game_path_hl2 = None
    recognized_game_path_sdk = None
    
    for game_path in games_paths_list:
        game_path_lowercase = str(game_path).lower()
        if "mod" in game_path_lowercase and "s" in game_path_lowercase and "garry" in game_path_lowercase:
            recognized_game_path_gmod = str(game_path)
        if "2" in game_path_lowercase and "half" in game_path_lowercase and "life" in game_path_lowercase:
            recognized_game_path_hl2 = str(game_path)
        if "sdk" in game_path_lowercase and "2013" in game_path_lowercase:
            recognized_game_path_sdk = str(game_path)
    
    # Define preference order for recognized game paths
    if recognized_game_path_sdk is not None:
        chosen_game_path = recognized_game_path_sdk
    elif recognized_game_path_hl2 is not None:
        chosen_game_path = recognized_game_path_hl2
    elif recognized_game_path_gmod is not None:
        chosen_game_path = recognized_game_path_gmod
    
    # Set selected game path
    if chosen_game_path is not None:
        bpy.context.scene.game_select = chosen_game_path
    
    # Trigger update
    onGameDropdownChanged(None, bpy.context)


#-----------------------------------------------
# Context Switching
#-----------------------------------------------
def switch_to_object_mode():
    """Switch to object mode if not already in it and return the previous mode."""
    if bpy.context.mode != 'OBJECT':
        context_mode_snapshot = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        return context_mode_snapshot
    return "null"

def restore_mode(context_mode_snapshot):
    """Restore the mode to the previously saved mode."""
    if context_mode_snapshot != "null":
        bpy.ops.object.mode_set(mode=context_mode_snapshot)
#-----------------------------------------------

def is_float(value):
  if value is None:
      return False
  try:
      float(value)
      return True
  except:
      return False

#-----------------------------------------------
# Mesh Validation
#-----------------------------------------------
# This here is an efficient alogrithm to count the number of loose parts inside a mesh
# i would implement it myself but i haven't done much graph stuff,
# and speed is really needed right now, and first implementation would be slow. 
# lemon's answer in https://blender.stackexchange.com/questions/75332/how-to-find-the-number-of-loose-parts-with-blenders-python-api
def MakeVertPaths( verts, edges ):
    #Initialize the path with all vertices indexes
    result = {v.index: set() for v in verts}
    #Add the possible paths via edges
    for e in edges:
        result[e.vertices[0]].add(e.vertices[1])
        result[e.vertices[1]].add(e.vertices[0])
    return result

def FollowEdges( startingIndex, paths ):
    current = [startingIndex]

    follow = True
    while follow:
        #Get indexes that are still in the paths
        eligible = set( [ind for ind in current if ind in paths] )
        if len( eligible ) == 0:
            follow = False #Stops if no more
        else:
            #Get the corresponding links
            next = [paths[i] for i in eligible]
            #Remove the previous from the paths
            for key in eligible: paths.pop( key )
            #Get the new links as new inputs
            current = set( [ind for sub in next for ind in sub] )

def CountIslands( obj ):
    #Prepare the paths/links from each vertex to others
    paths = MakeVertPaths( obj.data.vertices, obj.data.edges )
    found = True
    n = 0
    while found:
        try:
            #Get one input as long there is one
            startingIndex = next( iter( paths.keys() ) )
            n = n + 1
            #Deplete the paths dictionary following this starting index
            FollowEdges( startingIndex, paths )               
        except:
            found = False
    return n

def CountIslands2(obj):
    mesh = obj.data
    paths={v.index:set() for v in mesh.vertices}
    for e in mesh.edges:
        paths[e.vertices[0]].add(e.vertices[1])
        paths[e.vertices[1]].add(e.vertices[0])
    lparts=[]
    while True:
        try:
            i=next(iter(paths.keys()))
        except StopIteration:
            break
        lpart={i}
        cur={i}
        while True:
            eligible={sc for sc in cur if sc in paths}
            if not eligible:
                break
            cur={ve for sc in eligible for ve in paths[sc]}
            lpart.update(cur)
            for key in eligible: paths.pop(key)
        lparts.append(lpart)
    
    return len(lparts)

def checkVisMeshHasMesh(context):
    vis_mesh_obj = context.scene.vis_mesh
    return (vis_mesh_obj and vis_mesh_obj.type == 'MESH' and vis_mesh_obj.name in bpy.data.objects) == True

def checkPhyMeshHasMesh(context):
    phy_mesh_obj = context.scene.phy_mesh
    return (phy_mesh_obj and phy_mesh_obj.type == 'MESH' and phy_mesh_obj.name in bpy.data.objects) == True
#-----------------------------------------------

def getSteamInstallationPath():
    """
    Get the installation path of the Steam client on the user's system.
    
    This function attempts to retrieve the Steam installation path from the Windows registry. It first checks the 32-bit registry location,
    and if that fails, it checks the 64-bit registry location. If neither attempt is successful, the function returns `None`.
        
    Returns:
        str or None: The Steam installation path if found, otherwise `None`.
    """ 
    # windows specific attempts
    if(os.name == 'nt'):
        # check in registry (x86)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam") as key:
                return winreg.QueryValueEx(key, "SteamPath")[0]
        except Exception as e:
            print(e)
        
        # check in registry (x64)
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                return winreg.QueryValueEx(key, "InstallPath")[0]
        except Exception as e:
            print(e)
    
    # todo: linux specific attempts?
    
    return None

def setGamePath(new_game_path_value):
    """
    Sets the game path and the path to the studiomdl.exe file.
    
    This function updates the global `game_path` and `studiomdl_path` variables with the provided `new_game_path_value`. The `studiomdl_path` is constructed by joining the directory of the `game_path` with the "bin" subdirectory and the "studiomdl.exe" filename.
    
    Args:
        self (object): The current object instance.
        context (bpy.types.Context): The Blender context object.
        new_game_path_value (str): The new game path value to set.
    
    Returns:
        None
    """
    global game_path
    global studiomdl_path
    game_path = new_game_path_value
    studiomdl_path = Path(game_path).parent / "bin" / "studiomdl.exe"

def path_exists(path):
    """Check if the given path exists."""
    return os.path.exists(path)

#-----------------------------------------------
# File validation
#-----------------------------------------------
def find_file_in_subdirectories(base_path, file_name):
    """Find the first subdirectory containing the specified file."""
    for subdir in base_path.iterdir():
        if subdir.is_dir() and path_exists(subdir / file_name):
            return str(subdir)
    return None

def validate_studiomdl_path(input_path):
    """Check if the specified path contains studiomdl.exe."""
    return path_exists(input_path / "studiomdl.exe")

def validate_gameinfo_path(base_path):
    """Check if the base path contains gameinfo.txt in any subdirectory."""
    return find_file_in_subdirectories(base_path, "gameinfo.txt")

def get_games_list():
    """
    Get a list of all Source Engine games installed on the user's system.
    
    This function searches the Steam "common" directory for any subdirectories that contain a "bin" folder with a "studiomdl.exe" file,
    which indicates a Source Engine game is installed. It then iterates through those subdirectories to find the first one that contains a
    "gameinfo.txt" file, which is returned as the game path.
    
    Returns:
        list: A list of file paths to the directories containing Source Engine games.
    """
    global steam_path
    common = Path(steam_path) / "steamapps/common"
    
    subdirectories = [x for x in common.iterdir() if x.is_dir()]
    games_list = []

    for subdir in subdirectories:
        if path_exists(subdir / "bin" / "studiomdl.exe"):
            gameinfo_path = validate_gameinfo_path(subdir)
            if gameinfo_path:
                games_list.append(gameinfo_path)
    
    return games_list

def to_models_relative_path(file_path):
    MODELS_FOLDER_NAME = "models"
    
    # See if we can find a models folder up the chain
    index = file_path.rfind(MODELS_FOLDER_NAME)

    if index != -1:
        root = file_path[:index + len(MODELS_FOLDER_NAME)]
    else:
        return None

    return os.path.splitext(os.path.relpath(file_path, root))[0].replace("\\", "/")
#-----------------------------------------------

#-----------------------------------------------
# Initialization of things.
#-----------------------------------------------
def initialize_qc_writer_from_context(context, qc_path, qc_modelpath, qc_vismesh, qc_phymesh, qc_cdmaterials_list, has_collision, has_materials):
    """
    Initialize a QCWriter instance from the provided Blender context and parameters.
    
    Args:
        context (bpy.types.Context): The Blender context.
        qc_path (str): The path to the QC file.
        qc_modelpath (str): The path to the model file.
        qc_vismesh (str): The path to the visual mesh file.
        qc_phymesh (str): The path to the physical mesh file.
        qc_cdmaterials_list (list): A list of material paths.
        has_collision (bool): Whether the model has collision.
        has_materials (bool): Whether the model has materials.
    
    Returns:
        QCWriter: The initialized QCWriter instance.
    """
    paths = {
        'qc_path': qc_path,
        'qc_modelpath': qc_modelpath,
        'qc_vismesh': qc_vismesh,
        'qc_phymesh': qc_phymesh
    }

    attributes = {
        'qc_mass': context.scene.mass_text_input if not context.scene.staticprop else 1,
        'qc_surfaceprop': context.scene.surfaceprop,
        'qc_cdmaterials_list': qc_cdmaterials_list,
        'qc_maxconvexpieces': CountIslands(context.scene.phy_mesh) if has_collision else 0
    }

    flags = {
        'qc_staticprop': context.scene.staticprop,
        'qc_mostlyopaque': context.scene.mostlyopaque,
        'qc_concave': has_collision and CountIslands(context.scene.phy_mesh) > 1,
        'has_collision': has_collision,
        'has_materials': has_materials
    }

    qc_writer = QCWriter(paths, attributes, flags)
    return qc_writer

def initialize_mesh_exporter_from_context(context, temp_path, qc_vismesh, qc_phymesh):
    """
    Initialize a MeshExporter instance from the provided Blender context and parameters.
    
    Args:
        context (bpy.types.Context): The Blender context.
        temp_path (str): The temporary path for the exported files.
        qc_vismesh (str): The path to the visual mesh file.
        qc_phymesh (str): The path to the physical mesh file.
    
    Returns:
        MeshExporter: The initialized MeshExporter instance.
    """
    paths = {
        'temp_path': temp_path,
        'qc_vismesh': qc_vismesh,
        'qc_phymesh': qc_phymesh
    }

    context_objs = {
        'vis_mesh': context.scene.vis_mesh,
        'phy_mesh': context.scene.phy_mesh
    }

    mesh_exporter = MeshExporter(paths, context_objs)
    return mesh_exporter
#-----------------------------------------------
if __name__ == "__main__":
    register()