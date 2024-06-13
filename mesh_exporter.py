import bpy
import os
from io import StringIO

class MeshExporter:
    def __init__(self, paths, context_objs):
        self.paths = paths
        self.context_objs = context_objs

    def export_meshes(self, has_collision):
        """Export the visual and collision meshes to SMD format."""
        self._export_object_to_smd(self.context_objs['vis_mesh'], os.path.join(self.paths['temp_path'], self.paths['qc_vismesh']), False)
        if has_collision:
            self._export_object_to_smd(self.context_objs['phy_mesh'], os.path.join(self.paths['temp_path'], self.paths['qc_phymesh']), True)

    def _export_object_to_smd(self, obj, path, is_collision_smd):
        """Export the object to SMD format."""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh = object_eval.to_mesh()
        mesh.calc_loop_triangles()
        mesh.transform(obj.matrix_world)

        with open(path + ".smd", "w") as file:
            self._write_smd_header(file)
            sb = StringIO()
            has_materials = len(obj.material_slots) > 0

            if is_collision_smd:
                self._export_collision_mesh_to_smd(sb, mesh)
            else:
                self._export_mesh_to_smd(sb, obj, mesh, has_materials)
            
            file.write(sb.getvalue())
            file.write("end\n")

    def _write_smd_header(self, file):
        """Write the header for the SMD file."""
        file.write("version 1\nnodes\n0 \"root\" -1\nend\nskeleton\ntime 0\n0 0 0 0 0 0 0\nend\ntriangles\n")

    def _export_mesh_to_smd(self, sb, obj, mesh, has_materials):
        """Export the mesh to SMD format, with or without materials."""
        if has_materials:
            self._export_mesh_with_materials_to_smd(sb, obj, mesh)
        else:
            self._export_mesh_without_materials_to_smd(sb, mesh)

    def _export_collision_mesh_to_smd(self, sb, mesh):
        """Export the mesh to SMD format for collision."""
        for tri in mesh.loop_triangles:
            self._write_triangle(sb, "Phy", mesh, tri)

    def _export_mesh_with_materials_to_smd(self, sb, obj, mesh):
        """Export the mesh to SMD format with materials."""
        for tri in mesh.loop_triangles:
            material_name = obj.material_slots[tri.material_index].name
            self._write_triangle(sb, material_name, mesh, tri)

    def _export_mesh_without_materials_to_smd(self, sb, mesh):
        """Export the mesh to SMD format without materials."""
        for tri in mesh.loop_triangles:
            self._write_triangle(sb, "None", mesh, tri)

    def _write_triangle(self, sb, material_name, mesh, tri):
        """Write a single triangle to the string buffer."""
        vert_a, vert_b, vert_c = [mesh.vertices[i] for i in tri.vertices]
        pos_a, pos_b, pos_c = vert_a.co, vert_b.co, vert_c.co
        normal_a, normal_b, normal_c = vert_a.normal, vert_b.normal, vert_c.normal

        if not tri.use_smooth:
            normal = (pos_b - pos_a).cross(pos_c - pos_a).normalized()
            normal_a = normal
            normal_b = normal
            normal_c = normal

        uv_a, uv_b, uv_c = [mesh.uv_layers.active.data[loop].uv for loop in tri.loops]

        sb.write(
            f"{material_name}\n"
            f"0  {pos_a.x:.6f} {pos_a.y:.6f} {pos_a.z:.6f}  {normal_a.x:.6f} {normal_a.y:.6f} {normal_a.z:.6f}  {uv_a.x:.6f} {uv_a.y:.6f} 0\n"
            f"0  {pos_b.x:.6f} {pos_b.y:.6f} {pos_b.z:.6f}  {normal_b.x:.6f} {normal_b.y:.6f} {normal_b.z:.6f}  {uv_b.x:.6f} {uv_b.y:.6f} 0\n"
            f"0  {pos_c.x:.6f} {pos_c.y:.6f} {pos_c.z:.6f}  {normal_c.x:.6f} {normal_c.y:.6f} {normal_c.z:.6f}  {uv_c.x:.6f} {uv_c.y:.6f} 0\n"
        )