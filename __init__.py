bl_info = {
    "name": "AutoMDL",
    "author": "NvC_DmN_CH",
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

config = AutoMDLConfig()

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
    CdMaterialsPropGroup,
    AddonPrefs
]

def register():
    from bpy.utils import register_class, unregister_class

    # Unregister classes if they are already registered
    for cls in classes:
        try:
            unregister_class(cls)
        except:
            pass

    # Register classes
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(f"Error registering class {cls.__name__}: {e}")

    # Register custom properties
    config.register_custom_properties()

    print("AutoMDL addon registered successfully")

def unregister():
    from bpy.utils import unregister_class

    # Unregister classes
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering class {cls.__name__}: {e}")

    # Unregister custom properties
    config.unregister_custom_properties()

    print("AutoMDL addon unregistered successfully")

if __name__ == "__main__":
    register()
