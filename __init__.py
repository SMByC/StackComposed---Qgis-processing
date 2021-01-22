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

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QMessageBox

from StackComposed.utils.extra_deps import load_install_extra_deps, WaitDialog


def pre_init_plugin(iface):
    app = QCoreApplication.instance()
    parent = iface.mainWindow()
    dialog = None
    log = ''
    try:
        for msg_type, msg_val in load_install_extra_deps():
            app.processEvents()
            if msg_type == 'log':
                log += msg_val
            elif msg_type == 'needs_install':
                dialog = WaitDialog(parent, 'Stack Composed - installing dependencies')
            elif msg_type == 'install_done':
                dialog.accept()
    except Exception as e:
        if dialog:
            dialog.accept()
        QMessageBox.critical(parent, 'Stack Composed - installing dependencies',
                             'An error occurred during the installation of Python packages. ' +
                             'Click on "Stack Trace" in the QGIS message bar for details.')
        raise RuntimeError('\nStack Composed: Error installing Python packages. Read install instruction: '
                           'https://github.com/SMByC/StackComposed-Qgis-processing\nLog:\n' + log) from e


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load StackComposed class from file StackComposed.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    # load/install extra python dependencies
    pre_init_plugin(iface)

    #
    from StackComposed.StackComposed_plugin import StackComposedPlugin
    return StackComposedPlugin()
