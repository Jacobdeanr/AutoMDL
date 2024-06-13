class QCWriter:
    def __init__(self, paths, attributes, flags):
        self.paths = paths
        self.attributes = attributes
        self.flags = flags

    def write_qc_file(self):
        """Write the QC file with all necessary information."""
        with open(self.paths['qc_path'], "w") as file:
            self._write_model_section(file)
            self._write_static_prop(file)
            self._write_mostly_opaque(file)
            self._write_surface_prop(file)
            self._write_cdmaterials(file)
            self._write_sequence(file)
            if self.flags['has_collision']:
                self._write_collision_model(file)

    def _write_model_section(self, file):
        file.write(f"$modelname \"{self.paths['qc_modelpath']}.mdl\"\n\n")
        file.write(f"$bodygroup \"Body\"\n{{\n\tstudio \"{self.paths['qc_vismesh']}.smd\"\n}}\n")

    def _write_static_prop(self, file):
        if self.flags['qc_staticprop']:
            file.write("\n$staticprop\n")

    def _write_mostly_opaque(self, file):
        if self.flags['qc_mostlyopaque']:
            file.write("\n$mostlyopaque\n")

    def _write_surface_prop(self, file):
        file.write(f"\n$surfaceprop \"{self.attributes['qc_surfaceprop']}\"\n\n")
        file.write("$contents \"solid\"\n\n")

    def _write_cdmaterials(self, file):
        for material_path in self.attributes['qc_cdmaterials_list']:
            file.write(f"$cdmaterials \"{material_path}\"\n")
        if not self.flags['has_materials']:
            file.write(f"$cdmaterials \"\"\n")

    def _write_sequence(self, file):
        file.write(f"\n$sequence \"idle\" {{\n\t\"{self.paths['qc_vismesh']}.smd\"\n\tfps 30\n\tfadein 0.2\n\tfadeout 0.2\n\tloop\n}}\n")

    def _write_collision_model(self, file):
        file.write(f"\n$collisionmodel \"{self.paths['qc_phymesh']}.smd\" {{")
        if self.flags['qc_concave']:
            file.write(f"\n\t$concave\n\t$maxconvexpieces {self.attributes['qc_maxconvexpieces']}")
        file.write(f"\n\t$mass {self.attributes['qc_mass']}\n\t$inertia 1\n\t$damping 0\n\t$rotdamping 0\n\t$rootbone \" \"\n}}\n")