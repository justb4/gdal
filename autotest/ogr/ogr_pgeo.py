#!/usr/bin/env pytest
# -*- coding: utf-8 -*-
###############################################################################
# $Id$
#
# Project:  GDAL/OGR Test Suite
# Purpose:  Test read functionality for OGR PGEO driver.
# Author:   Even Rouault <even dot rouault at spatialys.com>
#
###############################################################################
# Copyright (c) 2010-2012, Even Rouault <even dot rouault at spatialys.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

import os
from osgeo import ogr


import gdaltest
import ogrtest
import pytest


@pytest.fixture(scope="module", autouse=True)
def setup_driver():
    driver = ogr.GetDriverByName('PGeo')
    if driver is not None:
        driver.Register()
    else:
        pytest.skip("PGeo driver not available", allow_module_level=True)

    # remove mdb driver
    mdb_driver = ogr.GetDriverByName('MDB')
    if mdb_driver is not None:
        mdb_driver.Deregister()

    yield

    if mdb_driver is not None:
        print('Reregistering MDB driver')
        mdb_driver.Register()


@pytest.fixture()
def download_test_data():
    if not gdaltest.download_file('http://download.osgeo.org/gdal/data/pgeo/PGeoTest.zip', 'PGeoTest.zip'):
        pytest.skip("Test data could not be downloaded")

    try:
        os.stat('tmp/cache/Autodesk Test.mdb')
    except OSError:
        try:
            gdaltest.unzip('tmp/cache', 'tmp/cache/PGeoTest.zip')
            try:
                os.stat('tmp/cache/Autodesk Test.mdb')
            except OSError:
                pytest.skip()
        except:
            pytest.skip()

    pgeo_ds = ogr.Open('tmp/cache/Autodesk Test.mdb')
    if pgeo_ds is None:
        pytest.skip('could not open DB. Driver probably misconfigured')

    return pgeo_ds

###############################################################################
# Basic testing


