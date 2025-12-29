#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  FillAreaDialogEnhanced.py
#  Enhanced dialog with mil/mm unit selector, nudge option, and group management
#
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com> (original FillAreaDialog.py)
#  Copyright 2025 Geoff Wall / Ceres Imaging (enhancements)
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
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

import wx
import wx.xrc


class FillAreaDialogEnhanced(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY,
                           title=u"Enhanced Via Stitching",
                           pos=wx.DefaultPosition,
                           size=wx.Size(450, 880),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        # Main sizer
        bSizer3 = wx.BoxSizer(wx.VERTICAL)

        # Title
        title = wx.StaticText(self, wx.ID_ANY, u"Enhanced Via Stitching with Nudge Search")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        bSizer3.Add(title, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        # Grid sizer for parameters
        fgSizer1 = wx.FlexGridSizer(0, 3, 0, 0)
        fgSizer1.AddGrowableCol(1)
        fgSizer1.SetFlexibleDirection(wx.BOTH)
        fgSizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        # ---- Unit selector ----
        self.m_staticTextUnit = wx.StaticText(self, wx.ID_ANY, u"Units")
        self.m_staticTextUnit.SetToolTip(u"Choose your preferred unit system")
        fgSizer1.Add(self.m_staticTextUnit, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_cbUnit = wx.ComboBox(self, wx.ID_ANY, u"mil",
                                     choices=[u"mil", u"mm"],
                                     style=wx.CB_READONLY)
        self.m_cbUnit.SetSelection(0)  # Default to mil
        self.m_cbUnit.SetToolTip(u"mil = thousandths of an inch (1 mil = 0.0254 mm)\n"
                                  u"mm = millimeters\n\n"
                                  u"Switching units will convert all values automatically.")
        fgSizer1.Add(self.m_cbUnit, 1, wx.ALL | wx.EXPAND, 5)

        fgSizer1.Add((0, 0), 1, wx.EXPAND, 5)  # Empty cell

        # ---- Via copper size ----
        self.m_labelSize = wx.StaticText(self, wx.ID_ANY, u"Via copper size (mil)")
        self.m_labelSize.SetToolTip(u"Outer diameter of the via's copper pad")
        fgSizer1.Add(self.m_labelSize, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Size = wx.TextCtrl(self, wx.ID_ANY, u"24")
        self.m_Size.SetToolTip(u"The outer diameter of the copper annular ring.\n\n"
                                u"HOW TO CHOOSE:\n"
                                u"  1. Check your existing vias in the design\n"
                                u"     (click a via, look at Properties)\n"
                                u"  2. Use the same size for consistency\n"
                                u"  3. Or check your fab's capabilities\n\n"
                                u"Typical values:\n"
                                u"  20-24 mil (0.5-0.6 mm) - Standard, most fabs\n"
                                u"  16-18 mil (0.4-0.45 mm) - Small/dense boards\n"
                                u"  28-32 mil (0.7-0.8 mm) - High-current/thick boards\n\n"
                                u"RULE OF THUMB: Match your board's existing vias.\n"
                                u"If unsure, 24 mil (0.6mm) works for most designs.")
        fgSizer1.Add(self.m_Size, 1, wx.ALL | wx.EXPAND, 5)

        self.m_sizeHelp = wx.StaticText(self, wx.ID_ANY, u"(0.6096 mm)")
        self.m_sizeHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_sizeHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Via drill size ----
        self.m_labelDrill = wx.StaticText(self, wx.ID_ANY, u"Via drill size (mil)")
        self.m_labelDrill.SetToolTip(u"Diameter of the drilled hole")
        fgSizer1.Add(self.m_labelDrill, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Drill = wx.TextCtrl(self, wx.ID_ANY, u"13.8")
        self.m_Drill.SetToolTip(u"The FINISHED plated hole diameter (after plating).\n\n"
                                 u"HOW TO CHOOSE:\n"
                                 u"  1. Match your existing vias (check via Properties)\n"
                                 u"  2. Ensure annular ring is adequate:\n"
                                 u"     Annular ring = (copper size - drill) / 2\n"
                                 u"     Most fabs need at least 5 mil annular ring\n\n"
                                 u"EXAMPLE: 24 mil copper, 14 mil drill\n"
                                 u"  Annular ring = (24-14)/2 = 5 mil  [OK]\n\n"
                                 u"Typical values:\n"
                                 u"  10-14 mil (0.25-0.35 mm) - Standard\n"
                                 u"  8 mil (0.2 mm) - Small (check fab, may cost extra)\n\n"
                                 u"RULE OF THUMB: Drill should be roughly half of\n"
                                 u"copper size, giving ~5-6 mil annular ring.")
        fgSizer1.Add(self.m_Drill, 1, wx.ALL | wx.EXPAND, 5)

        self.m_drillHelp = wx.StaticText(self, wx.ID_ANY, u"(0.3505 mm)")
        self.m_drillHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_drillHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Via clearance ----
        self.m_labelClearance = wx.StaticText(self, wx.ID_ANY, u"Via clearance (mil)")
        self.m_labelClearance.SetToolTip(u"Minimum gap from via to other copper")
        fgSizer1.Add(self.m_labelClearance, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Clearance = wx.TextCtrl(self, wx.ID_ANY, u"5")
        self.m_Clearance.SetToolTip(u"Minimum COPPER-to-COPPER clearance (edge to edge).\n\n"
                                     u"HOW TO CHOOSE:\n"
                                     u"  1. Check your fab's minimum clearance spec\n"
                                     u"  2. Check your board's design rules in KiCad\n"
                                     u"     (File > Board Setup > Design Rules > Clearance)\n"
                                     u"  3. Use the larger of the two values\n\n"
                                     u"Typical fab capabilities:\n"
                                     u"  4-5 mil - Budget fabs (JLCPCB, PCBWay)\n"
                                     u"  5-6 mil - Standard fabs (safe choice)\n"
                                     u"  8 mil   - Conservative/older fabs\n\n"
                                     u"RULE OF THUMB: Use 5-6 mil unless your fab\n"
                                     u"or design rules require something different.\n"
                                     u"When in doubt, go larger (safer).")
        fgSizer1.Add(self.m_Clearance, 1, wx.ALL | wx.EXPAND, 5)

        self.m_clearanceHelp = wx.StaticText(self, wx.ID_ANY, u"(0.1016 mm)")
        self.m_clearanceHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_clearanceHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Hole-to-hole clearance ----
        self.m_labelHoleClearance = wx.StaticText(self, wx.ID_ANY, u"Hole clearance (mil)")
        self.m_labelHoleClearance.SetToolTip(u"Minimum hole-to-hole spacing (edge to edge)")
        fgSizer1.Add(self.m_labelHoleClearance, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_HoleClearance = wx.TextCtrl(self, wx.ID_ANY, u"8")
        self.m_HoleClearance.SetToolTip(u"Minimum HOLE-to-HOLE clearance (edge to edge).\n\n"
                                         u"This is separate from copper clearance!\n"
                                         u"Drilled holes need physical spacing for the\n"
                                         u"drill bits and board structural integrity.\n\n"
                                         u"HOW TO CHOOSE:\n"
                                         u"  1. Check your fab's hole-to-hole spec\n"
                                         u"  2. Usually listed as 'drill to drill' spacing\n\n"
                                         u"Typical fab capabilities:\n"
                                         u"  6-8 mil - Budget fabs (JLCPCB, PCBWay)\n"
                                         u"  8-10 mil - Standard fabs (safe choice)\n"
                                         u"  10-12 mil - Conservative\n\n"
                                         u"WHY IT MATTERS:\n"
                                         u"  - Too close = drill breakage risk\n"
                                         u"  - Too close = weak board between holes\n"
                                         u"  - Affects via-to-via and via-to-PTH spacing\n\n"
                                         u"RULE OF THUMB: Use 8 mil for most fabs.\n"
                                         u"This is often more restrictive than copper clearance.")
        fgSizer1.Add(self.m_HoleClearance, 1, wx.ALL | wx.EXPAND, 5)

        self.m_holeClearanceHelp = wx.StaticText(self, wx.ID_ANY, u"(0.2032 mm)")
        self.m_holeClearanceHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_holeClearanceHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        # ---- Via grid ----
        self.m_labelStep = wx.StaticText(self, wx.ID_ANY, u"Via grid spacing (mil)")
        self.m_labelStep.SetToolTip(u"Distance between via centers")
        fgSizer1.Add(self.m_labelStep, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Step = wx.TextCtrl(self, wx.ID_ANY, u"100")
        self.m_Step.SetToolTip(u"Distance between via centers in the grid pattern.\n\n"
                                u"HOW TO CHOOSE:\n"
                                u"  1. Consider your highest signal frequency\n"
                                u"  2. For EMI shielding: spacing < wavelength/20\n"
                                u"  3. For general use: 100 mil is fine\n\n"
                                u"FREQUENCY GUIDE (wavelength/20 rule):\n"
                                u"  < 100 MHz:  100 mil is plenty\n"
                                u"  100-500 MHz: 75-100 mil\n"
                                u"  500 MHz-1 GHz: 50-75 mil\n"
                                u"  > 1 GHz: 25-50 mil\n\n"
                                u"TRADE-OFFS:\n"
                                u"  Smaller spacing = more vias = better shielding\n"
                                u"  but more drill time and diminishing returns\n"
                                u"  below ~50 mil for most applications.\n\n"
                                u"RULE OF THUMB: Start with 100 mil for general\n"
                                u"designs. Use 50 mil for RF or high-speed sections.")
        fgSizer1.Add(self.m_Step, 1, wx.ALL | wx.EXPAND, 5)

        self.m_stepHelp = wx.StaticText(self, wx.ID_ANY, u"(2.54 mm)")
        self.m_stepHelp.SetForegroundColour(wx.Colour(128, 128, 128))
        fgSizer1.Add(self.m_stepHelp, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer3.Add(fgSizer1, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Separator ----
        bSizer3.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 5)

        # ---- Net name ----
        netSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.m_staticText6 = wx.StaticText(self, wx.ID_ANY, u"Net name:")
        netSizer.Add(self.m_staticText6, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_cbNet = wx.ComboBox(self, wx.ID_ANY, u"GND",
                                    choices=[],
                                    style=wx.CB_READONLY)
        net_tip = (u"Select which net to fill with stitching vias.\n\n"
                   u"Usually GND for ground plane stitching.\n"
                   u"Only nets that have copper zones are listed.\n\n"
                   u"Vias will be placed inside copper pour zones\n"
                   u"of this net, connecting them across all layers.")
        self.m_staticText6.SetToolTip(net_tip)
        self.m_cbNet.SetToolTip(net_tip)
        netSizer.Add(self.m_cbNet, 1, wx.ALL | wx.EXPAND, 5)
        bSizer3.Add(netSizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Separator ----
        bSizer3.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 5)

        # ---- Checkboxes section ----
        checkSizer = wx.FlexGridSizer(0, 2, 0, 0)
        checkSizer.AddGrowableCol(0)

        # Staggered grid (brick/hex pattern)
        self.m_staticStaggered = wx.StaticText(self, wx.ID_ANY, u"Staggered grid pattern")
        checkSizer.Add(self.m_staticStaggered, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Staggered = wx.CheckBox(self, wx.ID_ANY)
        self.m_Staggered.SetValue(True)  # Default ON
        staggered_tip = (u"RECOMMENDED: Keep this ON for denser packing\n\n"
                         u"When ON: Alternating rows are offset by half the\n"
                         u"grid spacing, creating a brick/hexagonal pattern:\n\n"
                         u"  O   O   O   O        (row 0)\n"
                         u"    O   O   O   O      (row 1, offset)\n"
                         u"  O   O   O   O        (row 2)\n\n"
                         u"This packs ~15% more vias into the same area\n"
                         u"while maintaining the same minimum spacing.\n\n"
                         u"When OFF: Simple rectangular grid pattern.")
        self.m_staticStaggered.SetToolTip(staggered_tip)
        self.m_Staggered.SetToolTip(staggered_tip)
        checkSizer.Add(self.m_Staggered, 0, wx.ALL, 5)

        # Nudge search
        self.m_staticNudge = wx.StaticText(self, wx.ID_ANY, u"Enable nudge search")
        checkSizer.Add(self.m_staticNudge, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Nudge = wx.CheckBox(self, wx.ID_ANY)
        self.m_Nudge.SetValue(True)  # Default ON
        nudge_tip = (u"RECOMMENDED: Keep this ON\n\n"
                     u"When a grid position is blocked by a pad or track,\n"
                     u"the algorithm searches in a spiral pattern within\n"
                     u"the grid cell to find a nearby valid position.\n\n"
                     u"This significantly improves via density in crowded areas.\n"
                     u"The final report shows how many extra vias were placed\n"
                     u"thanks to nudge search.")
        self.m_staticNudge.SetToolTip(nudge_tip)
        self.m_Nudge.SetToolTip(nudge_tip)
        checkSizer.Add(self.m_Nudge, 0, wx.ALL, 5)

        # Ignore areas on other layers
        self.m_staticText71 = wx.StaticText(self, wx.ID_ANY, u"Ignore internal power planes")
        checkSizer.Add(self.m_staticText71, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_viaThroughAreas = wx.CheckBox(self, wx.ID_ANY)
        self.m_viaThroughAreas.SetValue(True)  # Default ON for multi-layer boards
        powerplane_tip = (u"RECOMMENDED for multi-layer boards: Keep this ON\n\n"
                          u"When ON: Ignores copper pours on POWER PLANE layers\n"
                          u"(layers marked as 'power' type like GND2, PWR5, etc.)\n"
                          u"Vias will pass through these and KiCad auto-creates clearance.\n\n"
                          u"ALWAYS checks copper pours on SIGNAL layers\n"
                          u"(F.Cu, B.Cu, and signal routing layers) regardless.\n\n"
                          u"When OFF: Checks ALL copper pours on ALL layers.\n"
                          u"Use this for 2-layer boards or special cases.")
        self.m_staticText71.SetToolTip(powerplane_tip)
        self.m_viaThroughAreas.SetToolTip(powerplane_tip)
        checkSizer.Add(self.m_viaThroughAreas, 0, wx.ALL, 5)

        # Only selected zone
        self.m_staticText81 = wx.StaticText(self, wx.ID_ANY, u"Only under selected Zone")
        checkSizer.Add(self.m_staticText81, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_only_selected = wx.CheckBox(self, wx.ID_ANY)
        selected_tip = (u"When ON: Only places vias in zones you've selected\n"
                        u"before running the plugin.\n\n"
                        u"Useful for:\n"
                        u"  - Testing on a small area first\n"
                        u"  - Different via density in different regions\n"
                        u"  - Stitching only specific zones\n\n"
                        u"When OFF: Places vias in ALL zones of the selected net.")
        self.m_staticText81.SetToolTip(selected_tip)
        self.m_only_selected.SetToolTip(selected_tip)
        checkSizer.Add(self.m_only_selected, 0, wx.ALL, 5)

        # Same net tracks
        self.m_staticText72 = wx.StaticText(self, wx.ID_ANY, u"Also on tracks with same net")
        checkSizer.Add(self.m_staticText72, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_sameNetTracks = wx.CheckBox(self, wx.ID_ANY)
        samenet_tip = (u"When ON: Allows placing vias directly on top of\n"
                       u"tracks that are the same net (e.g., GND tracks).\n\n"
                       u"When OFF: Keeps clearance from ALL tracks,\n"
                       u"even same-net tracks.\n\n"
                       u"Usually keep OFF unless you specifically want\n"
                       u"via-in-track connections.")
        self.m_staticText72.SetToolTip(samenet_tip)
        self.m_sameNetTracks.SetToolTip(samenet_tip)
        checkSizer.Add(self.m_sameNetTracks, 0, wx.ALL, 5)

        # Random offset
        self.m_staticText8 = wx.StaticText(self, wx.ID_ANY, u"Random offset")
        checkSizer.Add(self.m_staticText8, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_Random = wx.CheckBox(self, wx.ID_ANY)
        random_tip = (u"When ON: Adds small random offset to each via position.\n\n"
                      u"Makes the pattern look less mechanical/grid-like.\n"
                      u"Purely cosmetic - no electrical benefit.\n\n"
                      u"Usually keep OFF for clean, predictable results.")
        self.m_staticText8.SetToolTip(random_tip)
        self.m_Random.SetToolTip(random_tip)
        checkSizer.Add(self.m_Random, 0, wx.ALL, 5)

        bSizer3.Add(checkSizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Separator ----
        bSizer3.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 5)

        # ---- Delete existing vias section ----
        deleteBox = wx.StaticBox(self, wx.ID_ANY, u"Manage Existing Via Stitching Groups")
        deleteSizer = wx.StaticBoxSizer(deleteBox, wx.HORIZONTAL)

        self.m_groupList = wx.ComboBox(self, wx.ID_ANY, u"",
                                        choices=[],
                                        style=wx.CB_READONLY)
        self.m_groupList.SetToolTip(u"Select a via stitching group to delete.\n\n"
                                     u"Each time you run via stitching, a new\n"
                                     u"numbered group is created. You can delete\n"
                                     u"individual runs without affecting others.")
        deleteSizer.Add(self.m_groupList, 1, wx.ALL | wx.EXPAND, 5)

        self.m_deleteBtn = wx.Button(self, wx.ID_ANY, u"Delete Group")
        self.m_deleteBtn.SetToolTip(u"Delete all vias in the selected group.\n"
                                     u"This cannot be undone (use Ctrl+Z to undo).")
        deleteSizer.Add(self.m_deleteBtn, 0, wx.ALL, 5)

        self.m_refreshBtn = wx.Button(self, wx.ID_ANY, u"Refresh")
        self.m_refreshBtn.SetToolTip(u"Refresh the list of via stitching groups")
        deleteSizer.Add(self.m_refreshBtn, 0, wx.ALL, 5)

        bSizer3.Add(deleteSizer, 0, wx.EXPAND | wx.ALL, 5)

        # ---- Buttons ----
        bSizer1 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer1.Add((0, 0), 1, wx.EXPAND, 5)  # Spacer

        self.m_button1 = wx.Button(self, wx.ID_OK, u"Run")
        self.m_button1.SetDefault()
        bSizer1.Add(self.m_button1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_button2 = wx.Button(self, wx.ID_CANCEL, u"Cancel")
        bSizer1.Add(self.m_button2, 0, wx.ALL, 5)

        bSizer3.Add(bSizer1, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(bSizer3)
        self.Layout()
        self.Centre(wx.BOTH)

        # Connect Events
        self.m_cbUnit.Bind(wx.EVT_COMBOBOX, self.onUnitChange)
        self.m_Size.Bind(wx.EVT_TEXT, self.onValueChange)
        self.m_Drill.Bind(wx.EVT_TEXT, self.onValueChange)
        self.m_Clearance.Bind(wx.EVT_TEXT, self.onValueChange)
        self.m_HoleClearance.Bind(wx.EVT_TEXT, self.onValueChange)
        self.m_Step.Bind(wx.EVT_TEXT, self.onValueChange)
        self.m_deleteBtn.Bind(wx.EVT_BUTTON, self.onDeleteGroup)
        self.m_refreshBtn.Bind(wx.EVT_BUTTON, self.onRefreshGroups)

        # Store reference to board for group management
        self.pcb = None

    def __del__(self):
        pass

    def onUnitChange(self, event):
        """Update labels and convert values when unit changes"""
        unit = self.m_cbUnit.GetStringSelection()

        # Update labels
        self.m_labelSize.SetLabel(f"Via copper size ({unit})")
        self.m_labelDrill.SetLabel(f"Via drill size ({unit})")
        self.m_labelClearance.SetLabel(f"Via clearance ({unit})")
        self.m_labelHoleClearance.SetLabel(f"Hole clearance ({unit})")
        self.m_labelStep.SetLabel(f"Via grid spacing ({unit})")

        # Convert current values
        try:
            if unit == "mm":
                # Convert mil to mm
                factor = 0.0254
                self.m_Size.SetValue(f"{float(self.m_Size.GetValue()) * factor:.4f}")
                self.m_Drill.SetValue(f"{float(self.m_Drill.GetValue()) * factor:.4f}")
                self.m_Clearance.SetValue(f"{float(self.m_Clearance.GetValue()) * factor:.4f}")
                self.m_HoleClearance.SetValue(f"{float(self.m_HoleClearance.GetValue()) * factor:.4f}")
                self.m_Step.SetValue(f"{float(self.m_Step.GetValue()) * factor:.4f}")
            else:
                # Convert mm to mil
                factor = 1 / 0.0254
                self.m_Size.SetValue(f"{float(self.m_Size.GetValue()) * factor:.2f}")
                self.m_Drill.SetValue(f"{float(self.m_Drill.GetValue()) * factor:.2f}")
                self.m_Clearance.SetValue(f"{float(self.m_Clearance.GetValue()) * factor:.2f}")
                self.m_HoleClearance.SetValue(f"{float(self.m_HoleClearance.GetValue()) * factor:.2f}")
                self.m_Step.SetValue(f"{float(self.m_Step.GetValue()) * factor:.2f}")
        except ValueError:
            pass

        self.updateHelpText()
        self.Layout()

    def onValueChange(self, event):
        """Update help text showing conversion"""
        self.updateHelpText()

    def updateHelpTextSingle(self, textCtrl, helpLabel, value_str, unit):
        """Update a single help label with converted value"""
        try:
            value = float(value_str.replace(',', '.'))
            if unit == "mil":
                helpLabel.SetLabel(f"({value * 0.0254:.4f} mm)")
            else:
                helpLabel.SetLabel(f"({value / 0.0254:.2f} mil)")
        except ValueError:
            pass

    def updateHelpText(self):
        """Show the alternate unit conversion"""
        unit = self.m_cbUnit.GetStringSelection()

        try:
            size = float(self.m_Size.GetValue().replace(',', '.'))
            drill = float(self.m_Drill.GetValue().replace(',', '.'))
            clearance = float(self.m_Clearance.GetValue().replace(',', '.'))
            hole_clearance = float(self.m_HoleClearance.GetValue().replace(',', '.'))
            step = float(self.m_Step.GetValue().replace(',', '.'))

            if unit == "mil":
                # Show mm equivalent
                self.m_sizeHelp.SetLabel(f"({size * 0.0254:.4f} mm)")
                self.m_drillHelp.SetLabel(f"({drill * 0.0254:.4f} mm)")
                self.m_clearanceHelp.SetLabel(f"({clearance * 0.0254:.4f} mm)")
                self.m_holeClearanceHelp.SetLabel(f"({hole_clearance * 0.0254:.4f} mm)")
                self.m_stepHelp.SetLabel(f"({step * 0.0254:.4f} mm)")
            else:
                # Show mil equivalent
                self.m_sizeHelp.SetLabel(f"({size / 0.0254:.2f} mil)")
                self.m_drillHelp.SetLabel(f"({drill / 0.0254:.2f} mil)")
                self.m_clearanceHelp.SetLabel(f"({clearance / 0.0254:.2f} mil)")
                self.m_holeClearanceHelp.SetLabel(f"({hole_clearance / 0.0254:.2f} mil)")
                self.m_stepHelp.SetLabel(f"({step / 0.0254:.2f} mil)")
        except ValueError:
            pass

    def GetUnit(self):
        return self.m_cbUnit.GetStringSelection()

    def GetSizeValue(self):
        """Return size in mm regardless of display unit"""
        val = float(self.m_Size.GetValue().replace(',', '.'))
        if self.GetUnit() == "mil":
            return val * 0.0254
        return val

    def GetDrillValue(self):
        """Return drill in mm regardless of display unit"""
        val = float(self.m_Drill.GetValue().replace(',', '.'))
        if self.GetUnit() == "mil":
            return val * 0.0254
        return val

    def GetClearanceValue(self):
        """Return clearance in mm regardless of display unit"""
        val = float(self.m_Clearance.GetValue().replace(',', '.'))
        if self.GetUnit() == "mil":
            return val * 0.0254
        return val

    def GetHoleClearanceValue(self):
        """Return hole clearance in mm regardless of display unit"""
        val = float(self.m_HoleClearance.GetValue().replace(',', '.'))
        if self.GetUnit() == "mil":
            return val * 0.0254
        return val

    def GetStepValue(self):
        """Return step in mm regardless of display unit"""
        val = float(self.m_Step.GetValue().replace(',', '.'))
        if self.GetUnit() == "mil":
            return val * 0.0254
        return val

    def SetSizeFromMM(self, mm):
        """Set size from mm value, converting to current unit"""
        if self.GetUnit() == "mil":
            self.m_Size.SetValue(f"{mm / 0.0254:.2f}")
        else:
            self.m_Size.SetValue(f"{mm:.4f}")
        self.updateHelpText()

    def SetDrillFromMM(self, mm):
        if self.GetUnit() == "mil":
            self.m_Drill.SetValue(f"{mm / 0.0254:.2f}")
        else:
            self.m_Drill.SetValue(f"{mm:.4f}")
        self.updateHelpText()

    def SetClearanceFromMM(self, mm):
        if self.GetUnit() == "mil":
            self.m_Clearance.SetValue(f"{mm / 0.0254:.2f}")
        else:
            self.m_Clearance.SetValue(f"{mm:.4f}")
        self.updateHelpText()

    def SetHoleClearanceFromMM(self, mm):
        if self.GetUnit() == "mil":
            self.m_HoleClearance.SetValue(f"{mm / 0.0254:.2f}")
        else:
            self.m_HoleClearance.SetValue(f"{mm:.4f}")
        self.updateHelpText()

    def SetStepFromMM(self, mm):
        if self.GetUnit() == "mil":
            self.m_Step.SetValue(f"{mm / 0.0254:.2f}")
        else:
            self.m_Step.SetValue(f"{mm:.4f}")
        self.updateHelpText()

    def SetBoard(self, pcb):
        """Set board reference for group management"""
        self.pcb = pcb
        self.refreshGroupList()

    def refreshGroupList(self):
        """Populate the group list with existing ViaStitching groups"""
        self.m_groupList.Clear()
        if self.pcb is None:
            return

        groups = []
        for group in self.pcb.Groups():
            name = group.GetName()
            if name.startswith("ViaStitching "):
                # Count items in group
                count = len(list(group.GetItems()))
                groups.append((name, count))

        if groups:
            groups.sort()  # Sort alphabetically
            for name, count in groups:
                self.m_groupList.Append(f"{name} ({count} vias)")
            self.m_groupList.SetSelection(0)
            self.m_deleteBtn.Enable(True)
        else:
            self.m_groupList.Append("(no via stitching groups found)")
            self.m_groupList.SetSelection(0)
            self.m_deleteBtn.Enable(False)

    def onRefreshGroups(self, event):
        """Refresh button clicked"""
        self.refreshGroupList()

    def onDeleteGroup(self, event):
        """Delete the selected via stitching group"""
        if self.pcb is None:
            return

        selection = self.m_groupList.GetStringSelection()
        if not selection or selection.startswith("(no via"):
            return

        # Extract group name (remove the " (X vias)" suffix)
        group_name = selection.rsplit(" (", 1)[0]

        # Confirm deletion
        result = wx.MessageBox(
            f"Delete all vias in group '{group_name}'?\n\n"
            f"This will remove all vias created in this run.\n"
            f"You can undo with Ctrl+Z.",
            "Confirm Delete",
            wx.YES_NO | wx.ICON_WARNING
        )

        if result != wx.YES:
            return

        # Find and delete the group
        for group in self.pcb.Groups():
            if group.GetName() == group_name:
                # Get all items in the group
                items = list(group.GetItems())
                via_count = 0

                # Remove each via
                for item in items:
                    if item.GetClass() == "PCB_VIA":
                        self.pcb.Remove(item)
                        via_count += 1

                # Remove the group itself
                self.pcb.Remove(group)

                wx.MessageBox(
                    f"Deleted {via_count} vias from group '{group_name}'.\n\n"
                    f"Remember to refill zones (press 'B').",
                    "Deletion Complete",
                    wx.OK | wx.ICON_INFORMATION
                )
                break

        # Refresh the list
        self.refreshGroupList()
