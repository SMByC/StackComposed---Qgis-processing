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


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load StackComposed class from file StackComposed.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from StackComposed.StackComposed_plugin import StackComposedPlugin
    return StackComposedPlugin()
