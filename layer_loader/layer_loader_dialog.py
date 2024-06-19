# -*- coding: utf-8 -*-
"""
/***************************************************************************
 layer_loaderDialog
                                 A QGIS plugin
 layer_loader
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-06-19
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
import os
from .psql import *

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
    QgsSymbol,
    QgsRendererRange,
    QgsGraduatedSymbolRenderer,
    QgsFeature,
    QgsGeometry,
    QgsSingleSymbolRenderer,
    QgsFillSymbol,
    QgsExpression,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsPointXY,
    QgsAnnotation,
    QgsCoordinateReferenceSystem,
    QgsTextAnnotation,
    QgsRuleBasedRenderer
)
from qgis.gui import QgsMapCanvasAnnotationItem
from qgis.gui import QgsMapToolEmitPoint
from PyQt5.QtGui import QColor, QTextDocument, QFont, QIcon
from PyQt5.QtCore import QSizeF, QPointF, QSize
from PyQt5.QtWidgets import QScrollArea, QColorDialog, QDoubleSpinBox, QDialog, QSpacerItem, QVBoxLayout, QSizePolicy, QHBoxLayout, QSlider,QCheckBox, QDockWidget, QWidget, QFormLayout, QLabel, QPushButton, QLineEdit, QGridLayout, QButtonGroup


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'layer_loader_dialog_base.ui'))


class layer_loaderDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(layer_loaderDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.num_layer = 0
        
        self.form_layout = QFormLayout()
        self.setLayout(self.form_layout)
        self.setWindowTitle('Layer Loader')
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        scroll_content = QWidget(self.scroll_area)
        scroll_content.setLayout(self.form_layout)
        self.scroll_area.setWidget(scroll_content)
        
        button_box_layout = QHBoxLayout()
        button_box_layout.addStretch(1)
        button_box_layout.addWidget(self.button_box)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scroll_area)
        main_layout.addLayout(button_box_layout)
        
        self.village_name = QLineEdit()
        self.village_name.setFont(QFont('Helvetica', 12))
        label = QLabel('Village Name:')
        label.setFont(QFont('Helvetica', 12))
        
        label2 = QLabel('Database Name:')
        label2.setFont(QFont('Helvetica', 12))
        label3 = QLabel('Host:')
        label3.setFont(QFont('Helvetica', 12))
        label4 = QLabel('Port:')
        label4.setFont(QFont('Helvetica', 12))
        label5 = QLabel('Username:')
        label5.setFont(QFont('Helvetica', 12))
        label6 = QLabel('Password:')
        label6.setFont(QFont('Helvetica', 12))
        
        self.hbox1 = QHBoxLayout()
        self.hbox2 = QHBoxLayout()
        
        self.lineEdit_user = QLineEdit()
        self.lineEdit_user.setText('postgres')
        
        self.lineEdit_database = QLineEdit()
        self.lineEdit_database.setText('dolr')
        
        self.line_Edit_password = QLineEdit()
        self.line_Edit_password.setText('postgres')
        
        self.lineEdit_host = QLineEdit()
        self.lineEdit_host.setText('localhost')
        
        self.lineEdit_port = QLineEdit()
        self.lineEdit_port.setText('5432')
        
        self.hbox1.addWidget(label2)
        self.hbox1.addWidget(self.lineEdit_database)
        self.hbox1.addWidget(label)
        self.hbox1.addWidget(self.village_name)
        
        self.hbox2.addWidget(label3)
        self.hbox2.addWidget(self.lineEdit_host)
        self.hbox2.addWidget(label4)
        self.hbox2.addWidget(self.lineEdit_port)
        self.hbox2.addWidget(label5)
        self.hbox2.addWidget(self.lineEdit_user)
        self.hbox2.addWidget(label6)
        self.hbox2.addWidget(self.line_Edit_password)
        
        self.add_layer_button = QPushButton('Add Layer')
        self.add_layer_button.setFont(QFont('Helvetica', 12))
        self.add_layer_button.clicked.connect(self.add_layer)
        
        self.form_layout.addRow(self.hbox1)
        self.form_layout.addRow(self.hbox2)
        self.form_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.form_layout.addRow(self.add_layer_button)
        self.layer_names = []
        
        
        
    def add_layer(self):
        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()
        self.num_layer += 1
        
        layer_name = QLineEdit()
        layer_name.setFont(QFont('Helvetica', 12))
        layer_name.setPlaceholderText('Layer Name')
        
        select_symbology_button = QPushButton('Select Symbology')
        select_symbology_button.setFont(QFont('Helvetica', 12))
        symbology_label = QLabel('No symbology')
        symbology_label.setFont(QFont('Helvetica', 12))
        
        select_color_button = QPushButton('Select Color')
        select_color_button.setFont(QFont('Helvetica', 12))
        color_label = QLabel('No color')
        color_label.setFont(QFont('Helvetica', 12))
        
        symbol = [select_symbology_button, symbology_label]
        symbol[0].clicked.connect(lambda: self.select_symbology(symbol[1]))
        
        color = [select_color_button, color_label]
        color[0].clicked.connect(lambda: self.select_color(color[1]))

        opacity_label = QLabel('Opacity : 100 %')
        opacity_label.setFont(QFont('Helvetica', 12))
        
        opacity_slider = QSlider(Qt.Horizontal)
        opacity_slider.setRange(0, 100)
        opacity_slider.setValue(100)
        # opacity_slider.valueChanged.connect(self.update_opacity)
        opacity = [opacity_label, opacity_slider]
        opacity[1].valueChanged.connect(lambda value, label = opacity[0]: label.setText(f'Opacity: {value} %'))
        
        sizewidth_label = QLabel('Size : ')
        sizewidth_label.setFont(QFont('Helvetica', 12))
        sizewidth_button = QDoubleSpinBox()
        sizewidth_button.setRange(0, 100)
        sizewidth_button.setValue(1)
        sizewidth_button.setSingleStep(0.1)
        sizewidth_button.setFont(QFont('Helvetica', 12))
        
        hbox1.addWidget(layer_name)
        hbox1.addWidget(select_symbology_button)
        hbox1.addWidget(symbology_label)
        
        hbox2.addWidget(opacity_label)
        hbox2.addWidget(opacity_slider)
        hbox2.addWidget(select_color_button)
        hbox2.addWidget(color_label)
        hbox2.addWidget(sizewidth_label)
        hbox2.addWidget(sizewidth_button)
        
        self.form_layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.form_layout.addRow(hbox1)
        self.form_layout.addRow(hbox2)
        self.layer_names.append((layer_name, symbology_label, opacity_slider, color_label, sizewidth_button))

    def select_symbology(self, label):
        symbology_dialog = SymbologySelectorDialog(self)
        
        if symbology_dialog.exec_():
            selected_symbol = symbology_dialog.get_selected_symbol()
            label.setText(f'Selected: {selected_symbol}')
    
    def select_color(self, label):
        color_dialog = QColorDialog(self)
        color = color_dialog.getColor()
        label.setText(f'{color.name()}')
#________________________________________________________________________________________

class SymbologySelectorDialog(QDialog):
    def __init__(self, parent=None):
        super(SymbologySelectorDialog, self).__init__(parent)
        self.setWindowTitle('Select Symbology')
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.grid_layout = QGridLayout()
        self.layout.addLayout(self.grid_layout)

        self.button_group = QButtonGroup()
        self.button_group.buttonClicked[int].connect(self.button_clicked)

        self.symbols = ['simple_fill', 'outline', 'circle', 'diamond', 'triangle']  
        
        plugin_dir = os.path.dirname(__file__)
        
        self.symbol_icons = [
            os.path.join(plugin_dir, 'icons', 'simple_fill.png'),
            os.path.join(plugin_dir, 'icons', 'outline.png'),
            os.path.join(plugin_dir, 'icons', 'circle.png'),
            os.path.join(plugin_dir, 'icons', 'diamond.png'),
            os.path.join(plugin_dir, 'icons', 'triangle.png')
            ]
        for i, (symbol, icon) in enumerate(zip(self.symbols, self.symbol_icons)):
            button = QPushButton()
            button.setIcon(QIcon(icon))
            button.setIconSize(QSize(128, 128))
            button.setCheckable(True)
            self.button_group.addButton(button, i)
            self.grid_layout.addWidget(button, i // 3, i % 3)

        self.selected_symbol = None
    
    def button_clicked(self, id):
        self.selected_symbol = self.symbols[id]
        self.accept()

    def get_selected_symbol(self):
        return self.selected_symbol