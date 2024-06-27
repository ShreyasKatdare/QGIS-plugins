from qgis.PyQt.QtCore import QVariant
import numpy as np
from qgis.core import QgsPointXY, QgsWkbTypes
from qgis.gui import QgsRubberBand
from qgis.PyQt import QtGui

def calculate_akarbandh_area_diff(feature):
    '''
    :param feature: QgsFeature
    Calculate the difference between the area of the feature and the akarbandh area.
    NOTE : The attribute named 'akarbandh_area' should be present in the feature.
    '''
    
    akarbandh_area = feature.attribute('akarbandh_area')

    if not (isinstance(akarbandh_area, float) or isinstance(akarbandh_area, int)):
        return None
    
    return (feature.geometry().area()/10000 - akarbandh_area)/akarbandh_area
    
def calculate_varp(feature):
    '''
    :param feature: QgsFeature
    Calculates the varp of the feature.
    '''

    geom = feature.geometry()
    points_list = [vertex for vertex in geom.vertices()]

    points = points_list
    points.append(points_list[1])
    sum = 0
    for i in range(len(points)-2):
        a = np.array([float(points[i].x()), float(points[i].y())])
        b = np.array([float(points[i+1].x()), float(points[i+1].y())])
        c = np.array([float(points[i+2].x()), float(points[i+2].y())])

        ba = b - a
        bc = c - b
        if (np.linalg.norm(ba) * np.linalg.norm(bc)) == 0 or np.dot(ba, bc)==0:
            continue
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        angle = np.arccos(min(cosine_angle,1))
        sum += abs(angle)

    varp = sum/(2*np.pi)
    if np.isnan(varp) or varp == "":
        return 1
    return varp

def calculate_shape_index(feature):
    '''
    :param feature: QgsFeature
    Calculates the shape index of the feature using the formula (perimeter^2)/area.
    '''
    return (feature.geometry().length() * feature.geometry().length()) / feature.geometry().area()

def calculate_farm_rating(feature, method, farmplots_layer):
    '''
    :param feature: QgsFeature
    :param method: str
    :param farmplots_layer: QgsVectorLayer
    Calculates the farm rating of the feature using the method specified with the farmplots_layer.
    '''
    
    if method == 'all_avg':
        geom_a = feature.geometry()
        ratings = []
        features = farmplots_layer.getFeatures()
        for farmplot_feature in features:
            geom_b = farmplot_feature.geometry()
            if geom_b.area() <= 0.05 * geom_a.area():
                continue
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
        features = farmplots_layer.getFeatures()
        for farmplot_feature in features:
            geom_b = farmplot_feature.geometry()
            if geom_b.area() <= 0.05 * geom_a.area():
                continue
            if geom_a.buffer(20, 5).intersects(geom_b):
                intersection = geom_a.intersection(geom_b)
                difference = geom_b.difference(geom_a)

                intersection_area = intersection.area()
                difference_area = difference.area()
                geom_b_area = geom_b.area()

                rating = max(intersection_area, difference_area) / geom_b_area
                ratings.append(rating)

        if ratings:
            if len(ratings) == 2:
                return sum(ratings) / 2
            if len(ratings) == 1:
                return ratings[0]
            ratings.sort()
            return sum(ratings[:3]) / 3
        else:
            return 0.0

def calculate_farm_intersection(feature, farmplots_layer):
    '''
    :param feature: The feature for which to calculate the farm intersection.
    :type feature: QgsFeature

    :param farmplots_layer: The farmplots layer to compare with.
    :type farmplots_layer: QgsVectorLayer

    :return: The ratio of the intersection area to the area of the feature.
    :rtype: float

    Calculates the intersection area of the feature with the farmplots_layer and
    returns the ratio of the intersection area to the area of the feature.
    '''

    geom_a = feature.geometry()
    intersection_area = 0
    features = farmplots_layer.getFeatures()
    for farmplot_feature in features:
        geom_b = farmplot_feature.geometry()
        intersection_area += geom_a.intersection(geom_b).area()
        
    return intersection_area / geom_a.area()
    

def calculate_farm_rating_nodes(feature, farm_topo_nodes, map_corner_nodes):
    '''
    :param feature: The feature for which to calculate the farm_rating_nodes.
    :type feature: QgsFeature

    :param farm_topo_nodes: The layer having the nodes of farmplots.
    :type farm_topo_nodes: QgsVectorLayer

    :param map_corner_nodes: The layer having the corner nodes of the editing map(e.g. jitter_spline_output_regularised_03).
    
    Calculates the farm_rating_nodes of the feature using the farm_topo_nodes and map_corner_nodes.
    
    '''
    
    farm_nodes = farm_topo_nodes.getFeatures()
    farm_nodes = list(farm_nodes)
    farm_rating_node = 0
    i = 0
    near_farm_nodes = []
    buffer_outside = feature.geometry().buffer(40, 5)
    buffer_inside = feature.geometry().buffer(-40, 5)    
    buffer = buffer_outside.difference(buffer_inside)
    
    for farm_node in farm_nodes:
        if buffer.intersects(farm_node.geometry()):
            near_farm_nodes.append(farm_node)
    
    is_vertex = {}
    for vertex in feature.geometry().vertices():
        vertex_xy = QgsPointXY(vertex.x(), vertex.y())
        tup = (vertex_xy.x(), vertex_xy.y())
        is_vertex[tup] = True
    
    for vertex in map_corner_nodes.getFeatures():
        point = vertex.geometry().asPoint()
        vertex_xy = QgsPointXY(point.x(), point.y())
        tup = (vertex_xy.x(), vertex_xy.y())
        if is_vertex.get(tup) is not None:
            dist = float('inf')
            for farm_node in near_farm_nodes:
                node = farm_node.geometry().asPoint()
                node_xy = QgsPointXY(node.x(), node.y())
                dist = min(dist, vertex_xy.distance(node_xy))
            if dist > 40:
                continue
            i += 1
            farm_rating_node += dist
            
    return farm_rating_node / i 


