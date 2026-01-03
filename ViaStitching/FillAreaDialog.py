# -*- coding: utf-8 -*-
#
#  FillAreaDialog.py
#  Via stitching dialog with unit selector and enhanced options
#
#  Based on wxFormBuilder dialog by JS Reynaud <js.reynaud@gmail.com>
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com>
#  Copyright 2025 Geoff Wall / Ceres Imaging (enhancements)
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
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see <http://www.gnu.org/licenses/>.
#

import os
import json
import wx
import wx.xrc


class FillAreaDialog(wx.Dialog):
    """
    Via Stitching dialog with all original features plus enhancements:
    - Unit selector (mil/mm) with live conversion
    - Hole clearance parameter
    - Nudge search option
    - Pattern tooltips explaining each fill type
    - Group management for easy via removal
    """

    # Conversion constants
    MM_PER_MIL = 0.0254
    MIL_PER_MM = 1.0 / MM_PER_MIL

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY,
                           title=u"Via Stitching Generator",
                           pos=wx.DefaultPosition,
                           size=wx.DefaultSize,  # Will be auto-sized by Fit()
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.board = None
        self.current_unit = "mm"  # Track current unit

        # Main sizer
        bSizer3 = wx.BoxSizer(wx.VERTICAL)

        # Help image
        help_image_path = os.path.join(os.path.dirname(__file__), "stitching-vias-help.png")
        if os.path.exists(help_image_path):
            self.m_bitmapStitching = wx.StaticBitmap(self, wx.ID_ANY,
                                                     wx.Bitmap(help_image_path, wx.BITMAP_TYPE_PNG))
            bSizer3.Add(self.m_bitmapStitching, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        else:
            self.m_bitmapStitching = wx.StaticBitmap(self, wx.ID_ANY, wx.NullBitmap)

        # Grid sizer for parameters (3 columns: label, input, help text)
        fgSizer1 = wx.FlexGridSizer(0, 3, 0, 0)
        fgSizer1.AddGrowableCol(1)
        fgSizer1.SetFlexibleDirection(wx.BOTH)
        fgSizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        # ---- Unit selector ----
        self.m_staticTextUnit = wx.StaticText(self, wx.ID_ANY, u"Units")
        self.m_staticTextUnit.SetToolTip(u"Choose mil (thousandths of inch) or mm")
        fgSizer1.Add(self.m_staticTextUnit, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_cbUnit = wx.ComboBox(self, wx.ID_ANY, u"mm",
                                    choices=[u"mm", u"mil"],
                                    style=wx.CB_READONLY)
        self.m_cbUnit.SetSelection(0)
        self.m_cbUnit.SetToolTip(u"mm = millimeters\nmil = thousandths of inch (1 mil = 0.0254 mm)\n\n"
                                 u"Switching units converts all values automatically.")
        self.m_cbUnit.Bind(wx.EVT_COMBOBOX, self.OnUnitChange)
        fgSizer1.Add(self.m_cbUnit, 1, wx.ALL | wx.EXPAND, 5)
        fgSizer1.Add((0, 0), 1, wx.EXPAND, 5)  # Empty cell

        # ---- Via copper size ----
        self.m_staticText3 = wx.StaticText(self, wx.ID_ANY, u"Via copper size (mm)")
        self.m_staticText3.SetToolTip(u"Outer diameter of the via's copper pad")
        fgSizer1.Add(self.m_staticText3, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_SizeMM = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString)
        self.m_SizeMM.SetToolTip(u"The outer diameter of the copper annular ring.\n\n"
                                 u"Typical values:\n"
                                 u"  0.5-0.6 mm (20-24 mil) - Standard\n"
                                 u"  0.4-0.45 mm (16-18 mil) - Small/dense\n"
                                 u"  0.7-0.8 mm (28-32 mil) - High-current")
        fgSizer1.Add(self.m_SizeMM, 1, wx.ALL | wx.EXPAND, 5)

        self.m_sizeHelp = wx.StaticText(self, wx.ID_ANY, u"")
        self.m_sizeHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_sizeHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Via drill size ----
        self.m_staticText9 = wx.StaticText(self, wx.ID_ANY, u"Via drill size (mm)")
        self.m_staticText9.SetToolTip(u"Diameter of the drilled hole")
        fgSizer1.Add(self.m_staticText9, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_DrillMM = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString)
        self.m_DrillMM.SetToolTip(u"The finished plated hole diameter.\n\n"
                                  u"Typical values:\n"
                                  u"  0.3-0.35 mm (12-14 mil) - Standard\n"
                                  u"  0.2-0.25 mm (8-10 mil) - Small\n\n"
                                  u"Must be smaller than copper size!")
        fgSizer1.Add(self.m_DrillMM, 1, wx.ALL | wx.EXPAND, 5)

        self.m_drillHelp = wx.StaticText(self, wx.ID_ANY, u"")
        self.m_drillHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_drillHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Via clearance ----
        self.m_staticText5 = wx.StaticText(self, wx.ID_ANY, u"Via clearance (mm)")
        self.m_staticText5.SetToolTip(u"Minimum clearance from via copper to other copper")
        fgSizer1.Add(self.m_staticText5, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_ClearanceMM = wx.TextCtrl(self, wx.ID_ANY, wx.EmptyString)
        self.m_ClearanceMM.SetToolTip(u"Clearance from via edge to other copper.\n\n"
                                      u"Uses your board's design rules by default.")
        fgSizer1.Add(self.m_ClearanceMM, 1, wx.ALL | wx.EXPAND, 5)

        self.m_clearanceHelp = wx.StaticText(self, wx.ID_ANY, u"")
        self.m_clearanceHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_clearanceHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Hole clearance (NEW) ----
        self.m_staticTextHoleClearance = wx.StaticText(self, wx.ID_ANY, u"Hole clearance (mm)")
        self.m_staticTextHoleClearance.SetToolTip(u"Minimum hole-to-hole distance")
        fgSizer1.Add(self.m_staticTextHoleClearance, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_HoleClearanceMM = wx.TextCtrl(self, wx.ID_ANY, u"0.5")
        self.m_HoleClearanceMM.SetToolTip(u"Minimum distance between via drill and other holes.\n\n"
                                          u"Important for:\n"
                                          u"  - Drill bit breakage prevention\n"
                                          u"  - PTH component clearance\n\n"
                                          u"Typical: 0.5 mm (20 mil) minimum")
        fgSizer1.Add(self.m_HoleClearanceMM, 1, wx.ALL | wx.EXPAND, 5)

        self.m_holeClearanceHelp = wx.StaticText(self, wx.ID_ANY, u"")
        self.m_holeClearanceHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_holeClearanceHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Via spacing ----
        self.m_staticText2 = wx.StaticText(self, wx.ID_ANY, u"Via spacing (mm)")
        self.m_staticText2.SetToolTip(u"Distance between via centers")
        fgSizer1.Add(self.m_staticText2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_StepMM = wx.TextCtrl(self, wx.ID_ANY, u"2.54")
        self.m_StepMM.SetToolTip(u"Spacing between via centers.\n\n"
                                 u"Common values:\n"
                                 u"  2.54 mm (100 mil) - Standard\n"
                                 u"  1.27 mm (50 mil) - Dense\n"
                                 u"  5.08 mm (200 mil) - Sparse\n\n"
                                 u"Smaller = more vias, better thermal/electrical\n"
                                 u"Larger = fewer vias, less crowded")
        fgSizer1.Add(self.m_StepMM, 1, wx.ALL | wx.EXPAND, 5)

        self.m_stepHelp = wx.StaticText(self, wx.ID_ANY, u"")
        self.m_stepHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_stepHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer3.Add(fgSizer1, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Layers to ignore section ----
        layerBox = wx.StaticBox(self, wx.ID_ANY, u"Layers to ignore during placement")
        layerSizer = wx.StaticBoxSizer(layerBox, wx.VERTICAL)

        self.m_layerList = wx.CheckListBox(self, wx.ID_ANY, size=(-1, 180))
        self.m_layerList.SetToolTip(u"Check layers to IGNORE during via placement.\n\n"
                                    u"Vias will pass through zones on checked layers.\n"
                                    u"Useful for internal power planes (PWR5, PWR6, etc.)\n\n"
                                    u"After placement, press 'B' to refill all zones.")
        layerSizer.Add(self.m_layerList, 1, wx.ALL | wx.EXPAND, 5)

        bSizer3.Add(layerSizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Net and Pattern selection (2 columns) ----
        fgSizer2 = wx.FlexGridSizer(0, 2, 0, 0)
        fgSizer2.AddGrowableCol(1)
        fgSizer2.SetFlexibleDirection(wx.BOTH)

        # Net name
        self.m_staticText6 = wx.StaticText(self, wx.ID_ANY, u"Net name")
        self.m_staticText6.SetToolTip(u"Which net to fill with vias")
        fgSizer2.Add(self.m_staticText6, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_cbNet = wx.ComboBox(self, wx.ID_ANY, u"GND",
                                   choices=[],
                                   style=wx.CB_READONLY)
        self.m_cbNet.SetToolTip(u"Select the net to fill with stitching vias.\n\n"
                                u"Usually GND for ground plane stitching.")
        fgSizer2.Add(self.m_cbNet, 1, wx.ALL | wx.EXPAND, 5)

        # Pattern
        self.m_staticText42 = wx.StaticText(self, wx.ID_ANY, u"Pattern")
        self.m_staticText42.SetToolTip(u"Via placement pattern")
        fgSizer2.Add(self.m_staticText42, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # Pattern dropdown with info button
        patternSizer = wx.BoxSizer(wx.HORIZONTAL)
        m_cbFillTypeChoices = [u"Rectangular", u"Staggered", u"Concentric", u"Outline", u"Outline (No Holes)"]
        self.m_cbFillType = wx.ComboBox(self, wx.ID_ANY, u"Rectangular",
                                        choices=m_cbFillTypeChoices,
                                        style=wx.CB_READONLY)
        self.m_cbFillType.SetSelection(0)
        self.m_cbFillType.Bind(wx.EVT_COMBOBOX, self.OnPatternChange)
        patternSizer.Add(self.m_cbFillType, 1, wx.EXPAND, 0)

        # Info button
        self.m_btnPatternInfo = wx.Button(self, wx.ID_ANY, "Help")
        self.m_btnPatternInfo.SetToolTip(u"Click to see pattern diagram")
        self.m_btnPatternInfo.Bind(wx.EVT_BUTTON, self.OnPatternInfoClick)
        patternSizer.Add(self.m_btnPatternInfo, 0, wx.LEFT, 5)

        fgSizer2.Add(patternSizer, 1, wx.ALL | wx.EXPAND, 5)

        bSizer3.Add(fgSizer2, 0, wx.EXPAND | wx.ALL, 5)

        # Pattern descriptions for tooltips
        self.pattern_descriptions = {
            "Rectangular": "Simple Grid\n"
                          "Vias placed on a regular rectangular grid pattern.\n\n"
                          "Best for: General purpose ground plane stitching",
            "Staggered": "Brick/Honeycomb Pattern\n"
                        "Every other row is offset by half the spacing.\n\n"
                        "Best for: ~15% denser packing than rectangular",
            "Concentric": "Concentric Rings\n"
                         "Vias follow the zone outline inward in concentric rings.\n\n"
                         "Best for: Thermal management, EMI shielding",
            "Outline": "Perimeter Only\n"
                      "Vias placed only along zone edges, including around holes.\n\n"
                      "Best for: Via fencing around sensitive areas",
            "Outline (No Holes)": "Simple Perimeter\n"
                                 "Like Outline but ignores internal cutouts.\n\n"
                                 "Best for: Simple perimeter fence without internal features"
        }
        # Set initial tooltip
        self._UpdatePatternTooltip()

        # ---- Checkboxes ----
        fgSizer3 = wx.FlexGridSizer(0, 2, 0, 0)
        fgSizer3.AddGrowableCol(0)

        # Nudge search (NEW)
        self.m_staticTextNudge = wx.StaticText(self, wx.ID_ANY, u"Enable nudge search")
        self.m_staticTextNudge.SetToolTip(u"Try nearby positions when grid point is blocked")
        fgSizer3.Add(self.m_staticTextNudge, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Nudge = wx.CheckBox(self, wx.ID_ANY, wx.EmptyString)
        self.m_Nudge.SetValue(True)
        self.m_Nudge.SetToolTip(u"When a grid position is blocked, search nearby\n"
                                u"in a spiral pattern to find a valid position.\n\n"
                                u"This can place 30-50% more vias in dense areas!")
        fgSizer3.Add(self.m_Nudge, 0, wx.ALL, 5)

        # Random offset
        self.m_staticText8 = wx.StaticText(self, wx.ID_ANY, u"Random offset")
        self.m_staticText8.SetToolTip(u"Add random offset to via positions")
        fgSizer3.Add(self.m_staticText8, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Random = wx.CheckBox(self, wx.ID_ANY, wx.EmptyString)
        self.m_Random.SetToolTip(u"Adds small random offset to each via position.\n"
                                 u"Can help with resonance in RF designs.")
        fgSizer3.Add(self.m_Random, 0, wx.ALL, 5)

        # Only selected zone
        self.m_staticText81 = wx.StaticText(self, wx.ID_ANY, u"Only under selected Zone")
        self.m_staticText81.SetToolTip(u"Limit vias to selected zone only")
        fgSizer3.Add(self.m_staticText81, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_only_selected = wx.CheckBox(self, wx.ID_ANY, wx.EmptyString)
        self.m_only_selected.SetToolTip(u"Only place vias under the currently selected zone.\n\n"
                                        u"Select a zone in PCB editor before running.")
        fgSizer3.Add(self.m_only_selected, 0, wx.ALL, 5)

        # Also on tracks with same net
        self.m_staticText72 = wx.StaticText(self, wx.ID_ANY, u"Also on tracks with same net")
        self.m_staticText72.SetToolTip(u"Place vias on tracks of the same net")
        fgSizer3.Add(self.m_staticText72, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_sameNetTracks = wx.CheckBox(self, wx.ID_ANY, wx.EmptyString)
        self.m_sameNetTracks.SetToolTip(u"Allow vias to be placed on tracks that are\n"
                                        u"part of the same net (e.g., GND traces).")
        fgSizer3.Add(self.m_sameNetTracks, 0, wx.ALL, 5)

        bSizer3.Add(fgSizer3, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Group Management Section ----
        groupBox = wx.StaticBox(self, wx.ID_ANY, u"Manage Via Stitching Groups")
        groupSizer = wx.StaticBoxSizer(groupBox, wx.HORIZONTAL)

        self.m_cbGroups = wx.ComboBox(self, wx.ID_ANY, u"",
                                      choices=[],
                                      style=wx.CB_READONLY)
        self.m_cbGroups.SetToolTip(u"Select a via stitching group to delete.\n\n"
                                   u"Each run creates a numbered group like\n"
                                   u"'ViaStitching GND #1', '#2', etc.")
        groupSizer.Add(self.m_cbGroups, 1, wx.ALL | wx.EXPAND, 5)

        self.m_btnDeleteGroup = wx.Button(self, wx.ID_ANY, u"Delete Group")
        self.m_btnDeleteGroup.SetToolTip(u"Delete the selected via stitching group.\n"
                                         u"This removes all vias in that group.")
        self.m_btnDeleteGroup.Bind(wx.EVT_BUTTON, self.OnDeleteGroupClick)
        groupSizer.Add(self.m_btnDeleteGroup, 0, wx.ALL, 5)

        self.m_btnRefreshGroups = wx.Button(self, wx.ID_ANY, u"Refresh")
        self.m_btnRefreshGroups.SetToolTip(u"Refresh the list of via stitching groups")
        self.m_btnRefreshGroups.Bind(wx.EVT_BUTTON, self.OnRefreshGroupsClick)
        groupSizer.Add(self.m_btnRefreshGroups, 0, wx.ALL, 5)

        bSizer3.Add(groupSizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Buttons ----
        bSizer1 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer1.Add((0, 0), 1, wx.EXPAND, 5)  # Spacer

        self.m_button1 = wx.Button(self, wx.ID_OK, u"Run")
        self.m_button1.SetDefault()
        bSizer1.Add(self.m_button1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_button2 = wx.Button(self, wx.ID_CANCEL, u"Cancel")
        bSizer1.Add(self.m_button2, 0, wx.ALL, 5)

        self.m_button3_delete = wx.Button(self, wx.ID_DELETE, u"Delete All Vias")
        self.m_button3_delete.SetToolTip(u"Delete ALL stitching vias on the selected net.\n\n"
                                         u"Use 'Delete Group' above for surgical removal.")
        self.m_button3_delete.Bind(wx.EVT_BUTTON, self.onDeleteClick)
        bSizer1.Add(self.m_button3_delete, 0, wx.ALL, 5)

        bSizer3.Add(bSizer1, 0, wx.EXPAND | wx.ALIGN_RIGHT, 5)

        self.SetSizer(bSizer3)
        self.Layout()
        self.Fit()  # Auto-size dialog to fit all content
        self.SetMinSize(self.GetSize())  # Prevent shrinking smaller than content
        self.Centre(wx.BOTH)

        # Bind text change events for live unit conversion display
        self.m_SizeMM.Bind(wx.EVT_TEXT, self.OnValueChange)
        self.m_DrillMM.Bind(wx.EVT_TEXT, self.OnValueChange)
        self.m_ClearanceMM.Bind(wx.EVT_TEXT, self.OnValueChange)
        self.m_HoleClearanceMM.Bind(wx.EVT_TEXT, self.OnValueChange)
        self.m_StepMM.Bind(wx.EVT_TEXT, self.OnValueChange)

    def __del__(self):
        pass

    def SetBoard(self, board):
        """Set board reference for group management and layer list"""
        self.board = board
        self.RefreshGroups()
        self.PopulateLayers()

    def PopulateLayers(self):
        """Populate the layer checklist with copper layers from the board"""
        self.m_layerList.Clear()
        if self.board is None:
            return

        import pcbnew
        # Get all copper layers in stackup order (CuStack returns top-to-bottom order)
        layer_set = self.board.GetEnabledLayers()

        for layer_id in layer_set.CuStack():
            layer_name = self.board.GetLayerName(layer_id)
            self.m_layerList.Append(layer_name)

    def GetIgnoredLayers(self):
        """Get list of layer names that are checked (to be ignored)"""
        ignored = []
        for i in range(self.m_layerList.GetCount()):
            if self.m_layerList.IsChecked(i):
                ignored.append(self.m_layerList.GetString(i))
        return ignored

    def SetIgnoredLayers(self, layer_names):
        """Set which layers should be checked (ignored)"""
        for i in range(self.m_layerList.GetCount()):
            layer_name = self.m_layerList.GetString(i)
            self.m_layerList.Check(i, layer_name in layer_names)

    def RefreshGroups(self):
        """Refresh the list of via stitching groups"""
        self.m_cbGroups.Clear()
        if self.board is None:
            return

        groups = []
        for group in self.board.Groups():
            name = group.GetName()
            if name.startswith("ViaStitching"):
                groups.append(name)

        groups.sort()
        self.m_cbGroups.Set(groups)
        if groups:
            self.m_cbGroups.SetSelection(0)

    def OnRefreshGroupsClick(self, event):
        """Handle refresh button click"""
        self.RefreshGroups()

    def OnDeleteGroupClick(self, event):
        """Handle delete group button click"""
        if self.board is None:
            return

        group_name = self.m_cbGroups.GetStringSelection()
        if not group_name:
            wx.MessageBox("No group selected", "Delete Group", wx.OK | wx.ICON_WARNING)
            return

        # Confirm deletion
        result = wx.MessageBox(
            f"Delete all vias in '{group_name}'?\n\nThis cannot be undone.",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_QUESTION
        )

        if result != wx.YES:
            return

        # Find and delete the group
        for group in self.board.Groups():
            if group.GetName() == group_name:
                # Get all items in the group
                items = list(group.GetItems())
                # Remove items from board
                for item in items:
                    self.board.Remove(item)
                # Remove the group itself
                self.board.Remove(group)
                break

        # Refresh display
        import pcbnew
        pcbnew.Refresh()
        self.RefreshGroups()
        wx.MessageBox(f"Deleted {len(items)} vias from '{group_name}'",
                      "Delete Complete", wx.OK | wx.ICON_INFORMATION)

    def OnUnitChange(self, event):
        """Handle unit selector change - convert all values"""
        new_unit = self.m_cbUnit.GetStringSelection()
        if new_unit == self.current_unit:
            return

        # Get conversion factor
        if new_unit == "mil":
            factor = self.MIL_PER_MM
            self.m_staticText3.SetLabel(u"Via copper size (mil)")
            self.m_staticText9.SetLabel(u"Via drill size (mil)")
            self.m_staticText5.SetLabel(u"Via clearance (mil)")
            self.m_staticTextHoleClearance.SetLabel(u"Hole clearance (mil)")
            self.m_staticText2.SetLabel(u"Via spacing (mil)")
        else:
            factor = self.MM_PER_MIL
            self.m_staticText3.SetLabel(u"Via copper size (mm)")
            self.m_staticText9.SetLabel(u"Via drill size (mm)")
            self.m_staticText5.SetLabel(u"Via clearance (mm)")
            self.m_staticTextHoleClearance.SetLabel(u"Hole clearance (mm)")
            self.m_staticText2.SetLabel(u"Via spacing (mm)")

        # Convert values
        for ctrl in [self.m_SizeMM, self.m_DrillMM, self.m_ClearanceMM,
                     self.m_HoleClearanceMM, self.m_StepMM]:
            try:
                val = float(ctrl.GetValue().replace(',', '.'))
                ctrl.SetValue(f"{val * factor:.4g}")
            except ValueError:
                pass

        self.current_unit = new_unit
        self.UpdateHelpText()

    def OnValueChange(self, event):
        """Update help text when values change"""
        self.UpdateHelpText()
        event.Skip()

    def UpdateHelpText(self):
        """Update the gray help text showing converted units"""
        if self.current_unit == "mm":
            # Show mil equivalent
            fmt = "({:.2f} mil)"
            factor = self.MIL_PER_MM
        else:
            # Show mm equivalent
            fmt = "({:.4f} mm)"
            factor = self.MM_PER_MIL

        for ctrl, help_ctrl in [(self.m_SizeMM, self.m_sizeHelp),
                                (self.m_DrillMM, self.m_drillHelp),
                                (self.m_ClearanceMM, self.m_clearanceHelp),
                                (self.m_HoleClearanceMM, self.m_holeClearanceHelp),
                                (self.m_StepMM, self.m_stepHelp)]:
            try:
                val = float(ctrl.GetValue().replace(',', '.'))
                help_ctrl.SetLabel(fmt.format(val * factor))
            except ValueError:
                help_ctrl.SetLabel("")

    def GetUnit(self):
        """Get current unit selection"""
        return self.m_cbUnit.GetStringSelection()

    def GetValueMM(self, ctrl):
        """Get value from control, converted to mm"""
        try:
            val = float(ctrl.GetValue().replace(',', '.'))
            if self.current_unit == "mil":
                val *= self.MM_PER_MIL
            return val
        except ValueError:
            return 0.0

    def GetSizeValueMM(self):
        return self.GetValueMM(self.m_SizeMM)

    def GetDrillValueMM(self):
        return self.GetValueMM(self.m_DrillMM)

    def GetClearanceValueMM(self):
        return self.GetValueMM(self.m_ClearanceMM)

    def GetHoleClearanceValueMM(self):
        return self.GetValueMM(self.m_HoleClearanceMM)

    def GetStepValueMM(self):
        return self.GetValueMM(self.m_StepMM)

    def _UpdatePatternTooltip(self):
        """Update the Pattern dropdown tooltip based on current selection"""
        pattern = self.m_cbFillType.GetStringSelection()
        if pattern in self.pattern_descriptions:
            self.m_cbFillType.SetToolTip(self.pattern_descriptions[pattern])

    def OnPatternChange(self, event):
        """Update pattern tooltip when selection changes"""
        self._UpdatePatternTooltip()
        event.Skip()

    def OnPatternInfoClick(self, event):
        """Show pattern diagram dialog for selected pattern"""
        pattern_diagrams = {
            "Rectangular": """
┌─────────────────────┐
│  ●   ●   ●   ●   ●  │
│  ●   ●   ●   ●   ●  │
│  ●   ●   ●   ●   ●  │
│  ●   ●   ●   ●   ●  │
└─────────────────────┘

Vias on a regular rectangular grid.

Best for: General ground stitching
""",
            "Staggered": """
┌─────────────────────┐
│  ●   ●   ●   ●   ●  │
│    ●   ●   ●   ●    │
│  ●   ●   ●   ●   ●  │
│    ●   ●   ●   ●    │
└─────────────────────┘

Every other row offset by half
(like bricks or honeycomb).

Best for: ~15% denser packing
""",
            "Concentric": """
┌─────────────────────┐
│  ●   ●   ●   ●   ●  │
│  ●               ●  │
│  ●       ●       ●  │
│  ●               ●  │
│  ●   ●   ●   ●   ●  │
└─────────────────────┘

Vias follow the zone outline
inward in concentric rings.

Best for: Thermal, EMI shielding
""",
            "Outline": """
┌─────────────────────┐
│  ●   ●   ●   ●   ●  │
│  ●   ┌───┐       ●  │
│  ●   ● ● ●       ●  │
│  ●   └───┘       ●  │
│  ●   ●   ●   ●   ●  │
└─────────────────────┘

Vias only along zone edges,
including around internal holes.

Best for: Via fencing, shielding
""",
            "Outline (No Holes)": """
┌─────────────────────┐
│  ●   ●   ●   ●   ●  │
│  ●   ┌───┐       ●  │
│  ●   │   │       ●  │
│  ●   └───┘       ●  │
│  ●   ●   ●   ●   ●  │
└─────────────────────┘

Vias only along outer zone edge,
ignoring internal cutouts.

Best for: Simple perimeter fence
"""
        }

        pattern = self.m_cbFillType.GetStringSelection()
        diagram = pattern_diagrams.get(pattern, "No diagram available")

        dlg = wx.Dialog(self, title=f"Pattern: {pattern}",
                       style=wx.DEFAULT_DIALOG_STYLE)
        sizer = wx.BoxSizer(wx.VERTICAL)

        text = wx.TextCtrl(dlg, value=diagram.strip(),
                          style=wx.TE_MULTILINE | wx.TE_READONLY,
                          size=(300, 280))
        text.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(text, 1, wx.ALL | wx.EXPAND, 10)

        btn = wx.Button(dlg, wx.ID_OK, "OK")
        sizer.Add(btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        dlg.SetSizer(sizer)
        dlg.Fit()
        dlg.Centre()
        dlg.ShowModal()
        dlg.Destroy()

    # Virtual event handler - override in derived class
    def onDeleteClick(self, event):
        event.Skip()

    # ---- Settings persistence ----
    @staticmethod
    def GetConfigPath():
        """Get path to config file"""
        return os.path.join(os.path.dirname(__file__), "via_stitching_settings.json")

    def SaveSettings(self):
        """Save current settings to config file"""
        settings = {
            "unit": self.current_unit,
            "size": self.m_SizeMM.GetValue(),
            "drill": self.m_DrillMM.GetValue(),
            "clearance": self.m_ClearanceMM.GetValue(),
            "hole_clearance": self.m_HoleClearanceMM.GetValue(),
            "step": self.m_StepMM.GetValue(),
            "pattern": self.m_cbFillType.GetStringSelection(),
            "nudge": self.m_Nudge.IsChecked(),
            "random": self.m_Random.IsChecked(),
            "only_selected": self.m_only_selected.IsChecked(),
            "ignored_layers": self.GetIgnoredLayers(),
            "same_net_tracks": self.m_sameNetTracks.IsChecked(),
        }
        try:
            with open(self.GetConfigPath(), 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass  # Silently fail if can't save

    def LoadSettings(self):
        """Load settings from config file"""
        try:
            with open(self.GetConfigPath(), 'r') as f:
                settings = json.load(f)

            # Apply unit first
            if "unit" in settings:
                unit = settings["unit"]
                if unit in ["mm", "mil"]:
                    idx = self.m_cbUnit.FindString(unit)
                    if idx != wx.NOT_FOUND:
                        self.m_cbUnit.SetSelection(idx)
                        self.current_unit = unit
                        # Update labels
                        if unit == "mil":
                            self.m_staticText3.SetLabel(u"Via copper size (mil)")
                            self.m_staticText9.SetLabel(u"Via drill size (mil)")
                            self.m_staticText5.SetLabel(u"Via clearance (mil)")
                            self.m_staticTextHoleClearance.SetLabel(u"Hole clearance (mil)")
                            self.m_staticText2.SetLabel(u"Via spacing (mil)")

            # Apply values
            if "size" in settings:
                self.m_SizeMM.SetValue(settings["size"])
            if "drill" in settings:
                self.m_DrillMM.SetValue(settings["drill"])
            if "clearance" in settings:
                self.m_ClearanceMM.SetValue(settings["clearance"])
            if "hole_clearance" in settings:
                self.m_HoleClearanceMM.SetValue(settings["hole_clearance"])
            if "step" in settings:
                self.m_StepMM.SetValue(settings["step"])

            # Apply pattern (with backward compatibility for "Star" -> "Staggered")
            if "pattern" in settings:
                pattern = settings["pattern"]
                if pattern == "Star":  # Backward compatibility
                    pattern = "Staggered"
                idx = self.m_cbFillType.FindString(pattern)
                if idx != wx.NOT_FOUND:
                    self.m_cbFillType.SetSelection(idx)
                    self._UpdatePatternTooltip()

            # Apply checkboxes
            if "nudge" in settings:
                self.m_Nudge.SetValue(settings["nudge"])
            if "random" in settings:
                self.m_Random.SetValue(settings["random"])
            if "only_selected" in settings:
                self.m_only_selected.SetValue(settings["only_selected"])
            if "ignored_layers" in settings:
                self.SetIgnoredLayers(settings["ignored_layers"])
            if "same_net_tracks" in settings:
                self.m_sameNetTracks.SetValue(settings["same_net_tracks"])

            self.UpdateHelpText()

        except FileNotFoundError:
            pass  # No config file yet
        except Exception:
            pass  # Silently fail if can't load
