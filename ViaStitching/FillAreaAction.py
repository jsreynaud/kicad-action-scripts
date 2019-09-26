#
#  FillAreaAction.py
#
#  Copyright 2017 JS Reynaud <js.reynaud@gmail.com>
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

def PopulateNets(anet,dlg):
    nets = pcbnew.GetBoard().GetNetsByName()
    for netname, net in nets.items():
        netname = net.GetNetname()
        if netname != None and netname != "":
            dlg.m_cbNet.Append(netname)
    if anet != None:
        index = dlg.m_cbNet.FindString(anet)
        dlg.m_cbNet.Select(index)                   
#
class FillAreaDialogEx(FillAreaDialog.FillAreaDialog):

    def onDeleteClick(self, event):
        return self.EndModal(wx.ID_DELETE)


class FillAreaAction(pcbnew.ActionPlugin):

    def defaults(self):
        self.name = "Via Stitching Generator"
        self.category = "Modify PCB"
        self.description = "Via Stitching for PCB Zone"
        self.icon_file_name = os.path.join(os.path.dirname(__file__), "./stitching-vias.png")
            
    def Run(self):
        a = FillAreaDialogEx(None)
        a.m_SizeMM.SetValue("0.8")
        a.m_StepMM.SetValue("2.54")
        a.m_DrillMM.SetValue("0.3")
        #a.m_Netname.SetValue("GND")
        a.m_ClearanceMM.SetValue("0.2")
        a.m_Star.SetValue(True)
        self.board = pcbnew.GetBoard()
        PopulateNets("GND",a)
        modal_result = a.ShowModal()
        if modal_result == wx.ID_OK:
            wx.LogMessage('Via Stitching: Version 1.3')
            if 1: #try:
                fill = FillArea.FillArea()
                fill.SetStepMM(float(a.m_StepMM.GetValue()))
                fill.SetSizeMM(float(a.m_SizeMM.GetValue()))
                fill.SetDrillMM(float(a.m_DrillMM.GetValue()))
                fill.SetClearanceMM(float(a.m_ClearanceMM.GetValue()))
                #fill.SetNetname(a.m_Netname.GetValue())
                netname = a.m_cbNet.GetStringSelection()
                fill.SetNetname(netname)
                if a.m_Debug.IsChecked():
                    fill.SetDebug()
                if a.m_Random.IsChecked():
                    fill.SetRandom()
                if a.m_Star.IsChecked():
                    fill.SetStar()
                if a.m_only_selected.IsChecked():
                    fill.OnlyOnSelectedArea()
                fill.Run()
            else: #except Exception:
                wx.MessageDialog(None, "Invalid parameter")
        elif modal_result == wx.ID_DELETE:
            if 1: #try:
                fill = FillArea.FillArea()
                fill.SetNetname(a.m_cbNet.GetStringSelection()) #a.m_Netname.GetValue())
                if a.m_Debug.IsChecked():
                    fill.SetDebug()
                fill.DeleteVias()
                fill.Run()
            else: #except Exception:
                wx.MessageDialog(None, "Invalid parameter for delete")
        else:
            print("Cancel")
        a.Destroy()


FillAreaAction().register()
