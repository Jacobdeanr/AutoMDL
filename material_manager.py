from pathlib import Path
import os

class MaterialManager:
    def __init__(self, context):
        self.context = context
        self.make_folders = context.preferences.addons[__package__].preferences.do_make_folders_for_cdmaterials
        self.make_vmts = context.preferences.addons[__package__].preferences.do_make_vmts

    def create_materials(self, blend_path, qc_cdmaterials_list, has_materials):
        """Handle the creation of material folders and VMT files if necessary."""
        if has_materials and self.make_folders:
            root = self.get_project_root(blend_path)
            for entry in qc_cdmaterials_list:
                self._create_material_folder_and_files(root, entry)

    def _create_material_folder_and_files(self, root, entry):
        """Create material folder and VMT files if necessary."""
        fullpath = Path(os.path.join(root, "materials", entry).replace("\\", "/"))
        print(f"root path = {root}. full path = {fullpath}")
        self._create_folder(fullpath)
        if self._should_create_vmt_files():
            self._create_vmt_files(fullpath, entry)

    def _should_create_vmt_files(self):
        """Check if VMT files should be created based on user preferences."""
        return self.make_vmts and self.context.scene.cdmaterials_type == '0'

    def _create_vmt_files(self, fullpath, entry):
        """Create VMT files in the specified folder if 'Same as MDL' option is selected."""
        for slot in self.context.scene.vis_mesh.material_slots:
            vmt_path = os.path.join(fullpath, slot.name + '.vmt')
            if not os.path.exists(vmt_path):
                self._create_vmt_file(vmt_path, entry)

    def _create_vmt_file(self, vmt_path, entry):
        """Create a single VMT file with the specified path and entry."""
        with open(vmt_path, "w") as file:
            vmt_basetexture = os.path.join(entry, "_PLACEHOLDER_").replace("\\", "/")
            file.write(f"VertexLitGeneric\n{{\n\t$basetexture \"{vmt_basetexture}\"\n}}")

    def _create_folder(self, fullpath):
        """Create a folder if it does not already exist."""
        try:
            os.makedirs(fullpath, exist_ok=True)
        except FileExistsError:
            pass

    def get_project_root(self, blend_path):
        """Get the root directory of the project, two levels up from the models path."""
        models_path = self._get_models_path(blend_path)
        return os.path.dirname(os.path.dirname(models_path))

    def _get_models_path(self, file_path):
        MODELS_FOLDER_NAME = "models"
        index = file_path.rfind(MODELS_FOLDER_NAME)

        if index != -1:
            return file_path[:index + len(MODELS_FOLDER_NAME)]
        return None