"""
Addon preferences: ODA path, import defaults, and branding / support links.
"""

import os
import shutil

import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty
from bpy.types import AddonPreferences


# --- Support / channel links ------------------------------------------------
URL_YOUTUBE = "https://www.youtube.com/@longlivethecube"
URL_COFFEE = "https://ko-fi.com/longlivethecube"
URL_GITHUB = "https://github.com/lylongfts/CAD2CUBE"
URL_ODA_DOWNLOAD = "https://www.opendesign.com/guestfiles/oda_file_converter"


def _guess_oda_path() -> str:
    """Try to find ODA File Converter in common install locations."""
    candidates = []
    program_files = [
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
    ]
    for pf in program_files:
        if not pf or not os.path.isdir(pf):
            continue
        try:
            for entry in os.listdir(pf):
                if entry.startswith("ODA") and "File Converter" in entry:
                    exe = os.path.join(pf, entry, "ODAFileConverter.exe")
                    if os.path.isfile(exe):
                        candidates.append(exe)
        except OSError:
            pass

    for name in ("ODAFileConverter", "TeighaFileConverter"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    return candidates[0] if candidates else ""


class CAD2CubePreferences(AddonPreferences):
    bl_idname = __package__

    oda_converter_path: StringProperty(
        name="ODA File Converter",
        description=(
            "Path to ODAFileConverter executable. Required for DWG import only. "
            "Download free from opendesign.com"
        ),
        subtype="FILE_PATH",
        default=_guess_oda_path(),
    )

    default_scale: FloatProperty(
        name="Default Scale",
        description="Default scale factor when unit auto-detect is disabled",
        default=0.001,
        min=0.000001,
        max=1000.0,
        precision=6,
    )

    default_auto_units: BoolProperty(
        name="Auto-detect Units",
        description="Read $INSUNITS from DXF header and convert to Blender meters",
        default=True,
    )

    default_recenter: BoolProperty(
        name="Recenter to Origin by Default",
        description=(
            "CAD files often use geographic/project coordinates far from origin. "
            "Recentering keeps imported geometry workable in Blender"
        ),
        default=True,
    )

    keep_temp_dxf: BoolProperty(
        name="Keep Temp DXF (DWG import)",
        description="Keep the intermediate DXF converted from DWG (for debugging)",
        default=False,
    )

    def draw(self, context):
        layout = self.layout

        # --- Branding header ------------------------------------------------
        box = layout.box()
        row = box.row()
        row.label(text="CAD2Cube", icon="MESH_GRID")
        row.label(text="Free forever • Made by Long Live The Cube")

        row = box.row(align=True)
        op = row.operator("cad2cube.open_url", text="YouTube Tutorials", icon="URL")
        op.url = URL_YOUTUBE
        op = row.operator("cad2cube.open_url", text="Support on Ko-fi", icon="FUND")
        op.url = URL_COFFEE
        op = row.operator("cad2cube.open_url", text="GitHub", icon="URL")
        op.url = URL_GITHUB

        # --- DWG conversion -------------------------------------------------
        box = layout.box()
        box.label(text="DWG Conversion (optional)", icon="FILE_CACHE")

        oda_ok = bool(self.oda_converter_path) and os.path.isfile(self.oda_converter_path)
        status_row = box.row()
        if oda_ok:
            status_row.label(text="ODA File Converter detected", icon="CHECKMARK")
        else:
            status_row.label(text="ODA File Converter not found", icon="ERROR")
            dl = box.row()
            op = dl.operator(
                "cad2cube.open_url",
                text="Download ODA File Converter (free)",
                icon="IMPORT",
            )
            op.url = URL_ODA_DOWNLOAD

        box.prop(self, "oda_converter_path")

        col = box.column(align=True)
        col.scale_y = 0.85
        col.label(text="DXF import works without ODA. ODA is only needed for .dwg files.",
                  icon="INFO")
        col.label(text="ODA File Converter is free from Open Design Alliance (account required).")

        # --- Import defaults ------------------------------------------------
        box = layout.box()
        box.label(text="Import Defaults", icon="SETTINGS")
        box.prop(self, "default_auto_units")
        row = box.row()
        row.enabled = not self.default_auto_units
        row.prop(self, "default_scale")
        box.prop(self, "default_recenter")
        box.prop(self, "keep_temp_dxf")


def get_prefs(context) -> CAD2CubePreferences:
    """Helper to fetch this addon's preferences."""
    return context.preferences.addons[__package__].preferences