def test_ogr_pgeo_1(download_test_data):
    assert download_test_data.GetLayerCount() == 3, 'did not get expected layer count'

    lyr = download_test_data.GetLayer(0)
    feat = lyr.GetNextFeature()
    if feat.GetField('OBJECTID') != 1 or \
       feat.GetField('IDNUM') != 9424 or \
       feat.GetField('OWNER') != 'City':
        feat.DumpReadable()
        pytest.fail('did not get expected attributes')

    if ogrtest.check_feature_geometry(feat, 'MULTILINESTRING ((1910941.703951031 445833.57942859828 0,1910947.927691862 445786.43811868131 0))', max_error=0.0000001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    feat_count = lyr.GetFeatureCount()
    assert feat_count == 9418, 'did not get expected feature count'


###############################################################################
# Test spatial filter


def test_ogr_pgeo_2(download_test_data):
    lyr = download_test_data.GetLayer(0)
    lyr.ResetReading()
    feat = lyr.GetNextFeature()
    geom = feat.GetGeometryRef()
    bbox = geom.GetEnvelope()

    lyr.SetSpatialFilterRect(bbox[0], bbox[1], bbox[2], bbox[3])

    feat_count = lyr.GetFeatureCount()
    assert feat_count == 6957, 'did not get expected feature count'

    feat = lyr.GetNextFeature()
    if feat.GetField('OBJECTID') != 1 or \
       feat.GetField('IDNUM') != 9424 or \
       feat.GetField('OWNER') != 'City':
        feat.DumpReadable()
        pytest.fail('did not get expected attributes')

    # Check that geometry filter is well cleared
    lyr.SetSpatialFilter(None)
    feat_count = lyr.GetFeatureCount()
    assert feat_count == 9418, 'did not get expected feature count'

###############################################################################
# Test attribute filter


def test_ogr_pgeo_3(download_test_data):
    lyr = download_test_data.GetLayer(0)
    lyr.SetAttributeFilter('OBJECTID=1')

    feat_count = lyr.GetFeatureCount()
    assert feat_count == 1, 'did not get expected feature count'

    feat = lyr.GetNextFeature()
    if feat.GetField('OBJECTID') != 1 or \
       feat.GetField('IDNUM') != 9424 or \
       feat.GetField('OWNER') != 'City':
        feat.DumpReadable()
        pytest.fail('did not get expected attributes')

    # Check that attribute filter is well cleared (#3706)
    lyr.SetAttributeFilter(None)
    feat_count = lyr.GetFeatureCount()
    assert feat_count == 9418, 'did not get expected feature count'

###############################################################################
# Test ExecuteSQL()


def test_ogr_pgeo_4(download_test_data):
    sql_lyr = download_test_data.ExecuteSQL('SELECT * FROM SDPipes WHERE OBJECTID = 1')

    feat_count = sql_lyr.GetFeatureCount()
    assert feat_count == 1, 'did not get expected feature count'

    feat = sql_lyr.GetNextFeature()
    if feat.GetField('OBJECTID') != 1 or \
       feat.GetField('IDNUM') != 9424 or \
       feat.GetField('OWNER') != 'City':
        feat.DumpReadable()
        pytest.fail('did not get expected attributes')

    download_test_data.ReleaseResultSet(sql_lyr)

###############################################################################
# Test GetFeature()


def test_ogr_pgeo_5(download_test_data):
    lyr = download_test_data.GetLayer(0)
    feat = lyr.GetFeature(9418)
    if feat.GetField('OBJECTID') != 9418:
        feat.DumpReadable()
        pytest.fail('did not get expected attributes')


###############################################################################
# Run test_ogrsf


def test_ogr_pgeo_6(download_test_data):
    import test_cli_utilities
    if test_cli_utilities.get_test_ogrsf_path() is None:
        pytest.skip()

    ret = gdaltest.runexternal(test_cli_utilities.get_test_ogrsf_path() + ' "tmp/cache/Autodesk Test.mdb"')

    assert ret.find('INFO') != -1 and ret.find('ERROR') == -1

###############################################################################
# Run test_ogrsf with -sql


def test_ogr_pgeo_7(download_test_data):
    import test_cli_utilities
    if test_cli_utilities.get_test_ogrsf_path() is None:
        pytest.skip()

    ret = gdaltest.runexternal(test_cli_utilities.get_test_ogrsf_path() + ' "tmp/cache/Autodesk Test.mdb" -sql "SELECT * FROM SDPipes"')

    assert ret.find('INFO') != -1 and ret.find('ERROR') == -1

###############################################################################
# Open mdb with non-spatial tables


def test_ogr_pgeo_8():
    pgeo_ds = ogr.Open('data/pgeo/sample.mdb')
    if pgeo_ds is None:
        pytest.skip('could not open DB. Driver probably misconfigured')

    assert pgeo_ds.GetLayerCount() == 4, 'did not get expected layer count'

    layer_names = [pgeo_ds.GetLayer(n).GetName() for n in range(4)]
    assert set(layer_names) == {'lines', 'polys', 'points', 'non_spatial'}, 'did not get expected layer names'

    non_spatial_layer = pgeo_ds.GetLayerByName('non_spatial')
    feat = non_spatial_layer.GetNextFeature()
    if feat.GetField('text_field') != 'Record 1' or \
       feat.GetField('int_field') != 13 or \
       feat.GetField('long_int_field') != 10001 or \
       feat.GetField('float_field') != 13.5 or \
       feat.GetField('double_field') != 14.5 or \
       feat.GetField('date_field') != '2020/01/30 00:00:00':
        feat.DumpReadable()
        pytest.fail('did not get expected attributes')

    feat_count = non_spatial_layer.GetFeatureCount()
    assert feat_count == 2, 'did not get expected feature count'

##################################################################################
# Open mdb with polygon layer containing a mix of single and multi-part geometries


def test_ogr_pgeo_9():
    pgeo_ds = ogr.Open('data/pgeo/mixed_types.mdb')
    if pgeo_ds is None:
        pytest.skip('could not open DB. Driver probably misconfigured')

    polygon_layer = pgeo_ds.GetLayerByName('polygons')
    assert polygon_layer.GetGeomType() == ogr.wkbMultiPolygon

    # The PGeo format has a similar approach to multi-part handling as Shapefiles,
    # where polygon and multipolygon geometries or line and multiline geometries will
    # co-exist in a layer reported as just polygon or line type respectively.
    # To handle this in a predictable way for clients we always promote the polygon/line
    # types to multitypes, and correspondingly ALWAYS return multi polygon/line geometry
    # objects for features (even if strictly speaking the original feature had a polygon/line
    # geometry object)
    feat = polygon_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'MULTIPOLYGON (((-11315979.9947 6171775.831,-10597634.808 6140025.7675,-11331855.0265 5477243.192,-11315979.9947 6171775.831)))',
                                      max_error=0.0000001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    feat = polygon_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'MULTIPOLYGON (((-9855477.0737 5596305.9301,-9581632.776 5258961.5054,-9863414.5896 5258961.5054,-9855477.0737 5596305.9301)),((-10101540.0658 6092400.6723,-9470507.5538 6112244.462,-9490351.3435 5350242.938,-10101540.0658 6092400.6723)))',
                                      max_error=0.0000001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

##################################################################################
# Open mdb with lines layer containing a mix of single and multi-part geometries


def test_ogr_pgeo_10():
    pgeo_ds = ogr.Open('data/pgeo/mixed_types.mdb')
    if pgeo_ds is None:
        pytest.skip('could not open DB. Driver probably misconfigured')

    polygon_layer = pgeo_ds.GetLayerByName('lines')
    assert polygon_layer.GetGeomType() == ogr.wkbMultiLineString

    # The PGeo format has a similar approach to multi-part handling as Shapefiles,
    # where polygon and multipolygon geometries or line and multiline geometries will
    # co-exist in a layer reported as just polygon or line type respectively.
    # To handle this in a predictable way for clients we always promote the polygon/line
    # types to multitypes, and correspondingly ALWAYS return multi polygon/line geometry
    # objects for features (even if strictly speaking the original feature had a polygon/line
    # geometry object)
    feat = polygon_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'MULTILINESTRING ((-10938947.9907 6608339.2042,-10244415.3516 6608339.2042))',
                                      max_error=0.0000001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    feat = polygon_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'MULTILINESTRING ((-10383321.8794 6457526.4025,-10391259.3953 5786806.3111),(-10252352.8675 6465463.9184,-9625289.1133 6469432.6764))',
                                      max_error=0.0000001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')


##################################################################################
# Open mdb with layers with z/m and check that they are handled correctly


def test_ogr_pgeo_11():
    pgeo_ds = ogr.Open('data/pgeo/geometry_types.mdb')
    if pgeo_ds is None:
        pytest.skip('could not open DB. Driver probably misconfigured')

    point_z_layer = pgeo_ds.GetLayerByName('point_z')
    assert point_z_layer.GetGeomType() == ogr.wkbPoint25D

    feat = point_z_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'POINT Z (-2 -1.0 4)',
                                      max_error=0.0000001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    feat = point_z_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'POINT Z (1 2 3)',
                                      max_error=0.0000001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    point_m_layer = pgeo_ds.GetLayerByName('point_m')
    assert point_m_layer.GetGeomType() == ogr.wkbPointM

    feat = point_m_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'POINT M (1 2 11)',
                                      max_error=0.0001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    feat = point_m_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'POINT M (-2 -1 13)',
                                      max_error=0.0001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    point_zm_layer = pgeo_ds.GetLayerByName('point_zm')
    assert point_zm_layer.GetGeomType() == ogr.wkbPointZM

    feat = point_zm_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'POINT ZM (-2 -1.0 4 13)',
                                      max_error=0.0001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')

    feat = point_zm_layer.GetNextFeature()
    if ogrtest.check_feature_geometry(feat,
                                      'POINT ZM (1 2 3 11)',
                                      max_error=0.0001) != 0:
        feat.DumpReadable()
        pytest.fail('did not get expected geometry')
