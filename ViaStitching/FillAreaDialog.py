# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.10.1-0-g8feb16b)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class FillAreaDialog
###########################################################################

class FillAreaDialog ( wx.Dialog ):

	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Fill Area parameters", pos = wx.DefaultPosition, size = wx.Size( 402,590 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizer3 = wx.BoxSizer( wx.VERTICAL )

		fgSizer1 = wx.FlexGridSizer( 0, 2, 0, 0 )
		fgSizer1.SetFlexibleDirection( wx.BOTH )
		fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_staticText3 = wx.StaticText( self, wx.ID_ANY, u"Via copper size (mm)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText3.Wrap( -1 )

		fgSizer1.Add( self.m_staticText3, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_SizeMM = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_SizeMM.SetMinSize( wx.Size( 1000,-1 ) )

		fgSizer1.Add( self.m_SizeMM, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText9 = wx.StaticText( self, wx.ID_ANY, u"Via drill size (mm)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText9.Wrap( -1 )

		fgSizer1.Add( self.m_staticText9, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_DrillMM = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_DrillMM, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText5 = wx.StaticText( self, wx.ID_ANY, u"Via clearance (mm)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText5.Wrap( -1 )

		fgSizer1.Add( self.m_staticText5, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_ClearanceMM = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_ClearanceMM, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText2 = wx.StaticText( self, wx.ID_ANY, u"Via grid (mm)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText2.Wrap( -1 )

		fgSizer1.Add( self.m_staticText2, 0, wx.ALL, 5 )

		self.m_StepMM = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_StepMM, 1, wx.ALL|wx.EXPAND, 5 )


		fgSizer1.Add( ( 0, 0), 1, wx.EXPAND, 5 )

		self.m_bitmapStitching = wx.StaticBitmap( self, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_bitmapStitching, 0, wx.EXPAND, 5 )

		self.m_staticText6 = wx.StaticText( self, wx.ID_ANY, u"Net name", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText6.Wrap( -1 )

		fgSizer1.Add( self.m_staticText6, 1, wx.ALL|wx.EXPAND, 5 )

		m_cbNetChoices = []
		self.m_cbNet = wx.ComboBox( self, wx.ID_ANY, u"GND", wx.DefaultPosition, wx.DefaultSize, m_cbNetChoices, wx.CB_READONLY )
		fgSizer1.Add( self.m_cbNet, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_staticText42 = wx.StaticText( self, wx.ID_ANY, u"Pattern", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText42.Wrap( -1 )

		fgSizer1.Add( self.m_staticText42, 0, wx.ALL, 5 )

		m_cbFillTypeChoices = [ u"Concentric", u"Outline", u"Outline (No Holes)", u"Rectangular", u"Star" ]
		self.m_cbFillType = wx.ComboBox( self, wx.ID_ANY, u"Rectangular", wx.DefaultPosition, wx.DefaultSize, m_cbFillTypeChoices, wx.CB_READONLY )
		self.m_cbFillType.SetSelection( 3 )
		fgSizer1.Add( self.m_cbFillType, 0, wx.ALL, 5 )

		self.m_staticText8 = wx.StaticText( self, wx.ID_ANY, u"Random it", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText8.Wrap( -1 )

		fgSizer1.Add( self.m_staticText8, 0, wx.ALL, 5 )

		self.m_Random = wx.CheckBox( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_Random, 0, wx.ALL, 5 )

		self.m_staticText81 = wx.StaticText( self, wx.ID_ANY, u"Only under selected Zone", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText81.Wrap( -1 )

		fgSizer1.Add( self.m_staticText81, 0, wx.ALL, 5 )

		self.m_only_selected = wx.CheckBox( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_only_selected, 0, wx.ALL, 5 )

		self.m_staticText71 = wx.StaticText( self, wx.ID_ANY, u"Ignore areas on other layers", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText71.Wrap( -1 )

		fgSizer1.Add( self.m_staticText71, 0, wx.ALL, 5 )

		self.m_viaThroughAreas = wx.CheckBox( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_viaThroughAreas, 0, wx.ALL, 5 )

		self.m_staticText7 = wx.StaticText( self, wx.ID_ANY, u"Debug mode", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText7.Wrap( -1 )

		fgSizer1.Add( self.m_staticText7, 1, wx.ALL|wx.EXPAND, 5 )

		self.m_Debug = wx.CheckBox( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer1.Add( self.m_Debug, 1, wx.ALL|wx.EXPAND, 5 )


		bSizer3.Add( fgSizer1, 1, wx.EXPAND, 5 )

		bSizer1 = wx.BoxSizer( wx.HORIZONTAL )

		self.m_staticText101 = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText101.Wrap( -1 )

		bSizer1.Add( self.m_staticText101, 1, wx.ALL, 5 )

		self.m_button1 = wx.Button( self, wx.ID_OK, u"Run", wx.DefaultPosition, wx.DefaultSize, 0 )

		self.m_button1.SetDefault()
		bSizer1.Add( self.m_button1, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )

		self.m_button2 = wx.Button( self, wx.ID_CANCEL, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.m_button2, 0, wx.ALL, 5 )

		self.m_button3_delete = wx.Button( self, wx.ID_DELETE, u"Delete Vias", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.m_button3_delete, 0, wx.ALL, 5 )


		bSizer3.Add( bSizer1, 0, wx.EXPAND|wx.ALIGN_RIGHT, 5 )


		self.SetSizer( bSizer3 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.m_button3_delete.Bind( wx.EVT_BUTTON, self.onDeleteClick )

	def __del__( self ):
		pass


	# Virtual event handlers, override them in your derived class
	def onDeleteClick( self, event ):
		event.Skip()


