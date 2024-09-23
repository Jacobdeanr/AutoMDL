import bpy
import os
from .auto_mdl_config import AutoMDLConfig
from .utils import to_models_relative_path, is_float


class AutoMDLPanel(bpy.types.Panel):
    """Creates a panel in the 3D view's sidebar for the AutoMDL add-on."""
    
    bl_label = "AutoMDL"
    bl_idname = "VIEW3D_PT_automdl_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AutoMDL'

    def draw(self, context):
        """Draws the panel layout."""
        layout = self.layout
        
        self.draw_compiler_options(layout, context)
        self.draw_operator_button(layout)
        self.draw_mesh_selection(layout, context)
        self.draw_surface_and_mass_options(layout, context)
        self.draw_vmt_paths(layout, context)
        self.draw_general_options(layout, context)

    def draw_compiler_options(self, layout, context):
        """Draws the compiler selection options."""
        print("I'm trying to draw the compiler options")
        config = AutoMDLConfig()
        row = layout.row()
        if config.steam_path is not None:
            row.label(text="Choose compiler:")
            row = layout.row()
            self.define_game_select_dropdown(context)
            row.prop(context.scene, "game_select", text="")
        else:
            row.label(text="Directory containing studiomdl.exe:")
            row = layout.row()
            row.alert = config.gameManualTextInputIsInvalid
            row.prop(context.scene, "studiomdl_manual_input")

    def define_game_select_dropdown(self, context):
        """Defines the game select dropdown property in the Blender UI."""
        config = AutoMDLConfig()
        game_select_items_enum = []
        for game_path in config.games_paths_list:
            game_name = str(os.path.basename(os.path.dirname(game_path)))
            item = (game_path, game_name, "")
            game_select_items_enum.append(item)

        bpy.types.Scene.game_select = bpy.props.EnumProperty(
            name="Selected Option",
            items=game_select_items_enum,
            update=onGameDropdownChanged
        )

    def draw_operator_button(self, layout):
        """Draws the button to execute the main operation."""
        row = layout.row()
        row.operator("wm.automdl")

    def draw_mesh_selection(self, layout, context):
        """Draws the UI elements for selecting visual and collision meshes."""
        layout.row().label(text="Visual mesh:")
        layout.row().prop_search(context.scene, "vis_mesh", context.scene, "objects", text="")

        layout.row().label(text="Collision mesh:")
        layout.row().prop_search(context.scene, "phy_mesh", context.scene, "objects", text="")

    def draw_surface_and_mass_options(self, layout, context):
        """Draws the surface type and mass options."""
        layout.row().label(text="Surface type:")
        layout.row().prop(context.scene, "surfaceprop", text="")

        row = layout.row()
        if not context.scene.staticprop:
            row.label(text="Mass:")
            row.alert = self.is_mass_text_input_invalid(context)
            row.prop(context.scene, "mass_text_input")
        else:
            row.label(text="No mass")

    def draw_vmt_paths(self, layout, context):
        """Draws the VMT path options."""
        if context.scene.vis_mesh and context.scene.vis_mesh.material_slots:
            layout.row().label(text="Path to VMT files will be:")
            layout.row().prop(context.scene, 'cdmaterials_type', expand=True)

            if context.scene.cdmaterials_type == '0':
                self.draw_auto_vmt_paths(layout, context)
            else:
                draw_ui_list(layout, context, 'cdmaterials_list', 'cdmaterials_active_index', 'cdmaterials_list_unique_id')
        else:
            layout.row().label(text="Visual mesh has no materials", icon='INFO')
    
    def draw_ui_list(layout, context, list_path, active_index_path, unique_id):
        layout.template_list(
            "UI_UL_list", unique_id,
            getattr(context, list_path.rsplit('.', 1)[0]),
            list_path.rsplit('.', 1)[1],
            getattr(context, active_index_path.rsplit('.', 1)[0]),
            active_index_path.rsplit('.', 1)[1]
        )

    def draw_auto_vmt_paths(self, layout, context):
        """Draws the automatically generated VMT paths."""
        if len(bpy.data.filepath) != 0:
            modelpath = to_models_relative_path(bpy.data.filepath)
            if modelpath is not None:
                modelpath_dirname = os.path.dirname(modelpath)
                for slot in context.scene.vis_mesh.material_slots:
                    layout.row().label(text=os.path.join("materials/models/", modelpath_dirname, slot.name).replace("\\", "/") + ".vmt", icon='MATERIAL')
            else:
                layout.row().label(text="Blend file is not inside a models folder", icon='ERROR')
        else:
            layout.row().label(text="Blend file not saved", icon='ERROR')

    def draw_general_options(self, layout, context):
        """Draws general options for the model compilation process."""
        layout.row().label(text="General options:")
        layout.row().prop(context.scene, "mostlyopaque", text="Has Transparent Materials")
        layout.row().prop(context.scene, "staticprop", text="Static Prop")

    def is_mass_text_input_invalid(self, context):
        return not is_float(context.scene.mass_text_input)

def onGameDropdownChanged(context):
    print("onGameDropdownCahnged")