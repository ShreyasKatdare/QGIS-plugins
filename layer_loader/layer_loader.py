# -*- coding: utf-8 -*-
"""
/***************************************************************************
 layer_loader
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
import random
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .layer_loader_dialog import *
import os.path
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
    QgsRuleBasedRenderer,
    QgsGradientColorRamp,
    QgsMarkerSymbol
)
from qgis.gui import QgsMapCanvasAnnotationItem
from qgis.gui import QgsMapToolEmitPoint
from PyQt5.QtGui import QColor, QTextDocument, QFont
from PyQt5.QtCore import QSizeF, QPointF
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QCheckBox, QDockWidget, QWidget, QFormLayout

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


class layer_loader:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'layer_loader_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&layer_loader')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('layer_loader', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/layer_loader/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'layer_loader'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&layer_loader'),
                action)
            self.iface.removeToolBarIcon(action)


    def load_layers(self, map, symbology, opacity, color, size):
        '''
        :param map: Name of the layer to be loaded
        :type map: str

        :param symbology: Symbology of the layer to be loaded
        :type symbology: str

        :param opacity: Opacity of the layer to be loaded
        :type opacity: float

        :param color: Color of the layer to be loaded
        :type color: str

        :param size: Size of the layer to be loaded
        :type size: float

        Function to load layers in QGIS
        '''
        
        village = self.village
        
        if symbology == 'simple_fill':
            layer = QgsVectorLayer(
                            f"dbname='{self.database}' host={self.host} port={self.port} user='{self.user}' password='{self.password}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                            f"{map}",
                            "postgres"
                        )
            if not layer.isValid():
                print(f"Layer {map} failed to load!")
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(f"Layer {map} failed to load!")
                msg.setWindowTitle("Failed")
                msg.exec_()
            else :
                
                symbol = QgsFillSymbol.createSimple({'color': QColor(color)})
                symbol.setOpacity(opacity)
                renderer = QgsSingleSymbolRenderer(symbol)
                layer.setRenderer(renderer)
                layer.triggerRepaint()
                QgsProject.instance().addMapLayer(layer)

        elif symbology == 'outline':
            layer = QgsVectorLayer(
                            f"dbname='{self.database}' host={self.host} port={self.port} user='{self.user}' password='{self.password}' sslmode=disable key='unique_id' srid=32643 type=Polygon table=\"{village}\".\"{map}\" (geom)",
                            f"{map}",
                            "postgres"
                        )
            if not layer.isValid():
                print(f"Layer {map} failed to load!")
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(f"Layer {map} failed to load!")
                msg.setWindowTitle("Failed")
                msg.exec_()
            else :
                symbol = QgsFillSymbol.createSimple({'color': QColor(0,0,0,0), 'outline_color': QColor(color), 'outline_width': size})
                symbol.setOpacity(opacity)
                renderer = QgsSingleSymbolRenderer(symbol)
                layer.setRenderer(renderer)
                layer.triggerRepaint()
                QgsProject.instance().addMapLayer(layer)
            
        elif symbology == 'circle' or symbology == 'diamond' or symbology == 'triangle':
            layer = QgsVectorLayer(
                            f"dbname='{self.database}' host={self.host} port={self.port} user='{self.user}' password='{self.password}' sslmode=disable key='unique_id' srid=32643 type=Point table=\"{village}\".\"{map}\" (geom)",
                            f"{map}",
                            "postgres"
                        )
            if not layer.isValid():
                print(f"Layer {map} failed to load!")
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setText(f"Layer {map} failed to load!")
                msg.setWindowTitle("Failed")
                msg.exec_()
            else :
                symbol = QgsMarkerSymbol.createSimple({'name': symbology, 'color': QColor(color), 'size': size})
                symbol.setOpacity(opacity)
                renderer = QgsSingleSymbolRenderer(symbol)
                layer.setRenderer(renderer)
                layer.triggerRepaint()
                QgsProject.instance().addMapLayer(layer)
        
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setText(f"Wrong / No symbology selected for layer {map}!")
            msg.setWindowTitle("Failed")
            msg.exec_()
            
    def run(self):
        """Run method that performs all the real work"""
        '''
        Loops through the layers and loads them in QGIS in the specified symbology
        '''
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = layer_loaderDialog()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            
            self.layers = []
            self.village = self.dlg.village_name.text()
            self.user = self.dlg.lineEdit_user.text()
            self.database = self.dlg.lineEdit_database.text()
            self.password = self.dlg.line_Edit_password.text()
            self.host = self.dlg.lineEdit_host.text()
            self.port = self.dlg.lineEdit_port.text()
            
            # get the layers from the dialog
            for layer in self.dlg.layer_names:
                map = layer[0].text()
                symbology = layer[1].text().rsplit(' ', 1)[-1]
                opacity = layer[2].value() / 100
                color = layer[3].text()
                size = layer[4].value()
                if color == "No color":
                    # print("No color selected")
                    r = random.randint(0, 255)
                    g = random.randint(0, 255)
                    b = random.randint(0, 255)
                    color = QColor(r, g, b)
                
                self.load_layers(map, symbology, opacity, color, size)