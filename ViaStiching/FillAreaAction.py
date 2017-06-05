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
import pcbnew
import FillArea
import wx
import FillAreaDialog


class FillAreaAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Via stiching WX"
        self.category = "Undefined"
        self.description = ""

    def Run(self):
        a = FillAreaDialog.FillAreaDialog(None)
        a.m_SizeMM.SetValue("0.35")
        a.m_StepMM.SetValue("2.54")
        a.m_DrillMM.SetValue("0.3")
        a.m_Netname.SetValue("auto")
        a.m_ClearanceMM.SetValue("0.2")

        if a.ShowModal() == wx.ID_OK:
            fill = FillArea.FillArea()
            try:
                fill.SetStepMM(float(a.m_StepMM.GetValue()))
                fill.SetSizeMM(float(a.m_SizeMM.GetValue()))
                fill.SetDrillMM(float(a.m_DrillMM.GetValue()))
                fill.SetClearanceMM(float(a.m_ClearanceMM.GetValue()))
                if a.m_Netname.GetValue() != "auto":
                    fill.SetNetname(a.m_Netname.GetValue())
                if a.m_Debug.IsChecked():
                    fill.SetDebug()
                if a.m_Random.IsChecked():
                    fill.SetRandom()
                if a.m_only_selected.IsChecked():
                    fill.OnlyOnSelectedArea()
                fill.Run()
            except Exception:
                wx.MessageDialog(None,"Invalid parameter")
        else:
            print "Cancel"
        a.Destroy()

FillAreaAction().register()
