#
#  FillAreaAction.py
#  Via stitching action plugin
#
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
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

from __future__ import print_function
import pcbnew
import wx
from . import FillArea
from . import FillAreaDialog
import os


def GetKiCadUnits():
    """Get KiCad's current display units (mm or mil)"""
    try:
        # KiCad 9 uses GetUserUnits() - returns EDA_UNITS enum
        units = pcbnew.GetUserUnits()
        # EDA_UNITS_MILS = 5 in KiCad 9
        if hasattr(pcbnew, 'EDA_UNITS_MILS') and units == pcbnew.EDA_UNITS_MILS:
            return "mil"
        elif hasattr(pcbnew, 'EDA_UNITS_INCHES') and units == pcbnew.EDA_UNITS_INCHES:
            return "mil"  # Treat inches as mil for our purposes
        elif units == 5:  # Fallback: EDA_UNITS_MILS value
            return "mil"
        else:
            return "mm"
    except Exception:
        return "mm"  # Default to mm


def PopulateNets(anet, dlg):
    """Populate net dropdown with zone nets"""
    netnames = list(set([zone.GetNetname() for zone in pcbnew.GetBoard().Zones()]))
    netnames.sort()
    dlg.m_cbNet.Set(netnames)
    if anet is not None:
        index = dlg.m_cbNet.FindString(anet)
        if index != wx.NOT_FOUND:
            dlg.m_cbNet.Select(index)
        elif netnames:
            dlg.m_cbNet.Select(0)


class FillAreaDialogEx(FillAreaDialog.FillAreaDialog):
    """Extended dialog with delete button handling"""

    def onDeleteClick(self, event):
        return self.EndModal(wx.ID_DELETE)


class FillAreaAction(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Via Stitching Generator"
        self.category = "Modify PCB"
        self.description = "Via Stitching for PCB Zone"
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "./stitching-vias.png")
        self.show_toolbar_button = True

    def Run(self):
        # Create dialog
        a = FillAreaDialogEx(None)

        # Get board and design settings
        self.board = pcbnew.GetBoard()
        self.boardDesignSettings = self.board.GetDesignSettings()

        # Pass board reference for group management
        a.SetBoard(self.board)

        # Check if config file exists
        config_exists = os.path.exists(a.GetConfigPath())

        # Set defaults from board design settings (will be overridden by LoadSettings if config exists)
        a.m_SizeMM.SetValue(str(pcbnew.ToMM(self.boardDesignSettings.GetCurrentViaSize())))
        a.m_DrillMM.SetValue(str(pcbnew.ToMM(self.boardDesignSettings.GetCurrentViaDrill())))
        a.m_ClearanceMM.SetValue(str(pcbnew.ToMM(self.boardDesignSettings.GetSmallestClearanceValue())))
        # m_StepMM and m_HoleClearanceMM have defaults set in dialog

        # Load saved settings (overrides board defaults if config exists)
        a.LoadSettings()

        # If no config exists, use KiCad's current units
        if not config_exists:
            kicad_units = GetKiCadUnits()
            if kicad_units == "mil" and a.current_unit == "mm":
                # Convert to mil
                a.m_cbUnit.SetSelection(1)  # Select "mil"
                a.OnUnitChange(None)

        # Update help text to show converted units
        a.UpdateHelpText()

        a.SetMinSize(a.GetSize())

        # Populate nets
        PopulateNets("GND", a)

        # Show dialog
        modal_result = a.ShowModal()

        if modal_result == wx.ID_OK:
            # Save settings for next time
            a.SaveSettings()

            wx.LogMessage('Via Stitching Generator starting...')

            try:
                fill = FillArea.FillArea()

                # Set parameters using helper methods that handle unit conversion
                fill.SetStepMM(a.GetStepValueMM())
                fill.SetSizeMM(a.GetSizeValueMM())
                fill.SetDrillMM(a.GetDrillValueMM())
                fill.SetClearanceMM(a.GetClearanceValueMM())

                # Set hole clearance if the method exists (enhancement)
                if hasattr(fill, 'SetHoleClearanceMM'):
                    fill.SetHoleClearanceMM(a.GetHoleClearanceValueMM())

                # Set net
                netname = a.m_cbNet.GetStringSelection()
                fill.SetNetname(netname)

                # Set fill type/pattern
                fill.SetType(a.m_cbFillType.GetStringSelection())

                # Set options
                fill.SetRandom(a.m_Random.IsChecked())
                fill.SetSameNetTracks(a.m_sameNetTracks.IsChecked())

                if a.m_only_selected.IsChecked():
                    fill.OnlyOnSelectedArea()

                # Set nudge option if method exists (enhancement)
                if hasattr(fill, 'SetNudgeEnabled'):
                    fill.SetNudgeEnabled(a.m_Nudge.IsChecked())

                # Set ignored layers if method exists (enhancement)
                if hasattr(fill, 'SetIgnoredLayers'):
                    fill.SetIgnoredLayers(a.GetIgnoredLayers())

                # Run!
                fill.Run()

                wx.LogMessage('Via Stitching Generator complete')

            except Exception as e:
                wx.LogError(f"Error during via stitching: {str(e)}")
                import traceback
                wx.LogError(traceback.format_exc())

        elif modal_result == wx.ID_DELETE:
            # Delete all vias on net
            try:
                fill = FillArea.FillArea()
                fill.SetNetname(a.m_cbNet.GetStringSelection())
                fill.DeleteVias()
                fill.Run()
            except Exception as e:
                wx.LogError(f"Error deleting vias: {str(e)}")

        else:
            print("Cancelled")

        a.Destroy()


# Register the plugin
FillAreaAction().register()
