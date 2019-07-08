########################
Create and View Graphics
########################

This tutorial example shows how to create basic graphics to visualise an image in OpenCMISS-Zinc, and how to view them
interactively in a window.

What You Need
=============

You need to install Python, the OpenCMISS-Zinc library, and PyZinc (Python bindings to Zinc) as described in earlier
tutorials. For the user interface you also require Qt, PySide (Qt for Python) and the
`ZincPythonTools <https://github.com/OpenCMISS-Bindings/ZincPythonTools>`_ which supply reusable widgets for showing
graphics and building user interfaces with Zinc. Instructions for getting these are found elsewhere on the opencmiss.org
documentation.

You will also need to download and unzip the
`Zinc View Graphics Example Zip file <https://github.com/OpenCMISS-Examples/zinc_view_graphics/archive/master.zip>`_.

Running the Example
===================

Change to the ``src/zinc_view_graphics`` directory under the location where you unzipped the example files and run the
example script with::

  python read_view_image.py

You should see a window containing a graphical visualisation of an image as in the following figure:

.. figure:: sample.png
  :align: center