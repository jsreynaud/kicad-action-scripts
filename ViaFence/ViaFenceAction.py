#
#  ViaFenceAction.py
#  Place vias along selected tracks or graphic lines
#
#  Copyright 2025 Geoff Wall / Ceres Imaging
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#

import pcbnew
import wx
import math
import os


class ViaFenceDialog(wx.Dialog):
    """Dialog for via fence settings"""

    MM_PER_MIL = 0.0254
    MIL_PER_MM = 1.0 / MM_PER_MIL

    def __init__(self, parent, board):
        wx.Dialog.__init__(self, parent, title="Via Fence Generator",
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.board = board
        self.design_settings = board.GetDesignSettings()
        self.current_unit = "mm"

        # Get default via size from board
        default_via_size = pcbnew.ToMM(self.design_settings.GetCurrentViaSize())
        default_via_drill = pcbnew.ToMM(self.design_settings.GetCurrentViaDrill())

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Instructions
        instructions = wx.StaticText(self, label="Select track(s) or graphic line(s) before running.\n"
                                                  "Vias will be placed along the selected items.")
        sizer.Add(instructions, 0, wx.ALL, 10)

        # Grid for parameters
        grid = wx.FlexGridSizer(6, 3, 5, 10)
        grid.AddGrowableCol(1)

        # Unit selector
        grid.Add(wx.StaticText(self, label="Units:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.unit_ctrl = wx.ComboBox(self, choices=["mm", "mil"], style=wx.CB_READONLY)
        self.unit_ctrl.SetSelection(0)
        self.unit_ctrl.Bind(wx.EVT_COMBOBOX, self.OnUnitChange)
        grid.Add(self.unit_ctrl, 1, wx.EXPAND)
        grid.Add(wx.StaticText(self, label=""), 0)  # Empty cell

        # Via spacing
        self.spacing_label = wx.StaticText(self, label="Via spacing (mm):")
        grid.Add(self.spacing_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self.spacing_ctrl = wx.TextCtrl(self, value="2.54")
        self.spacing_ctrl.SetToolTip("Distance between via centers along the path")
        grid.Add(self.spacing_ctrl, 1, wx.EXPAND)
        self.spacing_help = wx.StaticText(self, label="")
        self.spacing_help.SetForegroundColour(wx.Colour(128, 128, 128))
        grid.Add(self.spacing_help, 0, wx.ALIGN_CENTER_VERTICAL)

        # Via size
        self.size_label = wx.StaticText(self, label="Via copper size (mm):")
        grid.Add(self.size_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self.size_ctrl = wx.TextCtrl(self, value=f"{default_via_size:.3f}")
        self.size_ctrl.SetToolTip("Outer diameter of via copper pad")
        grid.Add(self.size_ctrl, 1, wx.EXPAND)
        self.size_help = wx.StaticText(self, label="")
        self.size_help.SetForegroundColour(wx.Colour(128, 128, 128))
        grid.Add(self.size_help, 0, wx.ALIGN_CENTER_VERTICAL)

        # Via drill
        self.drill_label = wx.StaticText(self, label="Via drill size (mm):")
        grid.Add(self.drill_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self.drill_ctrl = wx.TextCtrl(self, value=f"{default_via_drill:.3f}")
        self.drill_ctrl.SetToolTip("Diameter of drilled hole")
        grid.Add(self.drill_ctrl, 1, wx.EXPAND)
        self.drill_help = wx.StaticText(self, label="")
        self.drill_help.SetForegroundColour(wx.Colour(128, 128, 128))
        grid.Add(self.drill_help, 0, wx.ALIGN_CENTER_VERTICAL)

        # Offset from path (for fencing on both sides)
        self.offset_label = wx.StaticText(self, label="Offset from path (mm):")
        grid.Add(self.offset_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self.offset_ctrl = wx.TextCtrl(self, value="0")
        self.offset_ctrl.SetToolTip("0 = on the path\n"
                                    "> 0 = offset to both sides (creates fence)")
        grid.Add(self.offset_ctrl, 1, wx.EXPAND)
        self.offset_help = wx.StaticText(self, label="")
        self.offset_help.SetForegroundColour(wx.Colour(128, 128, 128))
        grid.Add(self.offset_help, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        # Net selection (separate row, full width)
        net_sizer = wx.BoxSizer(wx.HORIZONTAL)
        net_sizer.Add(wx.StaticText(self, label="Net:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.net_ctrl = wx.ComboBox(self, style=wx.CB_READONLY)
        self._populate_nets()
        net_sizer.Add(self.net_ctrl, 1, wx.EXPAND)
        sizer.Add(net_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        sizer.AddSpacer(10)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self, wx.ID_OK, "Place Vias")
        ok_btn.SetDefault()
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(wx.Button(self, wx.ID_CANCEL))
        btn_sizer.Realize()
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        self.Fit()
        self.Centre()

        # Bind text change events for live conversion display
        self.spacing_ctrl.Bind(wx.EVT_TEXT, self.OnValueChange)
        self.size_ctrl.Bind(wx.EVT_TEXT, self.OnValueChange)
        self.drill_ctrl.Bind(wx.EVT_TEXT, self.OnValueChange)
        self.offset_ctrl.Bind(wx.EVT_TEXT, self.OnValueChange)

        # Detect KiCad units and set accordingly
        self._detect_kicad_units()
        self.UpdateHelpText()

    def _detect_kicad_units(self):
        """Detect KiCad's current display units"""
        try:
            units = pcbnew.GetUserUnits()
            if hasattr(pcbnew, 'EDA_UNITS_MILS') and units == pcbnew.EDA_UNITS_MILS:
                self._switch_to_mil()
            elif units == 5:  # EDA_UNITS_MILS value
                self._switch_to_mil()
        except:
            pass

    def _switch_to_mil(self):
        """Switch display to mils"""
        if self.current_unit == "mm":
            self.unit_ctrl.SetSelection(1)
            self.OnUnitChange(None)

    def OnUnitChange(self, event):
        """Handle unit change"""
        new_unit = self.unit_ctrl.GetStringSelection()
        if new_unit == self.current_unit:
            return

        # Convert all values
        if new_unit == "mil":
            factor = self.MIL_PER_MM
            self.spacing_label.SetLabel("Via spacing (mil):")
            self.size_label.SetLabel("Via copper size (mil):")
            self.drill_label.SetLabel("Via drill size (mil):")
            self.offset_label.SetLabel("Offset from path (mil):")
        else:
            factor = self.MM_PER_MIL
            self.spacing_label.SetLabel("Via spacing (mm):")
            self.size_label.SetLabel("Via copper size (mm):")
            self.drill_label.SetLabel("Via drill size (mm):")
            self.offset_label.SetLabel("Offset from path (mm):")

        # Convert values
        for ctrl in [self.spacing_ctrl, self.size_ctrl, self.drill_ctrl, self.offset_ctrl]:
            try:
                val = float(ctrl.GetValue().replace(',', '.'))
                ctrl.SetValue(f"{val * factor:.3f}")
            except:
                pass

        self.current_unit = new_unit
        self.UpdateHelpText()
        self.Layout()

    def OnValueChange(self, event):
        """Update help text when values change"""
        self.UpdateHelpText()
        event.Skip()

    def UpdateHelpText(self):
        """Update help text showing converted values"""
        if self.current_unit == "mm":
            factor = self.MIL_PER_MM
            unit_str = "mil"
        else:
            factor = self.MM_PER_MIL
            unit_str = "mm"

        for ctrl, help_label in [(self.spacing_ctrl, self.spacing_help),
                                  (self.size_ctrl, self.size_help),
                                  (self.drill_ctrl, self.drill_help),
                                  (self.offset_ctrl, self.offset_help)]:
            try:
                val = float(ctrl.GetValue().replace(',', '.'))
                help_label.SetLabel(f"({val * factor:.2f} {unit_str})")
            except:
                help_label.SetLabel("")

    def _populate_nets(self):
        """Populate net dropdown"""
        netnames = set()
        for zone in self.board.Zones():
            netnames.add(zone.GetNetname())
        for track in self.board.GetTracks():
            netnames.add(track.GetNetname())

        netnames = sorted(list(netnames))
        self.net_ctrl.Set(netnames)

        # Default to GND
        idx = self.net_ctrl.FindString("GND")
        if idx == wx.NOT_FOUND:
            idx = self.net_ctrl.FindString("/GND")
        if idx != wx.NOT_FOUND:
            self.net_ctrl.SetSelection(idx)
        elif netnames:
            self.net_ctrl.SetSelection(0)

    def _get_value_mm(self, ctrl):
        """Get value from control in mm"""
        try:
            val = float(ctrl.GetValue().replace(',', '.'))
            if self.current_unit == "mil":
                val *= self.MM_PER_MIL
            return val
        except:
            return 0

    def GetSpacingMM(self):
        return self._get_value_mm(self.spacing_ctrl)

    def GetViaSizeMM(self):
        return self._get_value_mm(self.size_ctrl)

    def GetViaDrillMM(self):
        return self._get_value_mm(self.drill_ctrl)

    def GetOffsetMM(self):
        return self._get_value_mm(self.offset_ctrl)

    def GetNetname(self):
        return self.net_ctrl.GetStringSelection()


class ViaFenceAction(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Via Fence Generator"
        self.category = "Modify PCB"
        self.description = "Place vias along selected tracks or lines"
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "via-fence.png")
        self.show_toolbar_button = True

    def Run(self):
        board = pcbnew.GetBoard()

        # Get selected items
        selected_items = []
        for track in board.GetTracks():
            if track.IsSelected() and not isinstance(track, pcbnew.PCB_VIA):
                selected_items.append(track)

        for drawing in board.GetDrawings():
            if drawing.IsSelected():
                if drawing.GetClass() in ["PCB_SHAPE", "DRAWSEGMENT"]:
                    selected_items.append(drawing)

        if not selected_items:
            wx.MessageBox("Please select one or more tracks or graphic lines first.",
                          "No Selection", wx.OK | wx.ICON_WARNING)
            return

        # Show dialog
        dlg = ViaFenceDialog(None, board)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        spacing_mm = dlg.GetSpacingMM()
        via_size_mm = dlg.GetViaSizeMM()
        via_drill_mm = dlg.GetViaDrillMM()
        offset_mm = dlg.GetOffsetMM()
        netname = dlg.GetNetname()
        dlg.Destroy()

        # Convert to internal units
        spacing = pcbnew.FromMM(spacing_mm)
        via_size = pcbnew.FromMM(via_size_mm)
        via_drill = pcbnew.FromMM(via_drill_mm)
        offset = pcbnew.FromMM(offset_mm)

        # Get net
        net = board.FindNet(netname)
        if net is None:
            wx.MessageBox(f"Net '{netname}' not found.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Place vias along each selected item
        vias_placed = 0
        for item in selected_items:
            vias_placed += self._place_vias_along_item(board, item, spacing, via_size,
                                                        via_drill, net, offset)

        pcbnew.Refresh()
        wx.MessageBox(f"Placed {vias_placed} vias along {len(selected_items)} item(s).",
                      "Via Fence Complete", wx.OK | wx.ICON_INFORMATION)

    def _place_vias_along_item(self, board, item, spacing, via_size, via_drill, net, offset):
        """Place vias along a track or graphic line"""
        vias_placed = 0

        # Get start and end points
        if hasattr(item, 'GetStart') and hasattr(item, 'GetEnd'):
            start = item.GetStart()
            end = item.GetEnd()
        else:
            return 0

        # Calculate path length and direction
        dx = end.x - start.x
        dy = end.y - start.y
        length = math.sqrt(dx * dx + dy * dy)

        if length < spacing:
            # Path too short, place one via at center
            positions = [(start.x + dx / 2, start.y + dy / 2)]
        else:
            # Calculate number of vias and positions
            num_vias = int(length / spacing) + 1
            positions = []
            for i in range(num_vias):
                t = i / max(1, num_vias - 1) if num_vias > 1 else 0.5
                x = start.x + t * dx
                y = start.y + t * dy
                positions.append((x, y))

        # Calculate perpendicular direction for offset
        if offset > 0 and length > 0:
            # Perpendicular unit vector
            perp_x = -dy / length
            perp_y = dx / length

            # Create offset positions on both sides
            offset_positions = []
            for x, y in positions:
                offset_positions.append((x + perp_x * offset, y + perp_y * offset))
                offset_positions.append((x - perp_x * offset, y - perp_y * offset))
            positions = offset_positions

        # Place vias
        for x, y in positions:
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
            via.SetWidth(via_size)
            via.SetDrill(via_drill)
            via.SetNet(net)
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            board.Add(via)
            vias_placed += 1

        return vias_placed


# Register the plugin
ViaFenceAction().register()
