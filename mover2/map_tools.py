from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsGeometry, QgsPointXY


class VertexSelector(QgsMapTool):
    
    def __init__(self, canvas, layer, parent):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.parent = parent
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
            self.parent.after_selection()
    
    def findClosestVertex(self, point):
        closest_vertex = None
        min_dist = float('inf')
        for feature in self.layer.getFeatures():
            geom = feature.geometry()
            for vertex in geom.vertices():
                vertex_point = QgsPointXY(vertex.x(), vertex.y())
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
            del rb
        self.rubber_bands = []
        self.highlighted_vertex = None
        
#_______________________________________________________________________________________________________________________


class NewVertex(QgsMapTool):
    def __init__(self, canvas, layer, parent):
        super().__init__(canvas)
        self.canvas = canvas
        self.parent = parent
        self.layer = layer
        self.newvertex = None
        self.rbs = []
        self.clearHighlight()
        
    def canvasPressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.clearHighlight()
            self.parent.select_vertex()
            
        else :
            self.newvertex = self.toMapCoordinates(event.pos())
            print("New Vertex : ", self.newvertex)
            rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
            rubberBand.setToGeometry(QgsGeometry.fromPointXY(self.newvertex), self.layer)
            rubberBand.setColor(Qt.blue)
            rubberBand.setWidth(10)
            self.rbs.append(rubberBand)
            self.parent.after_new_vertex()
    
    def clearHighlight(self):
        for rb in self.rbs:
            self.canvas.scene().removeItem(rb)
            del rb
        self.rbs = []
        self.newvertex = None
       

#_______________________________________________________________________________________________________________________
