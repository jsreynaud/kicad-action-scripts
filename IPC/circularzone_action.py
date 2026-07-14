#!/usr/bin/env python3
#
#  circularzone_action.py
#
#  Circular zone / keep-out generator for KiCad
#  Ported to the KiCad IPC API (kicad-python), 2026
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

import math
import sys
import traceback

import wx

from kipy.board_types import BoardLayer, FootprintInstance, Zone, ZoneType
from kicad_connect import connect_to_kicad
from kipy.common_types import PolygonWithHoles
from kipy.geometry import PolyLine, PolyLineNode
from kipy.util.units import from_mm


def build_circle_outline(center_x, center_y, radius, edge_count):
    outline = PolyLine()
    for i in range(edge_count):
        angle = i * 2 * math.pi / edge_count
        outline.append(
            PolyLineNode.from_xy(
                int(center_x + radius * math.cos(angle)),
                int(center_y + radius * math.sin(angle)),
            )
        )
    outline.append(outline[0])
    outline.closed = True
    polygon = PolygonWithHoles()
    polygon.outline = outline
    return polygon


def build_zone(center_x, center_y, radius, edge_count, keepout, layer):
    zone = Zone()
    zone.layers = [layer]
    zone.outline = build_circle_outline(center_x, center_y, radius, edge_count)
    if keepout:
        zone.type = ZoneType.ZT_RULE_AREA
        settings = zone.proto.rule_area_settings
        settings.keepout_copper = True
        settings.keepout_vias = True
        settings.keepout_tracks = True
        settings.keepout_pads = True
        settings.keepout_footprints = True
        zone.name = "CircularZone keep-out"
    return zone


class CircularZoneDialog(wx.Dialog):
    def __init__(self, board, reference):
        super().__init__(None, title="Circular Zone (IPC)")

        grid = wx.FlexGridSizer(0, 2, 4, 8)
        grid.AddGrowableCol(1)

        def add_row(label, ctrl):
            grid.Add(
                wx.StaticText(self, label=label),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
                4,
            )
            grid.Add(ctrl, 1, wx.EXPAND | wx.RIGHT, 4)
            return ctrl

        self.radius = add_row("Radius (mm)", wx.TextCtrl(self, value="10"))
        self.segments = add_row("Segment count", wx.TextCtrl(self, value="36"))

        copper_layers = [
            l for l in board.get_enabled_layers() if BoardLayer.Name(l).endswith("_Cu")
        ]
        self.layer_values = copper_layers
        layer_names = [board.get_layer_name(l) for l in copper_layers]
        self.layer = add_row(
            "Layer",
            wx.ComboBox(
                self,
                value=layer_names[0] if layer_names else "",
                choices=layer_names,
                style=wx.CB_READONLY,
            ),
        )
        self.keepout = add_row("Keep-out area", wx.CheckBox(self))
        self.keepout.SetValue(True)

        comment = (
            "Using {} as position reference".format(reference)
            if reference
            else "No footprint selected: center at origin (0, 0)"
        )

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok_btn = wx.Button(self, wx.ID_OK, "Create")
        ok_btn.SetDefault()
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Cancel")
        buttons.AddStretchSpacer()
        buttons.Add(ok_btn, 0, wx.ALL, 4)
        buttons.Add(cancel_btn, 0, wx.ALL, 4)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(wx.StaticText(self, label=comment), 0, wx.ALL, 8)
        outer.Add(grid, 1, wx.EXPAND | wx.ALL, 8)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 4)
        self.SetSizerAndFit(outer)
        self.Centre()


def main():
    app = wx.App()
    try:
        kicad, board = connect_to_kicad(client_name="circular-zone")
    except Exception as e:
        wx.MessageBox(
            "Could not connect to KiCad:\n\n{}".format(e), "Circular Zone", wx.ICON_ERROR
        )
        return 1

    center_x, center_y = 0, 0
    reference = None
    try:
        for item in board.get_selection():
            if isinstance(item, FootprintInstance):
                center_x = item.position.x
                center_y = item.position.y
                reference = item.reference_field.text.value
                break
    except Exception:
        pass

    dialog = CircularZoneDialog(board, reference)
    try:
        if dialog.ShowModal() != wx.ID_OK:
            return 0

        try:
            radius = float(dialog.radius.GetValue().replace(",", "."))
            segments = int(float(dialog.segments.GetValue().replace(",", ".")))
            if radius <= 0 or segments < 3:
                raise ValueError
        except ValueError:
            wx.MessageBox(
                "Radius must be a positive number and segment count at least 3",
                "Circular Zone",
                wx.ICON_WARNING,
            )
            return 1

        layer_index = dialog.layer.GetSelection()
        layer = (
            dialog.layer_values[layer_index]
            if 0 <= layer_index < len(dialog.layer_values)
            else BoardLayer.BL_F_Cu
        )

        zone = build_zone(
            center_x,
            center_y,
            from_mm(radius),
            segments,
            dialog.keepout.IsChecked(),
            layer,
        )

        commit = board.begin_commit()
        try:
            board.create_items(zone)
            board.push_commit(commit, "Create circular zone")
        except Exception:
            board.drop_commit(commit)
            raise
    except Exception as e:
        traceback.print_exc()
        wx.MessageBox("Error: {}".format(e), "Circular Zone", wx.ICON_ERROR)
        return 1
    finally:
        dialog.Destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
