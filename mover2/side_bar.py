from PyQt5.QtWidgets import QDesktopWidget, QDialog, QScrollArea, QVBoxLayout, QWidget, QCheckBox, QDockWidget, QMessageBox, QAction, QFormLayout, QLabel, QPushButton, QRadioButton, QFileDialog
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from qgis.core import QgsVectorFileWriter

class SideBar(QDockWidget):
    def __init__(self, parent, editing_session):
        super(SideBar, self).__init__(parent)
        self.editing_session = editing_session
        
        screen = QDesktopWidget().screenGeometry()
        font_size = screen.height() // 50
        
        scroll = QScrollArea(self)
        self.setWidget(scroll)
        
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        scroll.setWidgetResizable(True)
        
        form_layout = QFormLayout(content_widget)
        label1 = QLabel("Editing Tools")
        label1.setFont(QFont("Helvetica", font_size))
        label2 = QLabel("Select Parameter to display")
        label2.setFont(QFont("Helvetica", font_size))
        label3 = QLabel("Generate Heatmap")
        label3.setFont(QFont("Helvetica", font_size))
        label4 = QLabel("(use right click to deselect and reselect the point)")
        label4.setFont(QFont("Helvetica", font_size - 5))
        
        parameter1 = QRadioButton("Farm Rating")
        parameter2 = QRadioButton("Corrected Area Difference")
        parameter3 = QRadioButton("Excess Area")
        parameter4 = QRadioButton("Farm Rating Nodes")
        none_parameter = QRadioButton("None")
        
        action1 = QPushButton("Start Editing")
        action2 = QPushButton("Stop Editing")
        action1.setFont(QFont("Helvetica", font_size - 5))
        action2.setFont(QFont("Helvetica", font_size - 5))
        action1.clicked.connect(self.editing_session.select_vertex)
        action2.clicked.connect(self.editing_session.deactivate)
        
        undo = QPushButton("Undo")
        undo.setFont(QFont("Helvetica", font_size - 5))
        undo.clicked.connect(self.editing_session.undo)

        parameter1.setFont(QFont("Helvetica", font_size - 5))
        parameter2.setFont(QFont("Helvetica", font_size - 5))
        parameter3.setFont(QFont("Helvetica", font_size - 5))
        parameter4.setFont(QFont("Helvetica", font_size - 5))
        none_parameter.setFont(QFont("Helvetica", font_size - 5))
        
        parameter1.clicked.connect(lambda: self.editing_session.display_rating(self.editing_session.layer, 'farm_rating'))
        parameter2.clicked.connect(lambda: self.editing_session.display_rating(self.editing_session.layer, 'corrected_area_diff'))
        parameter3.clicked.connect(lambda: self.editing_session.display_rating(self.editing_session.layer, 'excess_area'))
        parameter4.clicked.connect(lambda: self.editing_session.display_rating(self.editing_session.layer, 'farm_rating_nodes'))
        none_parameter.clicked.connect(lambda: self.editing_session.display_rating(self.editing_session.layer, None))
    
        self.farm_rating_heatmap_button = QCheckBox("Farm rating")
        self.farm_rating_heatmap_button.setFont(QFont("Helvetica", font_size - 5))
        self.farm_rating_heatmap_button.stateChanged.connect(self.farm_rating_heatmap)
        
        self.corrected_area_diff_heatmap_button = QCheckBox("Corrected Area Difference")
        self.corrected_area_diff_heatmap_button.setFont(QFont("Helvetica", font_size - 5))
        self.corrected_area_diff_heatmap_button.stateChanged.connect(self.corrected_area_diff_heatmap)
        
        self.excess_area_heatmap_button = QCheckBox("Excess Area")
        self.excess_area_heatmap_button.setFont(QFont("Helvetica", font_size - 5))
        self.excess_area_heatmap_button.stateChanged.connect(self.excess_area_heatmap)
        
        self.farm_rating_node_heatmap_button = QCheckBox("Farm Rating Nodes")
        self.farm_rating_node_heatmap_button.setFont(QFont("Helvetica", font_size - 5))
        self.farm_rating_node_heatmap_button.stateChanged.connect(self.farm_rating_node_heatmap)
        
        self.save_button = QPushButton("Save to postgres")
        self.save_button.setFont(QFont("Helvetica", font_size - 5))
        self.save_button.clicked.connect(self.editing_session.save_layer_postgres)
                
        self.save_locally = QPushButton("Save Layer Locally")
        self.save_locally.setFont(QFont("Helvetica", font_size - 5))
        self.save_locally.clicked.connect(self.save_layer_locally)

        form_layout.addRow(label1)
        form_layout.addRow(action1)
        form_layout.addRow(label4)
        form_layout.addRow(action2)
        form_layout.addRow(undo)
        form_layout.addRow(label2)
        form_layout.addRow(parameter1)
        form_layout.addRow(parameter2)
        form_layout.addRow(parameter3)
        form_layout.addRow(parameter4)
        form_layout.addRow(none_parameter)
        form_layout.addRow(label3)
        form_layout.addRow(self.farm_rating_heatmap_button)
        form_layout.addRow(self.corrected_area_diff_heatmap_button)
        form_layout.addRow(self.excess_area_heatmap_button)
        form_layout.addRow(self.farm_rating_node_heatmap_button)
        form_layout.addRow(self.save_button)
        form_layout.addRow(self.save_locally)
        

    def farm_rating_heatmap(self, state):
        if state == Qt.Checked:
            if self.corrected_area_diff_heatmap_button.isChecked():
                self.corrected_area_diff_heatmap_button.setChecked(False)
            if self.excess_area_heatmap_button.isChecked():
                self.excess_area_heatmap_button.setChecked(False)
            if self.farm_rating_node_heatmap_button.isChecked():
                self.farm_rating_node_heatmap_button.setChecked(False)
                
            self.editing_session.generate_heatmap("farm_rating")
        else:
            self.editing_session.remove_heatmap()
            
    def corrected_area_diff_heatmap(self, state):
        if state == Qt.Checked:
            if self.farm_rating_heatmap_button.isChecked():
                self.farm_rating_heatmap_button.setChecked(False)
            if self.excess_area_heatmap_button.isChecked():
                self.excess_area_heatmap_button.setChecked(False)
            if self.farm_rating_node_heatmap_button.isChecked():
                self.farm_rating_node_heatmap_button.setChecked(False)
            self.editing_session.generate_heatmap("corrected_area_diff")
        else:
            self.editing_session.remove_heatmap()

    def excess_area_heatmap(self, state):
        if state == Qt.Checked:
            if self.farm_rating_heatmap_button.isChecked():
                self.farm_rating_heatmap_button.setChecked(False)
            if self.corrected_area_diff_heatmap_button.isChecked():
                self.corrected_area_diff_heatmap_button.setChecked(False)
            if self.farm_rating_node_heatmap_button.isChecked():
                self.farm_rating_node_heatmap_button.setChecked(False)
            self.editing_session.generate_heatmap("excess_area")
        else:
            self.editing_session.remove_heatmap()
            
    def farm_rating_node_heatmap(self, state):
        if state == Qt.Checked:
            if self.farm_rating_heatmap_button.isChecked():
                self.farm_rating_heatmap_button.setChecked(False)
            if self.corrected_area_diff_heatmap_button.isChecked():
                self.corrected_area_diff_heatmap_button.setChecked(False)
            if self.excess_area_heatmap_button.isChecked():
                self.excess_area_heatmap_button.setChecked(False)
            self.editing_session.generate_heatmap("farm_rating_nodes")
        else:
            self.editing_session.remove_heatmap()

    def save_layer_locally(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Layer", "", "Shapefile (*.shp);;GeoJSON (*.geojson)")
        print("file_name : ", file_name)
        if file_name:
            writer = QgsVectorFileWriter.writeAsVectorFormat(self.editing_session.layer, file_name, "UTF-8", self.editing_session.layer.crs(), "ESRI Shapefile")
            if writer == QgsVectorFileWriter.NoError:
                print("Layer saved successfully")
            else:
                print("Error when saving layer: ", writer)