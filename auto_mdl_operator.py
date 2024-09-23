import bpy
import os
import shutil
import subprocess
from pathlib import Path
from .material_manager import MaterialManager
from .qc_writer import QCWriter
from .mesh_exporter import MeshExporter
from .auto_mdl_config import AutoMDLConfig

def check_visible_mesh_has_mesh(context):
    vis_mesh_obj = context.scene.vis_mesh
    return (vis_mesh_obj and vis_mesh_obj.type == 'MESH' and vis_mesh_obj.name in context.scene.objects) == True

def check_physics_mesh_has_mesh(context):
    phy_mesh_obj = context.scene.phy_mesh
    return (phy_mesh_obj and phy_mesh_obj.type == 'MESH' and phy_mesh_obj.name in context.scene.objects) == True

class AutoMDLOperator(bpy.types.Operator):
    bl_idname = "wm.automdl"
    bl_label = "Update MDL"
    bl_description = "Compile model"

    def execute(self, context):
        config = AutoMDLConfig()

        vis_mesh_valid = check_visible_mesh_has_mesh(context)
        phy_mesh_valid = check_physics_mesh_has_mesh(context)
        
        if not vis_mesh_valid:
            self.report({'ERROR'}, "Visual mesh is not valid")
            return {'CANCELLED'}
        
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

        mesh_exporter = self.initialize_mesh_exporter_from_context(context, config.temp_path, qc_vismesh, qc_phymesh)
        context_mode_snapshot = self.switch_to_object_mode()
        mesh_exporter.export_meshes(has_collision)
        self.restore_mode(context_mode_snapshot)

        qc_cdmaterials_list, has_materials = self.setup_qc_materials(context, qc_modelpath)
        qc_writer = self.initialize_qc_writer_from_context(context, qc_path, qc_modelpath, qc_vismesh, qc_phymesh, qc_cdmaterials_list, has_collision, has_materials)
        qc_writer.write_qc_file()

        self.compile_qc(qc_path)
        self.copy_compiled_files(qc_modelpath, blend_path)
        
        material_manager = MaterialManager(context)
        material_manager.create_materials(qc_cdmaterials_list, has_materials)

        compile_path = os.path.join(config.game_path, "models", os.path.dirname(qc_modelpath))
        self.report({'INFO'}, f"If compile was successful, output should be in \"{compile_path}\"")
        return {'FINISHED'}

    def set_game_path(self, context):
        config = AutoMDLConfig()
        if config.game_path_manager.game_select_method_is_dropdown:
            game_path = context.scene.game_select
        else:
            game_path = config.gameManualTextGameinfoPath
        config.game_path = game_path
        config.studiomdl_path = Path(game_path).parent / "bin" / "studiomdl.exe"
        return True

    def check_blend_file(self, blend_path):
        if not blend_path:
            self.report({'ERROR'}, "Please save the project inside a models folder")
            return False
        return True

    def check_meshes(self, context):
        has_collision = False
        phy_mesh_obj = context.scene.phy_mesh
        if phy_mesh_obj and phy_mesh_obj.name in context.scene.objects:
            has_collision = True

        vis_mesh_valid = check_visible_mesh_has_mesh(context)
        phy_mesh_valid = check_physics_mesh_has_mesh(context)

        if not vis_mesh_valid:
            self.report({'ERROR'}, "Please select a mesh for Visual mesh")

        if has_collision and not phy_mesh_valid:
            self.report({'ERROR'}, "Please select a mesh for Collision mesh")

        return has_collision, vis_mesh_valid, phy_mesh_valid

    def validate_meshes(self, context):
        if context.scene.vis_mesh and context.scene.vis_mesh.name not in context.scene.objects:
            self.report({'ERROR'}, "Visual mesh points to a deleted object!")
            return False

        if context.scene.phy_mesh and context.scene.phy_mesh.name not in context.scene.objects:
            self.report({'ERROR'}, "Collision mesh points to a deleted object!")
            return False

        return True

    def prepare_qc_paths(self, blend_path):
        config = AutoMDLConfig()
        qc_path = os.path.join(config.temp_path, "qc.qc")

        qc_modelpath = self.to_models_relative_path(blend_path)
        if qc_modelpath is None:
            return None, None, None, None

        qc_vismesh = os.path.basename(qc_modelpath) + "_ref"
        qc_phymesh = os.path.basename(qc_modelpath) + "_phy"
        
        return qc_modelpath, qc_vismesh, qc_phymesh, qc_path

    def setup_qc_materials(self, context, qc_modelpath):
        qc_cdmaterials_list = []
        has_materials = context.scene.vis_mesh.material_slots

        if has_materials:
            if context.scene.cdmaterials_type == '1':
                for material in context.scene.cdmaterials_list:
                    material_path = os.path.join(material.name, '', '').replace("\\", "/")
                    qc_cdmaterials_list.append(material_path)
            else:
                auto_path = "models/" + os.path.dirname(qc_modelpath)
                qc_cdmaterials_list.append(auto_path)

        return qc_cdmaterials_list, has_materials

    def compile_qc(self, qc_path):
        config = AutoMDLConfig()
        studiomdl_args = [config.studiomdl_path, "-game", config.game_path, "-nop4", "-quiet", "-nowarnings", "-nox360", qc_path]
        subprocess.run(studiomdl_args)

    def copy_compiled_files(self, qc_modelpath, blend_path):
        config = AutoMDLConfig()
        compile_path = os.path.join(config.game_path, "models", os.path.dirname(qc_modelpath))
        move_path = os.path.dirname(blend_path)
        compiled_model_name = Path(os.path.basename(qc_modelpath)).stem
        compiled_exts = [".dx80.vtx", ".dx90.vtx", ".mdl", ".phy", ".sw.vtx", ".vvd"]

        for ext in compiled_exts:
            src = os.path.join(compile_path, compiled_model_name + ext)
            dest = os.path.join(move_path, compiled_model_name + ext)
            print(f"Copying {src} to {dest}")
            if os.path.isfile(src):
                try:
                    shutil.copy(src, dest)
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to move {src} to {dest}: {e}")
                    return {'CANCELLED'}

        if os.path.isdir(compile_path) and not os.listdir(compile_path):
            os.rmdir(compile_path)

    def initialize_qc_writer_from_context(self, context, qc_path, qc_modelpath, qc_vismesh, qc_phymesh, qc_cdmaterials_list, has_collision, has_materials):
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
            'qc_maxconvexpieces': self.count_islands(context.scene.phy_mesh) if has_collision else 0
        }

        flags = {
            'qc_staticprop': context.scene.staticprop,
            'qc_mostlyopaque': context.scene.mostlyopaque,
            'qc_concave': has_collision and self.count_islands(context.scene.phy_mesh) > 1,
            'has_collision': has_collision,
            'has_materials': has_materials
        }

        return QCWriter(paths, attributes, flags)

    def initialize_mesh_exporter_from_context(self, context, temp_path, qc_vismesh, qc_phymesh):
        paths = {
            'temp_path': temp_path,
            'qc_vismesh': qc_vismesh,
            'qc_phymesh': qc_phymesh
        }

        context_objs = {
            'vis_mesh': context.scene.vis_mesh,
            'phy_mesh': context.scene.phy_mesh
        }

        return MeshExporter(paths, context_objs)

    def switch_to_object_mode(self):
        if bpy.context.mode != 'OBJECT':
            context_mode_snapshot = bpy.context.active_object.mode
            bpy.ops.object.mode_set(mode='OBJECT')
            return context_mode_snapshot
        return "null"

    def restore_mode(self, context_mode_snapshot):
        if context_mode_snapshot != "null":
            bpy.ops.object.mode_set(mode=context_mode_snapshot)
    
    def to_models_relative_path(self, file_path):
        MODELS_FOLDER_NAME = "models"
        
        index = file_path.rfind(MODELS_FOLDER_NAME)
        if index != -1:
            root = file_path[:index + len(MODELS_FOLDER_NAME)]
        else:
            return None

        return os.path.splitext(os.path.relpath(file_path, root))[0].replace("\\", "/")

    def count_islands( self, obj ):
        #Prepare the paths/links from each vertex to others
        paths = self.make_vertex_paths( obj.data.vertices, obj.data.edges )
        found = True
        n = 0
        while found:
            try:
                #Get one input as long there is one
                startingIndex = next( iter( paths.keys() ) )
                n = n + 1
                #Deplete the paths dictionary following this starting index
                self.follow_edges( startingIndex, paths )               
            except:
                found = False
        return n
    
    def make_vertex_paths( self, verts, edges ):
        #Initialize the path with all vertices indexes
        result = {v.index: set() for v in verts}
        #Add the possible paths via edges
        for e in edges:
            result[e.vertices[0]].add(e.vertices[1])
            result[e.vertices[1]].add(e.vertices[0])
        return result
    
    def follow_edges( self, startingIndex, paths ):
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
