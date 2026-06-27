"""
Layer manager: maps DXF layers to Blender collections (or materials, or flat).
"""

from __future__ import annotations

from typing import Dict

import bpy


# Mode constants (kept as strings to match operator EnumProperty values)
MODE_COLLECTIONS = "COLLECTIONS"
MODE_MATERIALS = "MATERIALS"
MODE_FLAT = "FLAT"


class LayerManager:
    """Routes imported objects into the right collection / assigns materials."""

    def __init__(self, mode: str, root_collection: bpy.types.Collection):
        self.mode = mode
        self.root = root_collection
        self._collections: Dict[str, bpy.types.Collection] = {}
        self._materials: Dict[str, bpy.types.Material] = {}

    # --- Public API ---------------------------------------------------------
    def prepare(self, layer_name: str, rgb: tuple[float, float, float]):
        """Pre-create the collection or material for a layer."""
        if self.mode == MODE_COLLECTIONS:
            self._get_or_create_collection(layer_name)
        elif self.mode == MODE_MATERIALS:
            self._get_or_create_material(layer_name, rgb)
        # FLAT mode: no per-layer setup needed

    def link_object(self, obj: bpy.types.Object, layer_name: str, rgb):
        """Place `obj` in the correct collection and/or assign material."""
        if self.mode == MODE_COLLECTIONS:
            coll = self._get_or_create_collection(layer_name)
            coll.objects.link(obj)
        elif self.mode == MODE_MATERIALS:
            self.root.objects.link(obj)
            mat = self._get_or_create_material(layer_name, rgb)
            if obj.data and hasattr(obj.data, "materials"):
                obj.data.materials.append(mat)
        else:  # FLAT
            self.root.objects.link(obj)

    # --- Internals ----------------------------------------------------------
    def _get_or_create_collection(self, name: str) -> bpy.types.Collection:
        if name in self._collections:
            return self._collections[name]

        # Sanitize: Blender collection names max 63 chars, can't be empty
        clean = (name or "Layer_0")[:63]
        coll = bpy.data.collections.new(clean)
        self.root.children.link(coll)
        self._collections[name] = coll
        return coll

    def _get_or_create_material(self, name: str, rgb) -> bpy.types.Material:
        if name in self._materials:
            return self._materials[name]

        mat = bpy.data.materials.new(name=f"DXF_{name}"[:63])
        mat.use_nodes = True
        # Set viewport color + Principled BSDF base color
        mat.diffuse_color = (*rgb, 1.0)
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    # Use string key — version-safe across Blender 3.x/4.x
                    if "Base Color" in node.inputs:
                        node.inputs["Base Color"].default_value = (*rgb, 1.0)
                    break
        self._materials[name] = mat
        return mat
