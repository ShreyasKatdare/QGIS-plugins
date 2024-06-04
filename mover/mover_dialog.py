# -*- coding: utf-8 -*-
"""
/***************************************************************************
 moverDialog
                                 A QGIS plugin
 mover
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-05-24
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
from .utils import *
from .postgres_utils import *

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
    QgsRuleBasedRenderer
)
from qgis.core import QgsVectorFileWriter, QgsDataSourceUri
from PyQt5.QtCore import pyqtSignal
from qgis.gui import QgsMapCanvasAnnotationItem, QgsMapToolEmitPoint, QgsRubberBand, QgsMapTool
from qgis.gui import QgsMapToolEmitPoint
from PyQt5.QtGui import QColor, QTextDocument
from PyQt5.QtCore import QSizeF, QPointF, Qt
from qgis.PyQt.QtCore import QVariant 
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDockWidget, QMessageBox, QAction

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'mover_dialog_base.ui'))


        
class VertexSelector(QgsMapTool):
    finished = pyqtSignal()
    def __init__(self, canvas, layer):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.selected_vertex = None
        self.highlighted_vertex = None
        self.rubber_bands = []

    def canvasMoveEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        closest_vertex = self.findClosestVertex(point)
        if closest_vertex:
            if closest_vertex != self.highlighted_vertex:
                self.highlightVertex(closest_vertex)
                self.highlighted_vertex = closest_vertex
        else:
            self.clearHighlight()

    def canvasPressEvent(self, event):
        if self.highlighted_vertex:
            self.selected_vertex = self.highlighted_vertex
            QMessageBox.information(None, "Vertex Selected", f"Vertex at {self.selected_vertex.x()}, {self.selected_vertex.y()} selected")
            self.finished.emit()
    
    def findClosestVertex(self, point):
        closest_vertex = None
        min_dist = float('inf')
        for feature in self.layer.getFeatures():
            geom = feature.geometry()
            for vertex in geom.vertices():
                vertex_point = QgsPointXY(vertex.x(), vertex.y())
                # dist = QgsGeometry.fromPointXY(vertex_point).distance(QgsGeometry.fromPointXY(point))
                dist = vertex_point.distance(QgsPointXY(point))
                if dist < min_dist:
                    min_dist = dist
                    closest_vertex = vertex_point
        return closest_vertex

    
    def highlightVertex(self, vertex):
        self.clearHighlight()
        rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rubberBand.setToGeometry(QgsGeometry.fromPointXY(vertex), self.layer)
        rubberBand.setColor(Qt.red)
        rubberBand.setWidth(10)
        self.rubber_bands.append(rubberBand)

    def clearHighlight(self):
        for rb in self.rubber_bands:
            self.canvas.scene().removeItem(rb)
        self.rubber_bands = []
        self.highlighted_vertex = None
        
    
class NewVertex(QgsMapTool):
    finished = pyqtSignal()
    def __init__(self, canvas, layer):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.newvertex = None
        
    def canvasPressEvent(self, event):
        self.newvertex = self.toMapCoordinates(event.pos())
        print("New Vertex : ", self.newvertex)
        rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rubberBand.setToGeometry(QgsGeometry.fromPointXY(self.newvertex), self.layer)
        rubberBand.setColor(Qt.blue)
        rubberBand.setWidth(10)
        self.finished.emit()
       

class moverDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(moverDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.village = 'dagdagad'
        self.map = 'survey_georeferenced'
        self.farmplots = "farmplots"
        self.pgconn = PGConn(psql)
        self.ok_button.accepted.connect(self.load_map)
        
    def load_map(self):
        village = self.village
        map = self.farmplots
        layer = QgsVectorLayer(
                        f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                        f"{map}",
                        "postgres"
                    )
        if not layer.isValid():
            print("Farmplots failed to load!")
        else :
            self.farmplots_layer = layer
            
        
        village = self.village
        map =  self.map
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_colored",
            "postgres"
        )

        if not original_layer.isValid():
            print("Layer failed to load!")
        else:
            layer = QgsVectorLayer("Polygon?crs=epsg:32643", "temporary_layer", "memory")
            data_provider = layer.dataProvider()
            data_provider.addAttributes(original_layer.fields())
            layer.updateFields()
            for feature in original_layer.getFeatures():
                data_provider.addFeature(feature)

            self.layer = layer
            self.vertexselector = VertexSelector(self.canvas, self.layer)
            self.mover = NewVertex(self.canvas, self.layer)
            QgsProject.instance().addMapLayer(layer)
            self.set_up()
            
    def set_up(self):
        self.select_action = QAction("Select Vertex", self.iface.mainWindow())
        self.select_action.triggered.connect(self.select_vertex)
        self.iface.addToolBarIcon(self.select_action)
        
        self.move_action = QAction("New vertex", self.iface.mainWindow())
        self.move_action.triggered.connect(self.move_vertex)
        self.iface.addToolBarIcon(self.move_action)
        
    def select_vertex(self):
        self.canvas.setMapTool(self.vertexselector)
        self.vertexselector.finished.connect(self.after_selection)

    def after_selection(self):
        self.canvas.unsetMapTool(self.vertexselector)
        print("Selected Vertex : ", self.vertexselector.selected_vertex)
        features = self.layer.getFeatures()
        self.ids_to_select = []
        self.features_of_concern = []
        for feature in features:
            geom = feature.geometry()
            for vertex in geom.vertices():
                if QgsPointXY(vertex.x(), vertex.y()) == self.vertexselector.selected_vertex:
                    self.ids_to_select.append(feature.id())
                    self.features_of_concern.append(feature)
                    break
        
        print("Selected Features : ", self.ids_to_select)
        self.layer.selectByIds(self.ids_to_select)
        
    def move_vertex(self):
        self.canvas.setMapTool(self.mover)
        self.mover.finished.connect(self.after_new_vertex)
        
    def after_new_vertex(self):
        self.canvas.unsetMapTool(self.mover)
        self.layer.startEditing()
        for feature in self.features_of_concern:
            geom = feature.geometry()
            new_vertices = []
            for vertex in geom.vertices():
                if QgsPointXY(vertex.x(), vertex.y()) == self.vertexselector.selected_vertex:
                    new_vertices.append(QgsPointXY(self.mover.newvertex.x(), self.mover.newvertex.y()))
                else:
                    new_vertices.append(QgsPointXY(vertex.x(), vertex.y()))
            
            new_geom = QgsGeometry.fromPolygonXY([new_vertices])
            feature.setGeometry(new_geom)
            new_farmrating = self.calculate_farmrating(feature, 'worst_3_avg')
            feature.setAttribute('farm_rating', new_farmrating)
            self.layer.updateFeature(feature)
        
        # add_farm_rating(self.pgconn, self.village, 'temporary_layer', self.farmplots, 'farm_rating', 'all_avg')
        
        self.layer.commitChanges()
        self.canvas.refresh()
        
        
    def calculate_farmrating(self, feature, method):
        if method == 'all_avg':
            geom_a = feature.geometry()
            ratings = []
            features = self.farmplots_layer.getFeatures()
            for farmplot_feature in features:
                geom_b = farmplot_feature.geometry()

                if geom_a.buffer(20, 5).intersects(geom_b):
                    intersection = geom_a.intersection(geom_b)
                    difference = geom_b.difference(geom_a)

                    intersection_area = intersection.area()
                    difference_area = difference.area()
                    geom_b_area = geom_b.area()

                    rating = max(intersection_area, difference_area) / geom_b_area
                    ratings.append(rating)

            if ratings:
                return sum(ratings) / len(ratings)
            else:
                return 0.0
        
        elif method == 'worst_3_avg':
            geom_a = feature.geometry()
            ratings = []
            features = self.farmplots_layer.getFeatures()
            for farmplot_feature in features:
                geom_b = farmplot_feature.geometry()

                if geom_a.buffer(20, 5).intersects(geom_b):
                    intersection = geom_a.intersection(geom_b)
                    difference = geom_b.difference(geom_a)

                    intersection_area = intersection.area()
                    difference_area = difference.area()
                    geom_b_area = geom_b.area()

                    rating = max(intersection_area, difference_area) / geom_b_area
                    ratings.append(rating)

            if ratings:
                ratings.sort()
                return sum(ratings[:3]) / 3
            else:
                return 0.0