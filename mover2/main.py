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
    '''
    This class is the main class of the plugin where all the core logic and 
    functionality of the plugin is implemented
    '''
    def __init__(self, parent):
        '''
        Constructor
        :param parent: The parent widget, here parent is instance of mover2 class which is
                       used to get the iface and dialog box
        '''
        self.parent = parent
        self.dlg = self.parent.dlg
        self.iface = self.parent.iface
        self.canvas = self.iface.mapCanvas()
        self.side_bar = None

        # This is the parameter to display when user clicks on one of the parameters 
        # under 'parameter to display' in the side bar
        self.param_selected = None
        
        # These 3 lists are used to store the old, new, transformed (vertices which lie between
        # selected vertex and pivots) vertices to implement undo functionality
        self.history_old_vertices = []
        self.history_new_vertices = []
        # transformed vertices are stored along with the ratio with which they were transformed
        self.history_transformed_vertices = []

        # Dictionary to store whether a vertex is a corner or not for editing map
        self.is_corner = {}

        # List to store highlighted rubber bands
        self.rubber_bands = []

        # List to store the points between selected vertex and pivots
        self.points_to_transform = []

        # Layer on which editing is to be done
        self.layer = None

        # Node id of selected vertex
        self.node_id = None
        
        # flag to tell whether logs table is to be dropped and newly created
        self.logs_first_time = False

        # List to store the history logs of the changes made
        self.logs = []
        
    
    def initiate(self):
        
        # Get the values from the dialog box entered by the user
        # These lineEdit and comboBox values are entered by the user in the dialog box
        # which is defined in the ui file (Open it in Qt Designer)
        # self.dlg is the dialog box object (which is define in mover2_dialog.py)
        self.map = self.dlg.mapCombo.currentText()
        self.village = self.dlg.village_in.text()
        self.method = self.dlg.ratingCombo.currentText()
        self.psql_conn = PGConn()

        self.farmplots = "farmplots"
        self.corner_nodes = "corner_nodes"

        # NOTE : This survey_georeferenced layer is needed to re-calculate the attributes 
        # like area_diff, perimeter_diff, deviation when the user moves a vertex
        self.survey_georef_layer = None
        
        if self.side_bar is None:
            self.side_bar = SideBar(self.dlg , self)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.side_bar)

        if self.dlg.lineEdit_farmplots.text() != "":
            self.farmplots = self.dlg.lineEdit_farmplots.text()
        
        if self.dlg.lineEdit_survey_georef.text() != "":
            self.survey_georef = self.dlg.lineEdit_survey_georef.text()
        else :
            self.survey_georef = "survey_georeferenced"

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
            
        
        # When the layers are removed from QGIS canvas clean_up function is called
        QgsProject.instance().layerWillBeRemoved.connect(self.clean_up)
        
        
    def load_layers(self):
        '''
        This function is used to load the layers on the QGIS canvas
        '''
        
        village = self.village
        map = self.farmplots
        print("Loading Farmplots")
        layer = QgsVectorLayer(
                        f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                        f"{map}",
                        "postgres"
                    )
        if not layer.isValid():
            print(f"Layer {map} failed to load!")
            # Message box to show that the layer failed to load
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer {map} failed to load!")
            msg.setWindowTitle("Failed")
            msg.exec_()
        else :
            # Load farmplots layer in desired color, opacity and symbology
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
        if '_editing' in map:
            if check_table_exists(self.psql_conn, village, map) == False:
                self.map = map.replace('_editing', '')
                map = self.map
                self.logs_first_time = True
            
        else :
            self.logs_first_time = True
        
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_temp",
            "postgres"
        )

        if not original_layer.isValid():
            print(f"Layer {map} failed to load!")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer {map} failed to load!")
            msg.setWindowTitle("Failed")
            msg.exec_()
        else:
            # Create a temporary copy of the layer to store the original layer so that the original layer
            # is not modified while editing the map
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
            
        
        # Create topology of the map which is to be edited
        print("Creating Topo")
        self.topo_name = f"{village}_{map}_topo_new"
        create_topo(self.psql_conn, self.village, self.topo_name, self.map)
        
        # Create corner nodes for the map which is to be edited
        print("Creating Corner Nodes")
        self.corner_nodes = f"corner_nodes_{self.map}"
        get_corner_nodes(self.psql_conn, self.topo_name, self.village, self.corner_nodes)
        
        # Create all nodes for the map which is to be edited
        print("Creating All Nodes")
        self.all_nodes = f"all_nodes_{self.map}"
        copy_table(self.psql_conn, f"{self.topo_name}.node", f"{self.village}.{self.all_nodes}")
        
        # Adding node_id column as Primary Key to corner nodes map so that
        # its geometry can be updated dynamically
        sql = f'''
                ALTER TABLE {self.village}.{self.corner_nodes}
                ADD CONSTRAINT pk_{self.corner_nodes} PRIMARY KEY (node_id);
        
            '''
        with self.psql_conn.connection().cursor() as curr:
            curr.execute(sql)
        
        sql = f'''
                ALTER TABLE {self.village}.{self.all_nodes}
                ADD CONSTRAINT pk_{self.all_nodes} PRIMARY KEY (node_id);
        
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
            print(f"Layer {map} failed to load!")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer {map} failed to load!")
            msg.setWindowTitle("Failed")
            msg.exec_()
        else:
            self.corner_nodes_layer = original_layer
            # QgsProject.instance().addMapLayer(self.corner_nodes_layer)
        
        map = self.all_nodes
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='node_id' srid=32643 type=Point table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_editing",
            "postgres"
        )
        if not original_layer.isValid():
            print(f"Layer {map} failed to load!")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer {map} failed to load!")
            msg.setWindowTitle("Failed")
            msg.exec_()
        else:
            self.all_nodes_layer = original_layer
            # QgsProject.instance().addMapLayer(self.all_nodes_layer)
        
        self.corners()
        
        # Load farm corner nodes (used to re-calculate attribute farm_rating_nodes
        # after moving the vertesx) layer on the QGIS canvas
        if self.dlg.lineEdit_farm_nodes.text() != "":
            map = self.dlg.lineEdit_farm_nodes.text()       
        else :
            map = "farm_corner_nodes"
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='node_id' srid=32643 type=Point table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_temp",
            "postgres"
        )

        if not original_layer.isValid():
            print(f"Layer {map} failed to load!")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer {map} failed to load!")
            msg.setWindowTitle("Failed")
            msg.exec_()
        else:
            self.farm_corner_nodes = original_layer
        
        map = self.survey_georef
        original_layer = QgsVectorLayer(
            f"dbname='{psql['database']}' host={psql['host']} port={psql['port']} user='{psql['user']}' password='{psql['password']}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
            f"{village}.{map}_temp",
            "postgres"
        )
        if not original_layer.isValid():
            print(f"Layer {map} failed to load!")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer {map} failed to load!")
            msg.setWindowTitle("Failed")
            msg.exec_()
        else:
            self.survey_georef_layer = original_layer
        
    
    def select_vertex(self):
        '''
        This function is used to select the vertex on the map.
        It unsets the current map tool, clears any existing vertex highlights,
        removes any other highlights, and sets the map tool to the vertex selector (more details inside map_tools.py). 
        It is called when the user clicks on the 'Select Vertex' button in the side bar
        '''
        self.canvas.unsetMapTool(self.mover)
        if self.vertexselector is not None:
            self.vertexselector.clearHighlight()
        
        self.RemoveHighlight()
        self.canvas.setMapTool(self.vertexselector)
        
    def after_selection(self):
        '''
        This function is called after the user selects a vertex on the map.
        It clears the highlight of the vertex selector, unsets the map tool of the vertex selector,
        and sets the map tool to the mover (more details inside map_tools.py).
        '''
        print("AFTER SELECTION CALLED !!!!!!!!!!!!!!!!!!")
        if self.mover is not None:
            self.mover.clearHighlight()
        self.canvas.unsetMapTool(self.vertexselector)
        
        print("Selected Vertex : ", self.vertexselector.selected_vertex)
        features = self.layer.getFeatures()
        self.ids_to_select = []
        self.features_of_concern = []
        
        # Find the features which contain the selected vertex
        for feature in features:
            geom = feature.geometry()
            for vertex in geom.vertices():
                if QgsPointXY(vertex.x(), vertex.y()) == self.vertexselector.selected_vertex:
                    self.ids_to_select.append(feature.id())
                    self.features_of_concern.append(feature)
                    break
        
        print("Selected Features : ", self.ids_to_select)

        # This function is used to find and highlight the pivots / corners in yellow and
        # the vertices between the selected vertex and the pivots in green 
        self.neighbour_vertices()

        # After highlighting the pivots and vertices between selected vertex and pivots
        # we are ready to move, so set the map tool to the mover
        self.move_vertex()
        
    def move_vertex(self):
        '''
        This function is used to move the selected vertex on the map.
        It sets the map tool to the mover (more details inside map_tools.py).
        '''
        self.canvas.setMapTool(self.mover)
        
    def after_new_vertex(self):
        '''
        This function is called after user selects a new vertex on the map.
        It unsets the map tool of the mover
        '''
        print("AFTER NEW VERTEX CALLED !!!!!!!!!!!!!!!!!!")
        self.canvas.unsetMapTool(self.mover)
        
        # Update the corner nodes layer (e.g. corner_nodes_jitter_spline_output_regularised_03)
        # and all nodes layer (e.g. all_nodes_jitter_spline_output_regularised_03) with the new vertex
        self.update_map_nodes_layer(self.vertexselector.selected_vertex, self.mover.newvertex, self.corner_nodes_layer)
        self.update_map_nodes_layer(self.vertexselector.selected_vertex, self.mover.newvertex, self.all_nodes_layer)
        
        old_x = self.vertexselector.selected_vertex.x()
        old_y = self.vertexselector.selected_vertex.y()
        new_x = self.mover.newvertex.x()
        new_y = self.mover.newvertex.y()
        
        # Add the changes to the logs list
        self.logs.append((self.node_id, old_x, old_y, new_x, new_y))
        
        self.layer.startEditing()
        
        # For undo operation append all the movements to these
        self.history_new_vertices.append(self.mover.newvertex)
        self.history_old_vertices.append(self.vertexselector.selected_vertex)
        transformed_vertices = []
        
        # Iterate over the features / polygons which contain the selected vertex 
        for feature in self.features_of_concern:
            geom = feature.geometry()
            # list of new points to create new geometry of polygon after moving the vertex
            new_vertices = []
            for vertex in geom.vertices():
                # If the vertex is old_vertex (selected to move) append new_vertex to list
                if QgsPointXY(vertex.x(), vertex.y()) == self.vertexselector.selected_vertex:
                    if self.is_corner.get((vertex.x(), vertex.y())) is not None:
                        self.is_corner[(self.mover.newvertex.x(), self.mover.newvertex.y())] = True
                    new_vertices.append(QgsPointXY(self.mover.newvertex.x(), self.mover.newvertex.y()))

                # self.points_to_transform : list of pairs (point, ratio)
                # If the vertex is in list points to transform i.e. the points between selected
                # vertex and pivots then append the point after transformation
                elif self.is_present_as_first(vertex, self.points_to_transform):
                    ratio = None
                    for point in self.points_to_transform:
                        if point[0] == vertex:
                            ratio = point[1]
                            break
                    transformed_vertex = self.transform(self.vertexselector.selected_vertex, self.mover.newvertex, (QgsPointXY(vertex.x(), vertex.y()), ratio))
                    new_vertices.append(transformed_vertex)
                    transformed_vertices.append((transformed_vertex, ratio))
                    self.update_map_nodes_layer(vertex, transformed_vertex, self.all_nodes_layer)

                # else just append the vertex as it is
                else:
                    new_vertices.append(QgsPointXY(vertex.x(), vertex.y()))
            
            # Update the geometry of the feature
            new_geom = QgsGeometry.fromPolygonXY([new_vertices])
            feature.setGeometry(new_geom)
            # Recalculate and update all the attributes of the feature according to this new geom 
            self.update_attributes(feature)
            self.layer.updateFeature(feature)
        
        self.history_transformed_vertices.append(transformed_vertices)        
        self.layer.commitChanges()
        self.canvas.refresh()
        self.display_rating(self.layer, self.param_selected)
        self.select_vertex()
    
    
    def clean_up(self, layer_id):
        '''
        This function is called when the layer is removed from the QGIS canvas.
        It is used to unset the map tools, clear the highlights, remove the side bar and
        delete the side bar object.
        '''
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
        '''
        :param layer: The layer on which the labels are to be displayed
        :type layer: QgsVectorLayer

        :param field: The field whose values are to be displayed as labels
        :type field: str

        This function is used to display the field for each polygon on the map layer.
        It is called when the user selects a parameter to display from the side bar.
        '''
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
        '''
        This function is used to undo the last movement of the vertex.
        It is called when the user clicks on the 'Undo' button in the side bar.
        '''
        
        if len(self.history_old_vertices) == 0:
            return

        self.RemoveHighlight()
        self.vertexselector.clearHighlight()
        self.mover.clearHighlight()
        
        print("Undoing")
        print(len(self.history_old_vertices), len(self.history_new_vertices))
        # Get the old vertex, new vertex and transformed vertices from the history lists
        old_vertex = self.history_old_vertices.pop()
        new_vertex = self.history_new_vertices.pop()
        transformed_vertices = self.history_transformed_vertices.pop()
        print("TRANSFORMED VERTICES : ")
        print(transformed_vertices)
        
        # Update the corner nodes layer and all nodes layer with the old vertex
        self.update_map_nodes_layer(new_vertex, old_vertex, self.corner_nodes_layer)
        self.update_map_nodes_layer(new_vertex, old_vertex, self.all_nodes_layer)
        
        # Add the changes to the logs list
        self.logs.append((self.node_id, new_vertex.x(), new_vertex.y(), old_vertex.x(), old_vertex.y()))
        
        # Just highlighting transformed vertices
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
        
        # Iterate over the features / polygons which contain the undo operation vertex
        # Almost similar to the after_new_vertex function
        for feature in features_changing:
            geom = feature.geometry()
            new_vertices = []
            for vertex in geom.vertices():
                # If the vertex is new_vertex then append old_vertex to list
                if QgsPointXY(vertex.x(), vertex.y()) == new_vertex:
                    new_vertices.append(QgsPointXY(old_vertex.x(), old_vertex.y()))
                
                # If the vertex is in transformed_vertices then append the vertex after reverse transformation
                elif self.is_present_as_first(vertex, transformed_vertices):
                    print("UNDOING ON TRANSFORMED VERTICES ")
                    ratio = None
                    point_needed = QgsPointXY(vertex.x(), vertex.y())
                    for point in transformed_vertices:
                        point_xy = QgsPointXY(point[0].x(), point[0].y())
                        if point_xy.x() == point_needed.x() and point_xy.y() == point_needed.y():
                            ratio = point[1]
                            break
                    transformed_vertex = self.transform(new_vertex, old_vertex, (QgsPointXY(vertex.x(), vertex.y()), ratio))
                    new_vertices.append(transformed_vertex)
                    self.update_map_nodes_layer(vertex, transformed_vertex, self.all_nodes_layer)

                else:
                    new_vertices.append(QgsPointXY(vertex.x(), vertex.y()))
            
            new_geom = QgsGeometry.fromPolygonXY([new_vertices])
            feature.setGeometry(new_geom)
            self.update_attributes(feature)
            self.layer.updateFeature(feature)
        
        self.layer.commitChanges()
        self.canvas.refresh()
        self.display_rating(self.layer, self.param_selected)

    def update_map_nodes_layer(self, old_vertex, new_vertex, nodes_map_layer):
        '''
        :param old_vertex: The old vertex which is to be updated
        :type old_vertex: QgsPointXY

        :param new_vertex: The new vertex which is to be updated
        :type new_vertex: QgsPointXY

        :param nodes_map_layer: The layer on which the vertex is to be updated
        :type nodes_map_layer: QgsVectorLayer

        This function is used to update the corner nodes layer and all nodes layer with the new vertex
        after the vertex is moved.
        '''
        
        old_vertex_xy = QgsPointXY(old_vertex.x(), old_vertex.y())
        new_vertex_xy = QgsPointXY(new_vertex.x(), new_vertex.y())
        nodes_map_layer.startEditing()
        print("updating corner nodes layer")
        for feature in nodes_map_layer.getFeatures():
            point = feature.geometry().asPoint()
            vertex_xy = QgsPointXY(point.x(), point.y())
            if vertex_xy.x() == old_vertex_xy.x() and vertex_xy.y() == old_vertex_xy.y():
                print("Got corresponding corner node")
                new_geom = QgsGeometry.fromPointXY(new_vertex_xy)
                self.node_id = feature['node_id']
                feature.setGeometry(new_geom)
                nodes_map_layer.updateFeature(feature)
                break
                
        nodes_map_layer.commitChanges()
        nodes_map_layer.triggerRepaint()
        self.canvas.refresh()
            
    
    
    
    def update_attributes(self, feature):
        '''
        :param feature: The feature whose attributes are to be updated
        :type feature: QgsFeature
        
        This function is used to update the attributes of the feature after the vertex is moved.
        The functions to calculate the attributes are defined in attribute_utils.py
        '''
        
        fields = self.layer.fields()
        
        # Checking if particular field is present in the layer
        if fields.indexFromName('akarbandh_area_diff') != -1 and fields.indexFromName('akarbandh_area') != -1:
            print(fields.indexFromName('akarbandh_area_diff'))
            new_akarbandh_area_diff = calculate_akarbandh_area_diff(feature)
            feature.setAttribute('akarbandh_area_diff', new_akarbandh_area_diff)
            
        if fields.indexFromName('varp') != -1:
            new_varp = calculate_varp(feature)
            if np.isnan(new_varp) or new_varp is None or new_varp == "":
                new_varp = 1
            ind = self.layer.fields().indexFromName('varp')
            feature.setAttribute(ind, float(new_varp))        
        
        if fields.indexFromName('shape_index') != -1:
            new_shape_index = calculate_shape_index(feature)
            feature.setAttribute('shape_index', new_shape_index)
        
        if fields.indexFromName('farm_rating') != -1:           
            new_farm_rating = calculate_farm_rating(feature, self.method, self.farmplots_layer)
            feature.setAttribute('farm_rating', new_farm_rating)
        
        if fields.indexFromName('farm_intersection') != -1:
            new_farm_intersection = calculate_farm_intersection(feature, self.farmplots_layer)
            feature.setAttribute('farm_intersection', new_farm_intersection)
            
        if fields.indexFromName('farm_rating_nodes') != -1:
            new_farm_rating_nodes = calculate_farm_rating_nodes(feature, self.farm_corner_nodes, self.corner_nodes_layer)
            feature.setAttribute('farm_rating_nodes', new_farm_rating_nodes)
        
        if fields.indexFromName('excess_area') != -1:
            new_excess_area = calculate_excess_area(feature, self.farmplots_layer)
            feature.setAttribute('excess_area', new_excess_area)
        
        if fields.indexFromName('area_diff') != -1:
            new_area_diff = calculate_area_diff(feature, self.survey_georef_layer)
            feature.setAttribute('area_diff', new_area_diff)
        
        if fields.indexFromName('perimeter_diff') != -1:
            new_perimeter_diff = calculate_perimeter_diff(feature, self.survey_georef_layer)
            feature.setAttribute('perimeter_diff', new_perimeter_diff)
            
        if fields.indexFromName('deviation') != -1:
            new_deviation = calculate_deviation(feature, self.survey_georef_layer)
            feature.setAttribute('deviation', new_deviation)
        
        if fields.indexFromName('corrected_area_diff') != -1:
            new_corrected_area_diff = calculate_corrected_area_diff(feature, self.survey_georef_layer)
            feature.setAttribute('corrected_area_diff', new_corrected_area_diff)
        
    
    def generate_heatmap(self, attribute):
        '''
        :param attribute: The attribute based on which the heatmap is to be generated
        :type attribute: str
        
        This function is used to generate the heatmap for the attribute selected by the user.
        It is called when the user clicks on the 'Generate Heatmap' checkbox in the side bar.
        '''
        print("generating heatmap")
        layer = self.layer
        field = attribute
        
        # ith color is for the range (colors[i][0], colors[i+1][0])
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
        '''
        This function is used to remove the heatmap from the layer.
        '''
        print("removing heatmap")
        layer = self.layer
        symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor('#3579b1'), 'outline_width': '1'})
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()
        self.iface.layerTreeView().refreshLayerSymbology(layer.id())

    def corners(self):
        '''
        This function is used to mark the corner nodes in the map using dictionary is_corner.
        '''
        for feature in self.corner_nodes_layer.getFeatures():
            geom = feature.geometry()
            point = geom.asPoint()
            tup = (point.x(), point.y())
            self.is_corner[tup] = True
    
    def neighbour_vertices(self):
        '''
        This function is used to find nearest pivot corner nodes and the vertices between
        selected vertex and pivot corner nodes
        It also highlights pivots in yellow and corner nodes in green
        '''
        self.points_to_transform = []
        features = self.features_of_concern
        print("number of features of concern : ", len(self.features_of_concern))
        geoms = []
        
        for feature in features:
            
            vertices = feature.geometry().vertices()
            ind = 0
            # vertex_list : A list of vertices of the polygon in circular order
            vertex_list = [vertex for vertex in vertices]
            n = len(vertex_list)
            
            # First find the index of the selected vertex in the vertex_list
            for vertex in vertex_list:
                if QgsPointXY(vertex.x(), vertex.y()) == self.vertexselector.selected_vertex:
                    break
                ind += 1
            
            # Caution just taken as the first and last vertex of the polygon are same
            if ind == 0:
                i = 1 
                j = n - 2 # NOTE : not n-1
            elif ind == n-1:
                i = 1 # NOTE : not 0
                j = n - 2
            else:
                # mod n is taken to make the list circular (just realized that it is not needed :P)
                i = (ind + 1)%n
                j = (ind + n - 1)%n
            
            prev_vertex = vertex_list[ind]
            dist = 0
            corner1_dist = None
            corner2_dist = None
            corner1_ind = None
            corner2_ind = None
            
            # Find the nearest pivot corner node one direction
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
            
            # Find the nearest pivot corner node in the other direction
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
            
            # Find the vertices between selected vertex and pivot corner nodes and append them to points_to_transform list
            # Also calculate the ratio of distance of the vertex from the selected vertex to the distance of the pivot corner node
            # This ratio is used to transform the vertices between selected vertex and pivot corner nodes
            while i != corner1_ind and i != ind:
                dist += prev_vertex.distance(vertex_list[i])
                prev_vertex = vertex_list[i]
                if not self.is_present_as_first(vertex_list[i], self.points_to_transform):
                    self.points_to_transform.append((vertex_list[i], (corner1_dist - dist)/corner1_dist))
                i = (i + 1)%n
                
            prev_vertex = vertex_list[ind]
            dist = 0
            # Find the vertices between selected vertex and pivot corner nodes
            while j != corner2_ind and j != ind:                
                dist += prev_vertex.distance(vertex_list[j])
                prev_vertex = vertex_list[j]
                if not self.is_present_as_first(vertex_list[j], self.points_to_transform):
                    self.points_to_transform.append((vertex_list[j], (corner2_dist - dist)/ corner2_dist))
                j = (j + n - 1)%n
                
            print("neighbours : ", len(geoms))
            
        # Just highlighting
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
        # Remove all the highlights / rubberband objects from the map
        for rb in self.rubber_bands:
            self.canvas.scene().removeItem(rb)
            del rb
        self.rubber_bands = []

    def transform(self, old_vertex, new_vertex, point_and_ratio):
        '''
        :param old_vertex: The old vertex which is to be updated
        :type old_vertex: QgsPointXY

        :param new_vertex: The new vertex which is to be updated
        :type new_vertex: QgsPointXY

        :param point_and_ratio: A pair of point and ratio
        :type point_and_ratio: Tuple(QgsPointXY, float)

        This function is used to transform the vertices between selected vertex and pivot corner nodes
        using the ratio of distance of the vertex from the selected vertex to the distance of the pivot corner node
        from the selected vertex measured along the boundary of the polygon.
        '''
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
        '''
        :param element: The element to be checked
        :type element: QgsPointXY
        
        :param list: The list in which the element is to be checked
        :type list: List(Tuple(QgsPointXY, float))
        
        This function is used to check if the element is present as the first element in the list of pairs (Just helper function)
        '''
        
        point_xy = QgsPointXY(element.x(), element.y())
        for sublist in list:
            point_xy_2 = QgsPointXY(sublist[0].x(), sublist[0].y())
            if point_xy.x() == point_xy_2.x() and point_xy.y() == point_xy_2.y():
                return True
        return False
    
    def deactivate(self):
        '''
        This function is used to deactivate the editing mode.
        '''
        if self.vertexselector is not None:
            self.vertexselector.clearHighlight()
        if self.mover is not None:
            self.mover.clearHighlight()
        self.canvas.unsetMapTool(self.vertexselector)
        self.canvas.unsetMapTool(self.mover)
        self.RemoveHighlight()
        
    def save_layer_postgres(self):
        '''
        This function is used to save the edited layer to the Postgres database.
        It is called when the user clicks on the 'Save to postgres' button in the side bar.
        '''
        schema = self.village

        # If the map is already the one edited then update the same map else
        # if started editing original map then create a new map with _editing suffix
        if 'editing' in self.map:
            table_name = self.map
        else:
            table_name = f"{self.map}_editing"
        drop_table(self.psql_conn, schema, table_name)
        uri = QgsDataSourceUri()
        uri.setConnection(psql['host'], psql['port'], psql['database'], psql['user'], psql['password'])
        uri.setDataSource(schema, table_name, "geom")
        err = QgsVectorLayerExporter.exportLayer(self.layer, uri.uri(), "postgres", QgsCoordinateReferenceSystem(), False)

        # If logs_first_time is True then create a new logs table else update the logs table
        print("Is logs first time ", self.logs_first_time)
        if '_editing' in self.map:
            mapp = self.map.replace('_editing', '')
        else :
            mapp = self.map
        logs_name = f"{mapp}_logs"
        if self.logs_first_time:
            drop_table(self.psql_conn, schema, logs_name)
            create_logs_table(self.psql_conn, schema, logs_name)
            
        if err[0] != QgsVectorLayerExporter.NoError:
            print("Error when saving layer to Postgres: ", err)
        else:
            print("Layer saved successfully")  
            print("Updating logs")
            # Insert all the logs in the logs table (See psql.py for more details)
            for log in self.logs:
                node_id = log[0]
                old_x = log[1]
                old_y = log[2]
                new_x = log[3]
                new_y = log[4]
                insert_log(self.psql_conn, schema, logs_name, node_id, old_x, old_y, new_x, new_y)
                
            self.logs_first_time = False
            self.logs = []
                            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Layer saved successfully\nYou will be able to see the layer named {table_name} in schema {schema}")
            msg.setWindowTitle("Success")
            msg.exec_()
            
        
        
    def run(self):
        '''
        This function is used to run the plugin.
        It is called from mover2.py when the user clicks on the 'OK' button in the dialog box.'''
        self.initiate()
        self.load_layers()
        
    