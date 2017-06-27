# -*- coding: utf-8 -*- 

###########################################################################
## Python code generated with wxFormBuilder (version Dec 21 2016)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class CircularZoneDlg
###########################################################################

class CircularZoneDlg ( wx.Dialog ):
	
	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Circular zone parameters", pos = wx.DefaultPosition, size = wx.Size( 373,290 ), style = wx.DEFAULT_DIALOG_STYLE )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		
		bSizer3 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_comment = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_comment.Wrap( -1 )
		bSizer3.Add( self.m_comment, 0, wx.ALL|wx.EXPAND, 5 )
		
		bSizer31 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.m_staticText3 = wx.StaticText( self, wx.ID_ANY, u"Radius (mm)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText3.Wrap( -1 )
		bSizer31.Add( self.m_staticText3, 1, wx.ALL|wx.EXPAND, 5 )
		
		self.m_radiusMM = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_radiusMM.SetMinSize( wx.Size( 1000,-1 ) )
		
		bSizer31.Add( self.m_radiusMM, 1, wx.ALL|wx.EXPAND, 5 )
		
		
		bSizer3.Add( bSizer31, 0, 0, 5 )
		
		bSizer4 = wx.BoxSizer( wx.HORIZONTAL )
		
		sbSizer1 = wx.StaticBoxSizer( wx.StaticBox( self, wx.ID_ANY, u"Type of Zone" ), wx.VERTICAL )
		
		self.m_radio_std = wx.RadioButton( sbSizer1.GetStaticBox(), wx.ID_ANY, u"Standard", wx.DefaultPosition, wx.DefaultSize, 0 )
		sbSizer1.Add( self.m_radio_std, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, 5 )
		
		self.m_radio_out = wx.RadioButton( sbSizer1.GetStaticBox(), wx.ID_ANY, u"Keepout", wx.DefaultPosition, wx.DefaultSize, 0 )
		sbSizer1.Add( self.m_radio_out, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		
		bSizer4.Add( sbSizer1, 1, wx.EXPAND, 5 )
		
		sbSizer2 = wx.StaticBoxSizer( wx.StaticBox( self, wx.ID_ANY, u"Number of segments" ), wx.VERTICAL )
		
		self.m_textCtrl_seg = wx.TextCtrl( sbSizer2.GetStaticBox(), wx.ID_ANY, u"64", wx.DefaultPosition, wx.DefaultSize, 0 )
		sbSizer2.Add( self.m_textCtrl_seg, 0, wx.ALL|wx.EXPAND, 5 )
		
		
		bSizer4.Add( sbSizer2, 1, wx.EXPAND, 5 )
		
		
		bSizer3.Add( bSizer4, 1, wx.EXPAND, 5 )
		
		bSizer1 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.m_staticText101 = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText101.Wrap( -1 )
		bSizer1.Add( self.m_staticText101, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_button1 = wx.Button( self, wx.ID_OK, u"Create", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_button1.SetDefault() 
		bSizer1.Add( self.m_button1, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		self.m_button2 = wx.Button( self, wx.ID_CANCEL, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer1.Add( self.m_button2, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5 )
		
		
		bSizer3.Add( bSizer1, 0, wx.ALIGN_RIGHT|wx.EXPAND, 5 )
		
		
		self.SetSizer( bSizer3 )
		self.Layout()
		
		self.Centre( wx.BOTH )
	
	def __del__( self ):
		pass
	

