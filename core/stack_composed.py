#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Stack Composed
#
#  Copyright (C) 2016-2018 Xavier Corredor Llano, SMBYC
#  Email: xcorredorl at ideam.gov.co
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import warnings
import numpy as np
from osgeo import gdal, osr

from qgis.core import QgsProcessingException

from StackComposed.core.image import Image
from StackComposed.core.stats import statistic


def run(stat, band, nodata, output, output_type, num_process, chunksize, start_date, end_date, images_files, feedback):
    # ignore warnings
    warnings.filterwarnings("ignore")

    feedback.pushInfo("\nLoading and prepare images in path(s):")

    # load images
    images = [Image(img) for img in images_files]

    # filter images based on the start date and/or end date, required filename as metadata
    if start_date not in [None, ''] or end_date not in [None, '']:
        [image.set_metadata_from_filename() for image in images]
        if start_date not in [None, '']:
            images = [image for image in images if image.date >= start_date]
        if end_date not in [None, '']:
            images = [image for image in images if image.date <= end_date]

    if len(images) <= 1:
        raise QgsProcessingException(
            "\n\nError: StackComposed required at least 2 or more images to process.\n")

    # save nodata set from arguments
    Image.nodata_from_arg = nodata

    # get wrapper extent
    min_x = min([image.extent[0] for image in images])
    max_y = max([image.extent[1] for image in images])
    max_x = max([image.extent[2] for image in images])
    min_y = min([image.extent[3] for image in images])
    Image.wrapper_extent = [min_x, max_y, max_x, min_y]

    # define the properties for the raster wrapper
    Image.wrapper_x_res = images[0].x_res
    Image.wrapper_y_res = images[0].y_res
    Image.wrapper_shape = (int((max_y-min_y)/Image.wrapper_y_res), int((max_x-min_x)/Image.wrapper_x_res))  # (y,x)

    # some information about process
    feedback.pushInfo("  images to process: {0}".format(len(images)))
    feedback.pushInfo("  band to process: {0}".format(band))
    feedback.pushInfo("  pixels size: {0} x {1}".format(round(Image.wrapper_x_res, 1), round(Image.wrapper_y_res, 1)))
    feedback.pushInfo("  wrapper size: {0} x {1} pixels".format(Image.wrapper_shape[1], Image.wrapper_shape[0]))
    feedback.pushInfo("  running in {0} cores with chunks size {1}".format(num_process, chunksize))

    # check
    feedback.pushInfo("  checking band and pixel size: ")
    for image in images:
        if band > image.n_bands:
            raise QgsProcessingException(
                "\n\nError: the image '{0}' don't have the band {1} needed to process\n".format(image.file_path, band))
        if round(image.x_res, 1) != round(Image.wrapper_x_res, 1) or \
           round(image.y_res, 1) != round(Image.wrapper_y_res, 1):
            raise QgsProcessingException(
                "\n\nError: the image '{}' don't have the same pixel size to the base image: {}x{} vs {}x{}."
                  " The stack-composed is not enabled for process yet images with different pixel size.\n"
                  .format(image.file_path, round(image.x_res, 1), round(image.y_res, 1),
                          round(Image.wrapper_x_res, 1), round(Image.wrapper_x_res, 1)))
    feedback.pushInfo("ok")

    # set bounds for all images
    [image.set_bounds() for image in images]

    # for some statistics that required filename as metadata
    if stat in ["last_pixel", "jday_last_pixel", "jday_median", "linear_trend"]:
        [image.set_metadata_from_filename() for image in images]

    # choose the default data type based on the statistic
    if output_type in [None, '', 'Default']:
        if stat in ['median', 'mean', 'gmean', 'max', 'min', 'last_pixel', 'jday_last_pixel',
                    'jday_median'] or stat.startswith(('percentile_', 'trim_mean_')):
            gdal_output_type = gdal.GDT_UInt16
        if stat in ['std', 'snr']:
            gdal_output_type = gdal.GDT_Float32
        if stat in ['valid_pixels']:
            if len(images) < 256:
                gdal_output_type = gdal.GDT_Byte
            else:
                gdal_output_type = gdal.GDT_UInt16
        if stat in ['linear_trend']:
            gdal_output_type = gdal.GDT_Int32
    else:
        if output_type == 'Byte': gdal_output_type = gdal.GDT_Byte
        if output_type == 'UInt16': gdal_output_type = gdal.GDT_UInt16
        if output_type == 'UInt32': gdal_output_type = gdal.GDT_UInt32
        if output_type == 'Int16': gdal_output_type = gdal.GDT_Int16
        if output_type == 'Int32': gdal_output_type = gdal.GDT_Int32
        if output_type == 'Float32': gdal_output_type = gdal.GDT_Float32
        if output_type == 'Float64': gdal_output_type = gdal.GDT_Float64
    for image in images:
        image.output_type = gdal_output_type

    ### process ###
    # Calculate the statistics
    feedback.pushInfo("\nProcessing the {} for band {}:".format(stat, band))
    output_array = statistic(stat, images, band, num_process, chunksize)

    ### save result ###
    # create output raster
    driver = gdal.GetDriverByName('GTiff')
    nbands = 1
    outRaster = driver.Create(output, Image.wrapper_shape[1], Image.wrapper_shape[0],
                              nbands, gdal_output_type)
    outband = outRaster.GetRasterBand(nbands)

    # set nodata value depend of the output type
    if gdal_output_type in [gdal.GDT_Byte, gdal.GDT_UInt16, gdal.GDT_UInt32, gdal.GDT_Int16, gdal.GDT_Int32]:
        outband.SetNoDataValue(0)
    if gdal_output_type in [gdal.GDT_Float32, gdal.GDT_Float64]:
        outband.SetNoDataValue(np.nan)

    # write band
    outband.WriteArray(output_array)

    # set projection and geotransform
    outRasterSRS = osr.SpatialReference()
    outRasterSRS.ImportFromWkt(Image.projection)
    outRaster.SetProjection(outRasterSRS.ExportToWkt())
    outRaster.SetGeoTransform((Image.wrapper_extent[0], Image.wrapper_x_res, 0,
                               Image.wrapper_extent[1], 0, -Image.wrapper_y_res))

    # clean
    del driver, outRaster, outband, outRasterSRS, output_array



