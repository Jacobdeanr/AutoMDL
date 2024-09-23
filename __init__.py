bl_info = {
    "name": "AutoMDL",
    "author": "NvC_DmN_CH, Jacob Robbins",
    "version": (1, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > AutoMDL",
    "description": "Compiles models for Source where the blend project file is",
    "warning": "",
    "wiki_url": "",
    "category": "3D View"
}

import bpy
from .auto_mdl_panel import AutoMDLPanel
from .auto_mdl_config import AutoMDLConfig, CdMaterialsPropGroup
from .auto_mdl_operator import AutoMDLOperator
from .constants import SURFACE_PROP_ITEMS
from .utils import format_game_select_items

# Global config instance
config = AutoMDLConfig()

def update_game_dropdown(self, context):
    """Called when the game dropdown changes."""
    config.ui_interaction_manager.on_game_dropdown_changed(context)

def update_manual_input(self, context):
    """Called when the manual game path input changes."""
    config.ui_interaction_manager.on_game_manual_text_input_changed(context)

def get_game_select_items(self, context):
    """Get the items for the game select dropdown."""
    config = AutoMDLConfig()
    return format_game_select_items(config.game_path_manager.games_paths_list)

class AddonPrefs(bpy.types.AddonPreferences):
    """Addon preferences for AutoMDL settings."""
    
    bl_idname = __package__

    # User preferences
    do_make_folders_for_cdmaterials: bpy.props.BoolProperty(
        name="Make Folders",
        description="Create appropriate folders for each $cdmaterials on compile",
        default=True
    )
    
    do_make_vmts: bpy.props.BoolProperty(
        name="Make placeholder VMTs",
        description="Create placeholder VMT files for the model's materials inside the appropriate material folder. Will not overwrite existing VMTs.",
        default=True
    )
    
    def draw(self, context):
        """Draw UI for addon preferences."""
        layout = self.layout
        layout.prop(self, "do_make_folders_for_cdmaterials", text="Automatically create material folders")
        layout.prop(self, "do_make_vmts", text="Create placeholder VMTs (Only with 'Same as MDL' option)")
        layout.enabled = self.do_make_folders_for_cdmaterials

# Classes to be registered/unregistered
classes = [
    AutoMDLOperator,
    AutoMDLPanel,
    CdMaterialsPropGroup,
    AddonPrefs
]

def register():
    """Register all classes and custom properties for the addon."""
    from bpy.utils import register_class
    

    # Register all classes
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(f"Error registering class {cls.__name__}: {e}")

    # Register custom properties
    register_properties()
    
    
    print("AutoMDL addon registered successfully.")

def unregister():
    """Unregister all classes and custom properties."""
    from bpy.utils import unregister_class

    # Unregister all classes
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering class {cls.__name__}: {e}")

    # Unregister custom properties
    unregister_properties()


    print("AutoMDL addon unregistered successfully.")

def unregister_properties():
    """Unregister custom properties for the addon."""
    del bpy.types.Scene.surfaceprop_text_input
    del bpy.types.Scene.vis_mesh
    del bpy.types.Scene.phy_mesh
    del bpy.types.Scene.surfaceprop
    del bpy.types.Scene.staticprop
    del bpy.types.Scene.mostlyopaque
    del bpy.types.Scene.mass_text_input
    if config.game_path_manager.game_select_method_is_dropdown:
        del bpy.types.Scene.game_select
    else:
        del bpy.types.Scene.studiomdl_manual_input
    del bpy.types.Scene.cdmaterials_type
    del bpy.types.Scene.cdmaterials_list
    del bpy.types.Scene.cdmaterials_list_active_index

def register_properties():
    """Register custom properties for the addon."""
    bpy.types.Scene.surfaceprop_text_input = bpy.props.StringProperty(name="", default="")
    bpy.types.Scene.mass_text_input = bpy.props.StringProperty(
        name="", default="35",
        description="Mass in kilograms (KG). By default, the Player can +USE pick up 35KG max. The gravgun can pick up 250KG max. The portal gun can pick up 85KG max."
    )
    bpy.types.Scene.vis_mesh = bpy.props.PointerProperty(type=bpy.types.Object, name="Selected Object", description="Select an object from the scene")
    bpy.types.Scene.phy_mesh = bpy.props.PointerProperty(type=bpy.types.Object, name="Selected Object", description="Select an object from the scene")
    bpy.types.Scene.surfaceprop = bpy.props.EnumProperty(
        name="Selected Option",
        items=SURFACE_PROP_ITEMS
    )
    bpy.types.Scene.staticprop = bpy.props.BoolProperty(name="Static Prop", description="Enable if used as prop_static\n($staticprop in QC)", default=False)
    bpy.types.Scene.mostlyopaque = bpy.props.BoolProperty(name="Has Transparency", description="Enabling this may fix sorting issues...", default=False)
    bpy.types.Scene.cdmaterials_type = bpy.props.EnumProperty(items=(
        ('0', 'Same as MDL', ''),
        ('1', 'Other', '')
    ))
    bpy.types.Scene.cdmaterials_list = bpy.props.CollectionProperty(type=CdMaterialsPropGroup)
    bpy.types.Scene.cdmaterials_list_active_index = bpy.props.IntProperty()

    if config.game_path_manager.game_select_method_is_dropdown:
        bpy.types.Scene.game_select = bpy.props.EnumProperty(
            name="Select Game",
            items=get_game_select_items,
            update=update_game_dropdown  
        )
    else:
        bpy.types.Scene.studiomdl_manual_input = bpy.props.StringProperty(
            name="",
            default="",
            description="Path to the studiomdl.exe file",
            update=update_manual_input  
        )

if __name__ == "__main__":
    register()
