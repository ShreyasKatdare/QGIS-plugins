import numpy as np
import os

from qgis._gui import QgsMapMouseEvent
from .psql import *
from .attribute_utils import *
from .side_bar import *
from .map_tools import *

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


class Main:
    def __init__(self, parent):
        self.parent = parent
        self.dlg = self.parent.dlg
        self.iface = self.parent.iface
        self.canvas = self.iface.mapCanvas()
        self.side_bar = None
        self.param_selected = None
        self.history_old_vertices = []
        self.history_new_vertices = []
        self.history_transformed_vertices = []
        self.is_corner = {}
        self.rubber_bands = []
        self.points_to_transform = []
        self.layer = None
        self.survey_georef = "survey_georeferenced"
        self.survey_georef_layer = None
        
    
    def initiate(self):
        self.map = self.dlg.mapCombo.currentText()
        self.village = self.dlg.village_in.text()
        self.method = self.dlg.ratingCombo.currentText()
        self.psql_conn = PGConn()

        self.farmplots = "farmplots"
        self.corner_nodes = "corner_nodes"
        self.survey_georef = "survey_georeferenced"
        self.survey_georef_layer = None
        
        if self.side_bar is None:
            self.side_bar = SideBar(self.dlg , self)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.side_bar)

        if self.dlg.lineEdit_farmplots.text() != "":
            self.farmplots = self.dlg.lineEdit_farmplots.text()
        
        if self.dlg.lineEdit_host.text() != "":
            psql['host'] = self.dlg.lineEdit_host.text()
        else:
            psql['host'] = 'localhost'
            
        if self.dlg.lineEdit_port.text() != "":
            psql['port'] = self.dlg.lineEdit_port.text()
        else:
            psql['port'] = '5432'
            
        if self.dlg.lineEdit_user.text() != "":
            psql['user'] = self.dlg.lineEdit_user.text()
        else:
            psql['user'] = "postgres"
            
        if self.dlg.lineEdit_password.text() != "":
            psql['password'] = self.dlg.lineEdit_password.text()
        else:
            psql['password'] = "postgres"  
        
        if self.dlg.lineEdit_database.text() != "":
            psql['database'] = self.dlg.lineEdit_database.text()        
        else:
            psql['database'] = "dolr"
            
        QgsProject.instance().layerWillBeRemoved.connect(self.clean_up)
        
        
    def load_layers(self):
        village = self.village
        map = self.farmplots
        print("Loading Farmplots")
        layer = QgsVectorLayer(
                        f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                        f"{map}",
                        "postgres"
                    )
        if not layer.isValid():
            print("Farmplots failed to load!")
        else :
            self.farmplots_layer = layer
            symbol = QgsFillSymbol.createSimple({'color': 'green'})
            symbol.setOpacity(0.3)
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            QgsProject.instance().addMapLayer(layer)
            
            
        print("Loading Map")
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
            symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor('#3579b1'), 'outline_width': '1'})
            renderer = QgsSingleSymbolRenderer(symbol)
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            self.vertexselector = VertexSelector(self.canvas, self.layer, self)
            self.mover = NewVertex(self.canvas, self.layer, self)
            QgsProject.instance().addMapLayer(layer)
            self.display_rating(self.layer, self.param_selected)
            
        
        # Create topo
        print("Creating Topo")
        self.topo_name = f"{village}_{map}_topo_new"
        create_topo(self.psql_conn, self.village, self.topo_name, self.map)
        
        # Create corner nodes
        print("Creating Corner Nodes")
        self.corner_nodes = f"corner_nodes_{self.map}"
        get_corner_nodes(self.psql_conn, self.topo_name, self.village, self.corner_nodes)
        
        # Adding node_id column as Primary Key to corner nodes map so that
        # its geometry can be updated dynamically
        sql = f'''
                ALTER TABLE {self.village}.{self.corner_nodes}
                ADD CONSTRAINT pk_{self.corner_nodes} PRIMARY KEY (node_id);
        
            '''
        with self.psql_conn.connection().cursor() as curr:
            curr.execute(sql)
        
        
        map = self.corner_nodes
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='node_id' srid=32643 type=Point table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_editing",
            "postgres"
        )

        if not original_layer.isValid():
            print("Layer failed to load!")
        else:
            self.corner_nodes_layer = original_layer
            QgsProject.instance().addMapLayer(self.corner_nodes_layer)
        self.corners()
        
        # Load farm corner nodes
        map = "farm_corner_nodes"        
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='node_id' srid=32643 type=Point table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_colored",
            "postgres"
        )

        if not original_layer.isValid():
            print("farm corner nodes Layer failed to load!")
        else:
            self.farm_corner_nodes = original_layer
        
        map = self.survey_georef
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_colored",
            "postgres"
        )
        if not original_layer.isValid():
            print("Survey Layer failed to load!")
        else:
            self.survey_georef_layer = original_layer
        
    
    def select_vertex(self):
        self.canvas.unsetMapTool(self.mover)
        if self.vertexselector is not None:
            self.vertexselector.clearHighlight()
        if self.mover is not None:
            self.mover.clearHighlight()
        self.RemoveHighlight()
        self.canvas.setMapTool(self.vertexselector)
        
    def after_selection(self):
        print("AFTER SELECTION CALLED !!!!!!!!!!!!!!!!!!")
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
        self.neighbour_vertices()
        self.move_vertex()
        
    def move_vertex(self):
        self.canvas.setMapTool(self.mover)
        
    def after_new_vertex(self):
        print("AFTER NEW VERTEX CALLED !!!!!!!!!!!!!!!!!!")
        self.canvas.unsetMapTool(self.mover)
        self.update_map_corner_nodes(self.vertexselector.selected_vertex, self.mover.newvertex)
        self.layer.startEditing()
        self.history_new_vertices.append(self.mover.newvertex)
        self.history_old_vertices.append(self.vertexselector.selected_vertex)
        transformed_vertices = []
        for feature in self.features_of_concern:
            geom = feature.geometry()
            new_vertices = []
            for vertex in geom.vertices():
                if QgsPointXY(vertex.x(), vertex.y()) == self.vertexselector.selected_vertex:
                    if self.is_corner.get((vertex.x(), vertex.y())) is not None:
                        self.is_corner[(self.mover.newvertex.x(), self.mover.newvertex.y())] = True
                    new_vertices.append(QgsPointXY(self.mover.newvertex.x(), self.mover.newvertex.y()))

                
                elif self.is_present_as_first(vertex, self.points_to_transform):
                    ratio = None
                    for point in self.points_to_transform:
                        if point[0] == vertex:
                            ratio = point[1]
                            break
                    transformed_vertex = self.transform(self.vertexselector.selected_vertex, self.mover.newvertex, (QgsPointXY(vertex.x(), vertex.y()), ratio))
                    new_vertices.append(transformed_vertex)
                    transformed_vertices.append((transformed_vertex, ratio))

                else:
                    new_vertices.append(QgsPointXY(vertex.x(), vertex.y()))
            
            
            new_geom = QgsGeometry.fromPolygonXY([new_vertices])
            feature.setGeometry(new_geom)
            self.update_attributes(feature)
            self.layer.updateFeature(feature)
        
        self.history_transformed_vertices.append(transformed_vertices)        
        self.layer.commitChanges()
        self.canvas.refresh()
        self.display_rating(self.layer, self.param_selected)
        self.select_vertex()
    
    
    def clean_up(self, layer_id):
        if self.layer is not None and self.layer.id() == layer_id:
            self.canvas.unsetMapTool(self.vertexselector)
            self.canvas.unsetMapTool(self.mover)
            
            self.vertexselector.clearHighlight()
            self.mover.clearHighlight()
            self.canvas.setMapTool(None)
            
            if self.side_bar is not None:
                self.iface.removeDockWidget(self.side_bar)
                self.side_bar.deleteLater()
                self.side_bar = None

            self.vertexselector = None
            self.mover = None
            self.layer = None
    
            for rb in self.rubber_bands:
                self.canvas.scene().removeItem(rb)
            self.rubber_bands = []
    
    def display_rating(self, layer, field):
        self.param_selected = field
        if self.param_selected is None:
            layer.setLabelsEnabled(False)
            layer.triggerRepaint()
            return
        
        layer.setLabelsEnabled(True)

        provider = QgsPalLayerSettings()
        if field == "farm_rating" or field == "corrected_area_diff" or field == "excess_area":
            provider.fieldName = f"round(100*{field}, 4)"
        else:
            provider.fieldName = f"round({field}, 4)"
        provider.isExpression = True
        provider.placement = QgsPalLayerSettings.Horizontal
        layer.setLabeling(QgsVectorLayerSimpleLabeling(provider))
        layer.triggerRepaint()
        
    def undo(self):
        if len(self.history_old_vertices) == 0:
            return

        self.RemoveHighlight()
        self.vertexselector.clearHighlight()
        self.mover.clearHighlight()
        
        print("Undoing")
        print(len(self.history_old_vertices), len(self.history_new_vertices))
        old_vertex = self.history_old_vertices.pop()
        new_vertex = self.history_new_vertices.pop()
        transformed_vertices = self.history_transformed_vertices.pop()
        print("TRANSFORMED VERTICES : ")
        print(transformed_vertices)
        self.update_map_corner_nodes(new_vertex, old_vertex)
        
        for vertex in transformed_vertices:
            vertex_xy = QgsPointXY(vertex[0].x(), vertex[0].y())
            rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
            rubberBand.setToGeometry(QgsGeometry.fromPointXY(vertex_xy), self.layer)
            rubberBand.setColor(Qt.blue)
            rubberBand.setWidth(10)
            self.rubber_bands.append(rubberBand)
            
        self.layer.startEditing()
        features = self.layer.getFeatures()
        features_changing = []
        for feature in features:
            geom = feature.geometry()
            for vertex in geom.vertices():
                if QgsPointXY(vertex.x(), vertex.y()) == new_vertex:
                    features_changing.append(feature)
                    break
        
        for feature in features_changing:
            geom = feature.geometry()
            new_vertices = []
            for vertex in geom.vertices():
                if QgsPointXY(vertex.x(), vertex.y()) == new_vertex:
                    new_vertices.append(QgsPointXY(old_vertex.x(), old_vertex.y()))
                
                elif self.is_present_as_first(vertex, transformed_vertices):
                    print("UNDOING ON TRANSFORMED VERTICES ")
                    ratio = None
                    point_needed = QgsPointXY(vertex.x(), vertex.y())
                    for point in transformed_vertices:
                        point_xy = QgsPointXY(point[0].x(), point[0].y())
                        if point_xy.x() == point_needed.x() and point_xy.y() == point_needed.y():
                            ratio = point[1]
                            break
                    new_vertices.append(self.transform(new_vertex, old_vertex, (QgsPointXY(vertex.x(), vertex.y()), ratio)))
                
                else:
                    new_vertices.append(QgsPointXY(vertex.x(), vertex.y()))
            
            new_geom = QgsGeometry.fromPolygonXY([new_vertices])
            feature.setGeometry(new_geom)
            self.update_attributes(feature)
            self.layer.updateFeature(feature)
        
        self.layer.commitChanges()
        self.canvas.refresh()
        self.display_rating(self.layer, self.param_selected)

    def update_map_corner_nodes(self, old_vertex, new_vertex):
        old_vertex_xy = QgsPointXY(old_vertex.x(), old_vertex.y())
        new_vertex_xy = QgsPointXY(new_vertex.x(), new_vertex.y())
        self.corner_nodes_layer.startEditing()
        print("updating corner nodes layer")
        for feature in self.corner_nodes_layer.getFeatures():
            point = feature.geometry().asPoint()
            vertex_xy = QgsPointXY(point.x(), point.y())
            if vertex_xy.x() == old_vertex_xy.x() and vertex_xy.y() == old_vertex_xy.y():
                print("Got corresponding corner node")
                new_geom = QgsGeometry.fromPointXY(new_vertex_xy)
                feature.setGeometry(new_geom)
                self.corner_nodes_layer.updateFeature(feature)
                break
                
        self.corner_nodes_layer.commitChanges()
        self.corner_nodes_layer.triggerRepaint()
        self.canvas.refresh()
            
    
    
    
    def update_attributes(self, feature):
        new_akarbandh_area_diff = calculate_akarbandh_area_diff(feature)
        new_varp = calculate_varp(feature)
        if np.isnan(new_varp) or new_varp is None or new_varp == "":
            new_varp = 1
        new_shape_index = calculate_shape_index(feature)
        new_farm_rating = calculate_farm_rating(feature, self.method, self.farmplots_layer)
        new_farm_intersection = calculate_farm_intersection(feature, self.farmplots_layer)
        new_farm_rating_nodes = calculate_farm_rating_nodes(feature, self.farm_corner_nodes, self.corner_nodes_layer)
        new_excess_area = calculate_excess_area(feature, self.farmplots_layer)
        new_area_diff = calculate_area_diff(feature, self.survey_georef_layer)
        new_perimeter_diff = calculate_perimeter_diff(feature, self.survey_georef_layer)
        new_deviation = calculate_deviation(feature, self.survey_georef_layer)
        new_corrected_area_diff = calculate_corrected_area_diff(feature, self.survey_georef_layer)
    
        feature.setAttribute('akarbandh_area_diff', new_akarbandh_area_diff)
        ind = self.layer.fields().indexFromName('varp')
        feature.setAttribute(ind, float(new_varp))        
        feature.setAttribute('shape_index', new_shape_index)
        feature.setAttribute('farm_rating', new_farm_rating)
        feature.setAttribute('farm_intersection', new_farm_intersection)
        feature.setAttribute('farm_rating_nodes', new_farm_rating_nodes)
        feature.setAttribute('excess_area', new_excess_area)
        feature.setAttribute('area_diff', new_area_diff)
        feature.setAttribute('perimeter_diff', new_perimeter_diff)
        feature.setAttribute('deviation', new_deviation)
        feature.setAttribute('corrected_area_diff', new_corrected_area_diff)
    
    def generate_heatmap(self, attribute):
        print("generating heatmap")
        layer = self.layer
        field = attribute
        if field == "farm_rating":
            colors = [(0.0, QColor('#d7191c')), (0.8, QColor('#ffffc0')), (0.9, QColor('#1a9641')), (1.0, QColor('blue'))]
        
        elif field == "corrected_area_diff":
            colors = [(-100000, QColor('#ca0020')), (-0.05, QColor('#ec846e')), (-0.03, QColor('#f6d6c8')), (-0.01, QColor('#d3d3d3')), (0.01, QColor('#cfe3ed')), (0.03, QColor('#76b4d5')), (0.05, QColor('#0571b0')), (100000, QColor('blue'))]
        
        elif field == "excess_area":
            colors = [(0.0, QColor('#d3d3d3')), (0.01, QColor('#cfe3ed')), (0.03, QColor('#76b4d5')), (0.05, QColor('#0571b0')), (100000, QColor('blue'))]
        
        elif field == "farm_rating_nodes":
            n = 5
            colorRamp = QgsGradientColorRamp.create({'color1': '#d7191c', 'color2': '#1a9641', 'stops': '0.5;#ffffbf'})
            color = [colorRamp.color(i/(n-1)).name() for i in range(n)]
            color = color[::-1]
            colors = [(0, QColor(color[0])), (5, QColor(color[1])), (10, QColor(color[2])), (15, QColor(color[3])), (20, QColor(color[4])), (1000000, QColor('blue'))]
        
        ranges = []
        for i in range(len(colors) - 1):
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(colors[i][1])
            if field == "farm_rating_nodes":
                rng = QgsRendererRange(colors[i][0], colors[i+1][0], symbol, f"{colors[i][0]} - {colors[i+1][0]}")
            else:
                rng = QgsRendererRange(colors[i][0], colors[i+1][0], symbol, f"{100*colors[i][0]} - {100*colors[i+1][0]}")
            ranges.append(rng)

        renderer = QgsGraduatedSymbolRenderer(field, ranges)
        layer.setRenderer(renderer)

        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())
        
    def remove_heatmap(self):
        print("removing heatmap")
        layer = self.layer
        symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor('#3579b1'), 'outline_width': '1'})
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def corners(self):
        for feature in self.corner_nodes_layer.getFeatures():
            geom = feature.geometry()
            point = geom.asPoint()
            tup = (point.x(), point.y())
            self.is_corner[tup] = True
    
    def neighbour_vertices(self):
        self.points_to_transform = []
        features = self.features_of_concern
        print("number of features of concern : ", len(self.features_of_concern))
        geoms = []
        
        for feature in features:
            
            vertices = feature.geometry().vertices()
            ind = 0
            vertex_list = [vertex for vertex in vertices]
            n = len(vertex_list)
            for vertex in vertex_list:
                if QgsPointXY(vertex.x(), vertex.y()) == self.vertexselector.selected_vertex:
                    break
                ind += 1
            
            if ind == 0:
                i = 1
                j = n - 2
            elif ind == n-1:
                i = 1
                j = n - 2
            else:
                i = (ind + 1)%n
                j = (ind + n - 1)%n
            print("OOOOOhhhhhNNNOOOO", ind, i, j, n)
            
            prev_vertex = vertex_list[ind]
            dist = 0
            corner1_dist = None
            corner2_dist = None
            corner1_ind = None
            corner2_ind = None
            
            while i != ind:
                print("i = ", i)
                point_xy = QgsPointXY(vertex_list[i].x(), vertex_list[i].y())
                dist += prev_vertex.distance(vertex_list[i])
                prev_vertex = vertex_list[i]
                if point_xy != self.vertexselector.selected_vertex and self.is_corner.get((point_xy.x(), point_xy.y())) is not None:
                    print("corner found at i = ", i)
                    corner1_dist = dist
                    geom = QgsGeometry.fromPointXY(point_xy)
                    if geom not in geoms:
                        print("appending corner as it was not previously marked")
                        geoms.append(geom)
                    corner1_ind = i
                    break
                
                i = (i + 1)%n
            
            prev_vertex = vertex_list[ind]
            dist = 0
            
            while j != ind:
                print("j = ", j)
                point_xy = QgsPointXY(vertex_list[j].x(), vertex_list[j].y())
                dist += prev_vertex.distance(vertex_list[j])
                prev_vertex = vertex_list[j]
                if point_xy != self.vertexselector.selected_vertex and self.is_corner.get((point_xy.x(), point_xy.y())) is not None:
                    print("corner found at j = ", j)                    
                    corner2_dist = dist
                    geom = QgsGeometry.fromPointXY(point_xy)
                    if geom not in geoms:
                        print("appending corner as it was not previously marked")
                        geoms.append(geom)
                    corner2_ind = j
                    break
                
                j = (j + n - 1)%n
            
            
            prev_vertex = vertex_list[ind]
            dist = 0
            if ind == 0:
                i = 1
                j = n - 2
            elif ind == n-1:
                i = 1
                j = n - 2
            else:
                i = (ind + 1)%n
                j = (ind + n - 1)%n
            
            
            while i != corner1_ind and i != ind:
                dist += prev_vertex.distance(vertex_list[i])
                prev_vertex = vertex_list[i]
                if not self.is_present_as_first(vertex_list[i], self.points_to_transform):
                    self.points_to_transform.append((vertex_list[i], (corner1_dist - dist)/corner1_dist))
                i = (i + 1)%n
                
            prev_vertex = vertex_list[ind]
            dist = 0
            
            while j != corner2_ind and j != ind:                
                dist += prev_vertex.distance(vertex_list[j])
                prev_vertex = vertex_list[j]
                if not self.is_present_as_first(vertex_list[j], self.points_to_transform):
                    self.points_to_transform.append((vertex_list[j], (corner2_dist - dist)/ corner2_dist))
                j = (j + n - 1)%n
                
            print("neighbours : ", len(geoms))
            
        for point in self.points_to_transform:
            point_xy = QgsPointXY(point[0].x(), point[0].y())
            rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
            rubberBand.setToGeometry(QgsGeometry.fromPointXY(point_xy), self.layer)
            rubberBand.setColor(Qt.green)
            rubberBand.setWidth(10)
            self.rubber_bands.append(rubberBand)
            
        rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rubberBand.setToGeometry(QgsGeometry.fromPointXY(self.vertexselector.selected_vertex), self.layer)
        rubberBand.setColor(Qt.red)
        rubberBand.setWidth(10)
        self.rubber_bands.append(rubberBand)
        
        for geom in geoms:
            rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
            rubberBand.setToGeometry(geom, self.layer)
            rubberBand.setColor(Qt.yellow)
            rubberBand.setWidth(10)
            self.rubber_bands.append(rubberBand)
        
            
    
    def RemoveHighlight(self):
        for rb in self.rubber_bands:
            self.canvas.scene().removeItem(rb)
            del rb
        self.rubber_bands = []

    def transform(self, old_vertex, new_vertex, point_and_ratio):
        dx = new_vertex.x() - old_vertex.x()
        dy = new_vertex.y() - old_vertex.y()
        
        point_transformed = QgsPointXY(point_and_ratio[0].x() + point_and_ratio[1]*dx, point_and_ratio[0].y() + point_and_ratio[1]*dy)
        rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rubberBand.setToGeometry(QgsGeometry.fromPointXY(point_transformed), self.layer)
        rubberBand.setColor(QColor(255, 165, 0))
        rubberBand.setWidth(10)
        self.rubber_bands.append(rubberBand)
        return point_transformed
    
    def is_present_as_first(self, element, list):
        point_xy = QgsPointXY(element.x(), element.y())
        for sublist in list:
            point_xy_2 = QgsPointXY(sublist[0].x(), sublist[0].y())
            if point_xy.x() == point_xy_2.x() and point_xy.y() == point_xy_2.y():
                return True
        return False
    
    def deactivate(self):
        if self.vertexselector is not None:
            self.vertexselector.clearHighlight()
        if self.mover is not None:
            self.mover.clearHighlight()
        self.canvas.unsetMapTool(self.vertexselector)
        self.canvas.unsetMapTool(self.mover)
        self.RemoveHighlight()
        
    def save_layer_postgres(self):
        schema = self.village
        table_name = f"{self.map}_editing"
        drop_table(self.psql_conn, schema, table_name)
        uri = QgsDataSourceUri()
        uri.setConnection(psql['host'], psql['port'], psql['database'], psql['user'], psql['password'])
        uri.setDataSource(schema, table_name, "geom")
        err = QgsVectorLayerExporter.exportLayer(self.layer, uri.uri(), "postgres", QgsCoordinateReferenceSystem(), False)

        if err[0] != QgsVectorLayerExporter.NoError:
            print("Error when saving layer to Postgres: ", err)
        else:
            print("Layer saved successfully")  
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer saved successfully\nYou will be able to see the layer named {table_name} in schema {schema}")
            msg.setWindowTitle("Success")
            # msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        
        
    def run(self):
        self.initiate()
        self.load_layers()
        
    