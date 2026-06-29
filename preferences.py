"""
Addon preferences: import defaults only.
"""

import bpy
from bpy.props import BoolProperty, FloatProperty
from bpy.types import AddonPreferences


class CAD2CubePreferences(AddonPreferences):
    bl_idname = __package__

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
            "Recentering keeps imported geometry workable"
        ),
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Import Defaults", icon="SETTINGS")
        box.prop(self, "default_auto_units")
        row = box.row()
        row.enabled = not self.default_auto_units
        row.prop(self, "default_scale")
        box.prop(self, "default_recenter")


def get_prefs(context) -> CAD2CubePreferences:
    """Helper to fetch this addon's preferences."""
    return context.preferences.addons[__package__].preferences
