# -*- coding: utf-8 -*-
"""
/***************************************************************************
 heatmap2Dialog
                                 A QGIS plugin
 Heatmap analysis
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-05-20
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
from PyQt5.QtGui import QColor, QTextDocument
from PyQt5.QtCore import QSizeF, QPointF
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDockWidget, QWidget

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'heatmap2_dialog_base.ui'))


class heatmap2Dialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(heatmap2Dialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self.heatmap_toggle = None
        self.ok_button.accepted.connect(self.load_maps)
        QgsProject.instance().layersRemoved.connect(self.on_layers_removed)
        
    def load_maps(self):
        maps = ["farmplots", "survey_georeferenced", "jitter_spline_output_regularised_05", "jitter_polygons_regularised_05"]
        village = self.village_in.text()
        map = maps[0]
        layer = QgsVectorLayer(
                        f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                        f"{map}",
                        "postgres"
                    )
        if not layer.isValid():
            print("Layer failed to load!")
        else :
            
            symbol = QgsFillSymbol.createSimple({'color': 'green'})
            symbol.setOpacity(0.3)
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            QgsProject.instance().addMapLayer(layer)
            
        map = maps[1]
        layer = QgsVectorLayer(
                        f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                        f"{map}",
                        "postgres"
                    )
        if not layer.isValid():
            print("Layer failed to load!")
        else :
            symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor('#3579b1'), 'outline_width': '1'})
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            QgsProject.instance().addMapLayer(layer)
            
        map = maps[2]
        layer = QgsVectorLayer(
                        f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                        f"{map}",
                        "postgres"
                    )
        if not layer.isValid():
            print("Layer failed to load!")
        else :
            symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor('#e41a1c'), 'outline_width': '1'})
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            QgsProject.instance().addMapLayer(layer)
        
        map = maps[3]
        layer = QgsVectorLayer(
                        f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                        f"{map}",
                        "postgres"
                    )
        if not layer.isValid():
            print("Layer failed to load!")
        else :
            symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor('#000000'), 'outline_width': '1'})
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            QgsProject.instance().addMapLayer(layer)
        
        if self.heatmap_toggle is None:    
            self.heatmap_toggle = HeatMapToggle(self, self)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.heatmap_toggle)
        else:
            self.heatmap_toggle.dialog = self
        
    def generate_heatmap(self, attribute):
        print("generating heatmap")
        layer = QgsProject.instance().mapLayersByName("jitter_spline_output_regularised_05")[0]
        field = attribute
        if field == "farm_rating":
            colors = [(0.0, QColor('#d7191c')), (0.8, QColor('#ffffc0')), (0.9, QColor('#1a9641')), (1.0, QColor('blue'))]
        
        elif field == "actual_area_diff":
            colors = [(-100000, QColor('#ca0020')), (-0.05, QColor('#ec846e')), (-0.03, QColor('#f6d6c8')), (-0.01, QColor('#d3d3d3')), (0.01, QColor('#cfe3ed')), (0.03, QColor('#76b4d5')), (0.05, QColor('#0571b0')), (100000, QColor('blue'))]
        ranges = []
        for i in range(len(colors) - 1):
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(colors[i][1])
            rng = QgsRendererRange(colors[i][0], colors[i+1][0], symbol, f"{100*colors[i][0]} - {100*colors[i+1][0]}")
            ranges.append(rng)

        renderer = QgsGraduatedSymbolRenderer(field, ranges)
        layer.setRenderer(renderer)

        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())
        
    def on_layers_removed(self, layers):
        if len(QgsProject.instance().mapLayers()) == 0:
            if self.heatmap_toggle:
                self.iface.removeDockWidget(self.heatmap_toggle)
                self.heatmap_toggle.deleteLater()
                self.heatmap_toggle = None
    
    def remove_heatmap(self):
        print("removing heatmap")
        layer = QgsProject.instance().mapLayersByName("jitter_spline_output_regularised_05")[0]
        symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor('#e41a1c'), 'outline_width': '1'})
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())
    
class HeatMapToggle(QDockWidget):
    def __init__(self, parent=None, dialog=None):
        super(HeatMapToggle, self).__init__(parent)
        self.dialog = dialog
        self.label = QtWidgets.QLabel("Generate heatmap")
        self.checkbox1 = QCheckBox("Farm rating heatmap")
        self.checkbox2 = QCheckBox("Actual area difference heatmap")
        self.checkbox1.stateChanged.connect(self.on_checkbox1_state_changed)
        self.checkbox2.stateChanged.connect(self.on_checkbox2_state_changed)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.checkbox1)
        layout.addWidget(self.checkbox2)

        widget = QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)
        
    def on_checkbox1_state_changed(self, state):
        if state == Qt.Checked:
            self.dialog.generate_heatmap("farm_rating")
        else:
            self.dialog.remove_heatmap()
            
    def on_checkbox2_state_changed(self, state):
        if state == Qt.Checked:
            self.dialog.generate_heatmap("actual_area_diff")
        else:
            self.dialog.remove_heatmap()