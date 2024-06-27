# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mover2Dialog
                                 A QGIS plugin
 mover2
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-06-10
        git sha              : $Format:%H$
        copyright            : (C) 2024 by sk
        email                : shreyas.08kat@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import numpy as np
import os

from qgis._gui import QgsMapMouseEvent
from .psql import *
from .attribute_utils import *

import psycopg2
import os
import qgis.utils
import qgis

from PyQt5.QtGui import QColor
from PyQt5 import QtCore
from PyQt5.QtCore import QPointF, Qt
from qgis.PyQt import uic, QtWidgets

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsVectorLayerEditUtils,
    QgsSymbol,
    QgsRendererRange,
    QgsGraduatedSymbolRenderer,
    QgsFeature,
    QgsLineSymbol,
    QgsGeometry,
    QgsSingleSymbolRenderer,
    QgsFillSymbol,
    QgsWkbTypes,
    QgsFeatureRequest,
    QgsField,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsPointXY,
    QgsAnnotation,
    QgsCoordinateReferenceSystem,
    QgsTextAnnotation,
    QgsRuleBasedRenderer,
    QgsGradientColorRamp,
    QgsVectorLayerExporter,
    QgsProperty
)
from qgis.core import QgsVectorFileWriter, QgsDataSourceUri
from PyQt5.QtCore import pyqtSignal
from qgis.gui import QgsMapCanvasAnnotationItem, QgsMapToolEmitPoint, QgsRubberBand, QgsMapTool
from qgis.gui import QgsMapToolEmitPoint
from PyQt5.QtGui import QColor, QTextDocument, QFont
from PyQt5.QtCore import QSizeF, QPointF, Qt
from qgis.PyQt.QtCore import QVariant 
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDockWidget, QMessageBox, QAction, QFormLayout, QLabel, QPushButton, QRadioButton, QFileDialog


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mover2_dialog_base.ui'))


class mover2Dialog(QtWidgets.QDialog, FORM_CLASS):
    '''
    This class is used to create the dialog box for the plugin which pops 
    up when the plugin icon is clicked
    If you want to change fields in the dialog box, you can do that here 
    or to add new buttons on the dialog box, you can add them by opening the
    mover2_dialog_base.ui file in Qt Designer and adding the buttons there and changing
    the code in this file accordingly
    '''
    def __init__(self, iface, parent=None):
        """
        Constructor.
        :param iface: An interface instance that will be passed to this class
                      which provides the hook by which you can manipulate the QGIS
                      application at run time.
        :type iface: QgsInterface

        :param parent: Not needed here
        :type parent: QWidget

        """
        super(mover2Dialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.hide_show_more = True
        
        self.ratingLabel.hide()
        self.ratingCombo.hide()
        self.defaultLabel.hide()
        self.label_3.hide()
        self.label_4.hide()
        self.label_5.hide()
        self.label_6.hide()
        self.label_10.hide()
        self.label_11.hide()
        self.label_13.hide()
        self.label_16.hide()
        
        # If you want to add additional map name to drop down, add it here
        self.mapCombo.addItems(['jitter_spline_output_regularised_03', 'survey_georeferenced', 'shifted_faces', 'jitter_spline_output_regularised_05', 'farm_graph_faces', 'jitter_spline_output_regularised_03_editing', 'survey_georeferenced_editing', 'shifted_faces_editing', 'jitter_spline_output_regularised_05_editing', 'farm_graph_faces_editing'])
        
        # The following code is used to set the default values for the fields in the dialog box
        # like the host, port, user, password, database, farmplots, etc.

        self.lineEdit_farmplots.setText('farmplots')
        self.lineEdit_host.setText('localhost')
        self.lineEdit_port.setText('5432')
        self.lineEdit_user.setText('postgres')
        self.lineEdit_password.setText('postgres')
        self.lineEdit_database.setText('dolr')
        
        self.lineEdit_farmplots.hide()
        self.lineEdit_host.hide()
        self.lineEdit_port.hide()
        self.lineEdit_user.hide()
        self.lineEdit_password.hide()
        self.lineEdit_database.hide()
        self.ratingCombo.addItems(['worst_3_avg', 'all_avg'])
        self.ratingCombo.setCurrentText('worst_3_avg')
        self.showButton.clicked.connect(self.show_hide)
        
    
    def show_hide(self):
        '''
        This function is used to show or hide the additional fields
        '''

        if self.hide_show_more:
            self.ratingLabel.show()
            self.ratingCombo.show()
            self.defaultLabel.show()
            
            self.label_3.show()
            self.label_4.show()
            self.label_5.show()
            self.label_6.show()
            self.label_10.show()
            self.label_11.show()
            self.label_13.show()
            self.label_16.show()
            
            self.lineEdit_farmplots.show()
            self.lineEdit_host.show()
            self.lineEdit_port.show()
            self.lineEdit_user.show()
            self.lineEdit_password.show()
            self.lineEdit_database.show()
            
            self.hide_show_more = False
        else:
            self.ratingLabel.hide()
            self.ratingCombo.hide()
            self.defaultLabel.hide()
            
            self.label_3.hide()
            self.label_4.hide()
            self.label_5.hide()
            self.label_6.hide()
            self.label_10.hide()
            self.label_11.hide()
            self.label_13.hide()
            self.label_16.hide()
            
            self.lineEdit_farmplots.hide()
            self.lineEdit_host.hide()
            self.lineEdit_port.hide()
            self.lineEdit_user.hide()
            self.lineEdit_password.hide()
            self.lineEdit_database.hide()
            
            self.hide_show_more = True         
    
#_______________________________________________________________________________________________________________________
