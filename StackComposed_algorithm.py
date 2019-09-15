# -*- coding: utf-8 -*-
"""
/***************************************************************************
 StackComposed
                          A QGIS plugin processing
 Compute and generate the composed of a raster images stack
                              -------------------
        copyright            : (C) 2019 by Xavier Corredor Llano, SMByC
        email                : xcorredorl@ideam.gov.co
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
from multiprocessing import cpu_count

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterRasterDestination, QgsProcessingParameterNumber,
                       QgsProcessingParameterEnum, QgsProcessingParameterDefinition,
                       QgsProcessingParameterString)


class StackComposedAlgorithm(QgsProcessingAlgorithm):
    """
    This algorithm compute a specific statistic using the time
    series of all pixels across (the time) all raster in the specific band
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    STAT = 'STAT'
    BAND = 'BAND'
    DATA_TYPE = 'DATA_TYPE'
    NODATA_INPUT = 'NODATA_INPUT'
    START_DATE = 'START_DATE'
    END_DATE = 'END_DATE'
    NUM_PROCESS = 'NUM_PROCESS'
    CHUNKS = 'CHUNKS'
    OUTPUT = 'OUTPUT'

    STAT_DICT = {'Median': 'median', 'Arithmetic mean': 'mean', 'Geometric mean': 'gmean',
                 'Maximum value': 'max', 'Minimum value': 'min', 'Standard deviation': 'std',
                 'Number of valid pixels': 'valid_pixels',
                 'Last valid pixel (required filename as metadata)': 'last_pixel',
                 'Julian day of the last valid pixel (required filename as metadata)': 'jday_last_pixel',
                 'Julian day of the median value (required filename as metadata)': 'jday_median',
                 'Linear trend least-squares method (required filename as metadata)': 'linear_trend'}
    TYPES = ['Default', 'Byte', 'Int16', 'UInt16', 'UInt32', 'Int32', 'Float32', 'Float64', 'CInt16', 'CInt32',
             'CFloat32', 'CFloat64']

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        parameter_input = \
            QgsProcessingParameterMultipleLayers(
                self.INPUT,
                self.tr('Input raster files'),
                QgsProcessing.TypeRaster,
            )
        parameter_input.setMinimumNumberInputs(2)
        self.addParameter(parameter_input)

        self.addParameter(
            QgsProcessingParameterEnum(
                self.STAT,
                self.tr('Statistic for compute the composed'),
                self.STAT_DICT.keys(),
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
            QgsProcessingParameterEnum(
                self.DATA_TYPE,
                self.tr('Output data type'),
                self.TYPES,
                allowMultiple=False,
                defaultValue=0
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
            QgsProcessingParameterString(
                self.START_DATE,
                self.tr('Initial date for filter data, format YYYY-MM-DD'),
                defaultValue=None,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.END_DATE,
                self.tr('End date for filter data, format YYYY-MM-DD'),
                defaultValue=None,
                optional=True
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

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(parameters, self.INPUT, context)
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
                context, source.fields(), source.wkbType(), source.sourceCrs())

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()

        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            # Add a feature in the sink
            sink.addFeature(feature, QgsFeatureSink.FastInsert)

            # Update the progress bar
            feedback.setProgress(int(current * total))

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}

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

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return StackComposedAlgorithm()
