"""
CAD2Cube — DXF Importer for Blender
====================================
Free & open source. Made by Long Live The Cube.

Import DXF files into Blender with proper unit handling,
layer-to-collection mapping, and block instancing.

License: GPL-3.0-or-later
"""

bl_info = {
    "name": "CAD2Cube — DXF Importer",
    "author": "Long Live The Cube",
    "version": (1, 5, 0),
    "blender": (4, 2, 0),
    "location": "File > Import > CAD2Cube (.dxf)",
    "description": "Import DXF with layers, units, and block support",
    "category": "Import-Export",
    "doc_url": "https://github.com/lylongfts/CAD2CUBE",
    "tracker_url": "https://github.com/lylongfts/CAD2CUBE/issues",
}

import bpy
from bpy.types import TOPBAR_MT_file_import

from . import preferences
from . import operators


def _menu_func_import_dxf(self, context):
    self.layout.operator(
        operators.IMPORT_OT_dxf.bl_idname,
        text="CAD2Cube — DXF (.dxf)",
        icon="MESH_GRID",
    )


_classes = (
    preferences.CAD2CubePreferences,
    operators.IMPORT_OT_dxf,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    TOPBAR_MT_file_import.append(_menu_func_import_dxf)


def unregister():
    TOPBAR_MT_file_import.remove(_menu_func_import_dxf)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
