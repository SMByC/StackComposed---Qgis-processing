# -*- coding: utf-8 -*-
"""
/***************************************************************************
 StackComposed
                          A QGIS plugin processing
 Compute and generate the composed of a raster images stack
                              -------------------
        copyright            : (C) 2021 by Xavier Corredor Llano, SMByC
        email                : xavier.corredor.llano@gmail.com
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
import os
from multiprocessing import cpu_count

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterRasterDestination, QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum, QgsProcessingParameterDefinition,
                       QgsProcessingParameterString, QgsProcessingException, QgsRasterFileWriter)

from StackComposed.core import stack_composed


class StackComposedAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm compute a specific statistic using the time
    series of all pixels across (the time) all raster in the specific band
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUTS = 'INPUTS'
    STAT = 'STAT'
    BAND = 'BAND'
    NODATA_INPUT = 'NODATA_INPUT'
    DATA_TYPE = 'DATA_TYPE'
    NUM_PROCESS = 'NUM_PROCESS'
    CHUNKS = 'CHUNKS'
    OUTPUT = 'OUTPUT'

    STAT_KEYS = ['median', 'mean', 'gmean', 'max', 'min', 'std', 'valid_pixels', 'last_pixel', 'jday_last_pixel',
                 'jday_median', 'linear_trend']
    STAT_DESC = ['Median', 'Arithmetic mean', 'Geometric mean', 'Maximum value', 'Minimum value', 'Standard deviation',
                 'Number of valid pixels', 'Last valid pixel (required filename as metadata)',
                 'Julian day of the last valid pixel (required filename as metadata)',
                 'Julian day of the median value (required filename as metadata)',
                 'Linear trend least-squares method (required filename as metadata)']

    TYPES = ['Default', 'Byte', 'UInt16', 'Int16', 'UInt32', 'Int32', 'Float32', 'Float64']

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return StackComposedAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Stack Composed'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Raster layer stack'

    def icon(self):
        return QIcon(":/plugins/StackComposed/icons/stack_composed.svg")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        parameter_input = \
            QgsProcessingParameterMultipleLayers(
                self.INPUTS,
                self.tr('All input raster files to process'),
                QgsProcessing.TypeRaster,
            )
        parameter_input.setMinimumNumberInputs(2)
        self.addParameter(parameter_input)

        self.addParameter(
            QgsProcessingParameterEnum(
                self.STAT,
                self.tr('Statistic for compute the composed'),
                self.STAT_DESC,
                allowMultiple=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                self.tr('Set the band number to process'),
                type=QgsProcessingParameterNumber.Integer,
                minValue=1,
                defaultValue=1,
                optional=False
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA_INPUT,
                self.tr('Input pixel value to treat as "nodata"'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=None,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.DATA_TYPE,
                self.tr('Output data type'),
                self.TYPES,
                allowMultiple=False,
                defaultValue='Default',
            )
        )

        parameter_num_process = \
            QgsProcessingParameterNumber(
                self.NUM_PROCESS,
                self.tr('Set the number of process'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=cpu_count(),
                optional=True
            )
        parameter_num_process.setFlags(parameter_num_process.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(parameter_num_process)

        parameter_chunks = \
            QgsProcessingParameterNumber(
                self.CHUNKS,
                self.tr('Chunks size for parallel process'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=500,
                optional=True
            )
        parameter_chunks.setFlags(parameter_chunks.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(parameter_chunks)

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                self.tr('Output raster stack composed')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        layers = self.parameterAsLayerList(parameters, self.INPUTS, context)
        images_files = [os.path.realpath(layer.source().split("|layername")[0]) for layer in layers]

        output_file = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        stack_composed.run(
            stat=self.STAT_KEYS[self.parameterAsEnum(parameters, self.STAT, context)],
            band=self.parameterAsInt(parameters, self.BAND, context),
            nodata=self.parameterAsInt(parameters, self.NODATA_INPUT, context),
            output= output_file,
            output_type=self.TYPES[self.parameterAsEnum(parameters, self.DATA_TYPE, context)],
            num_process=self.parameterAsInt(parameters, self.NUM_PROCESS, context),
            chunksize=self.parameterAsInt(parameters, self.CHUNKS, context),
            images_files=images_files,
            feedback=feedback)

        return {self.OUTPUT: output_file}
