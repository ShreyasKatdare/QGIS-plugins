from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsGeometry, QgsPointXY

# QgsMapTool is a class that is used to create custom map tools in QGIS
# QgsRubberBand is a class that is used to draw / highlight temporary geometries on the map canvas


class VertexSelector(QgsMapTool):
    '''
    This class is used to select a vertex from a layer
    '''
    def __init__(self, canvas, layer, parent):
        '''
        Constructor
        :param canvas: The map canvas
        :type canvas: QgsMapCanvas
        
        :param layer: The layer to select the vertex from
        :type layer: QgsVectorLayer

        :param parent: The parent widget, here parent is instance of main class which is
                       present in main.py so that we can call the functions of main class
        
        '''
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.parent = parent
        self.selected_vertex = None
        self.highlighted_vertex = None
        self.rubber_bands = []

    def canvasMoveEvent(self, event):
        '''
        This function is called when the mouse is moved on the canvas
        :param event: The event object
        :type event: QMouseEvent

        The closest vertex to the mouse pointer will be highlighted in red
        '''
        # Get the point where the mouse is moved
        point = self.toMapCoordinates(event.pos())
        closest_vertex = self.findClosestVertex(point)
        if closest_vertex:
            if closest_vertex != self.highlighted_vertex:
                self.highlightVertex(closest_vertex)
                self.highlighted_vertex = closest_vertex
        else:
            self.clearHighlight()

    def canvasPressEvent(self, event):
        '''
        This function is called when the mouse is pressed on the canvas
        :param event: The event object
        :type event: QMouseEvent
        '''
        if self.highlighted_vertex:   
            self.selected_vertex = self.highlighted_vertex
            self.parent.after_selection()
    
    def findClosestVertex(self, point):
        '''
        This function is used to find the closest vertex to the given point
        :param point: The point for which the closest vertex is to be found
        :type point: QgsPointXY
        '''
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
        '''
        This function is used to highlight the given vertex
        :param vertex: The vertex to highlight
        :type vertex: QgsPointXY
        '''
        
        self.clearHighlight()
        rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        rubberBand.setToGeometry(QgsGeometry.fromPointXY(vertex), self.layer)
        rubberBand.setColor(Qt.red)
        rubberBand.setWidth(10)
        self.rubber_bands.append(rubberBand)

    def clearHighlight(self):
        '''
        This function is used to clear the highlighted vertex
        '''
        
        for rb in self.rubber_bands:
            self.canvas.scene().removeItem(rb)
            del rb
        self.rubber_bands = []
        self.highlighted_vertex = None
        
#_______________________________________________________________________________________________________________________


class NewVertex(QgsMapTool):
    '''
    This class is used to select a new vertex where the old vertex is to be moved on canvas
    '''
    
    def __init__(self, canvas, layer, parent):
        '''
        Constructor
        :param canvas: The map canvas
        :type canvas: QgsMapCanvas
        
        :param layer: The layer to select the vertex from
        :type layer: QgsVectorLayer

        :param parent: The parent widget, here parent is instance of main class which is
                          present in main.py so that we can call the functions of main class
        
        '''
        
        super().__init__(canvas)
        self.canvas = canvas
        self.parent = parent
        self.layer = layer
        self.newvertex = None
        self.rbs = []
        self.clearHighlight()
        
    def canvasPressEvent(self, event):
        '''
        This function is called when the mouse is pressed on the canvas
        :param event: The event object
        :type event: QMouseEvent
        
        If the right mouse button is pressed, the highlight is cleared and the vertex selection tool is activated
        If the left mouse button is pressed, a new vertex is selected and highlighted in blue
        '''
        
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
        '''
        This function is used to clear the highlighted vertex
        '''
        for rb in self.rbs:
            self.canvas.scene().removeItem(rb)
            del rb
        self.rbs = []
        self.newvertex = None
       

#_______________________________________________________________________________________________________________________