def calculate_excess_area(feature, farmplots_layer):
    '''
    :param feature: The feature for which to calculate the excess area.
    :type feature: QgsFeature

    :param farmplots_layer: The farmplots layer to compare with.
    :type farmplots_layer: QgsVectorLayer

    :return: The excess area of the feature.
    :rtype: float
    
    Calculates the percentage excess area of a given feature with respect to a farmplots layer.
    '''
    geom_a = feature.geometry()
    excess_area = 0
    features = farmplots_layer.getFeatures()
    for farmplot_feature in features:
        geom_b = farmplot_feature.geometry()
        if geom_a.buffer(20, 5).intersects(geom_b):
            intersection_area = geom_a.intersection(geom_b).area()
            difference_area = geom_b.difference(geom_a).area()
            excess_area += min(intersection_area, difference_area)
            
    return excess_area / geom_a.area()

def calculate_area_diff(feature, survey_georeferenced_map):
    '''
    :param feature: The feature for which to calculate the area difference.
    :type feature: QgsFeature

    :param survey_georeferenced_map: The survey georeferenced map layer.
    :type survey_georeferenced_map: QgsVectorLayer

    :return: The area difference of the feature.
    :rtype: float

    Calculates the area difference of a given feature with respect to a survey georeferenced map.
    '''
    
    
    if not (isinstance(feature.attribute('area_diff'), float) or isinstance(feature.attribute('area_diff'), int)):
        return None
        
    for survey_feature in survey_georeferenced_map.getFeatures():
        if survey_feature.attribute('gid') == feature.attribute('gid'):
            return (feature.geometry().area() - survey_feature.geometry().area()) / survey_feature.geometry().area()
    return None
    
def calculate_perimeter_diff(feature, survey_georeferenced_map):
    '''
    :param feature: The feature for which to calculate the perimeter difference.
    :type feature: QgsFeature

    :param survey_georeferenced_map: The survey georeferenced map layer.
    :type survey_georeferenced_map: QgsVectorLayer

    :return: The perimeter difference of the feature.
    :rtype: float

    Calculates the perimeter difference of a given feature with respect to a survey georeferenced map.

    '''
    
    
    if not (isinstance(feature.attribute('perimeter_diff'), float) or isinstance(feature.attribute('perimeter_diff'), int)):
        return None
        
    for survey_feature in survey_georeferenced_map.getFeatures():
        if survey_feature.attribute('gid') == feature.attribute('gid'):
            return (feature.geometry().length() - survey_feature.geometry().length()) / survey_feature.geometry().length()
    return None

def calculate_deviation(feature, survey_georeferenced_map):
    '''
    :param feature: The feature for which to calculate the deviation.
    :type feature: QgsFeature

    :param survey_georeferenced_map: The survey georeferenced map layer.
    :type survey_georeferenced_map: QgsVectorLayer

    :return: The deviation of the feature.
    :rtype: float

    Calculates the deviation of a given feature with respect to a survey georeferenced map.
    '''
    
    if not (isinstance(feature.attribute('deviation'), float) or isinstance(feature.attribute('deviation'), int)):
        return None
    
    survey_feature = None
    for fea in survey_georeferenced_map.getFeatures():
        if fea.attribute('gid') == feature.attribute('gid'):
            survey_feature = fea
            break
    
    if survey_feature is None:
        return None
    
    survey_geom = survey_feature.geometry()
    feature_geom = feature.geometry()
    
    survey_centroid = survey_geom.centroid().asPoint()
    feature_centroid = feature_geom.centroid().asPoint()
    dx = feature_centroid.x() - survey_centroid.x()
    dy = feature_centroid.y() - survey_centroid.y()
    
    survey_geom.translate(dx, dy)
    
    diff_area1 = survey_geom.difference(feature_geom).area()
    diff_area2 = feature_geom.difference(survey_geom).area()
    
    return (diff_area1 + diff_area2) / (2*survey_geom.area())
    
    
def calculate_corrected_area_diff(feature, survey_georeferenced_map):
    '''
    :param feature: The feature for which to calculate the corrected area difference.
    :type feature: QgsFeature

    :param survey_georeferenced_map: The survey georeferenced map layer.
    :type survey_georeferenced_map: QgsVectorLayer

    :return: The corrected area difference of the feature.
    :rtype: float

    Calculates the corrected area difference of a given feature with respect to a survey georeferenced map.
    '''
    
    if not isinstance(feature.attribute('corrected_area_diff'), float) or isinstance(feature.attribute('corrected_area_diff'), int):
        return None
    for survey_feature in survey_georeferenced_map.getFeatures():
        if survey_feature.attribute('survey_no') == feature.attribute('survey_no') and survey_feature.attribute('corrected_area') is not None and survey_feature.attribute('corrected_area') > 0:
            return (feature.geometry().area() - survey_feature.attribute('corrected_area')) / survey_feature.attribute('corrected_area')
    
    return None


