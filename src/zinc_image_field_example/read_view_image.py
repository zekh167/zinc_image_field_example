import sys
from PySide import QtGui
from zinc_view_graphics_ui import Ui_ZincViewGraphics

import imagesize

from opencmiss.zinc.context import Context as ZincContext
from opencmiss.zinc.element import Element, Elementbasis
from opencmiss.zinc.status import OK as ZINC_OK


class ZincViewImage(QtGui.QMainWindow):

    def __init__(self, filename, parent=None):
        super(ZincViewImage, self).__init__(parent)

        self._context = ZincContext("ZincViewGraphics")
        self._material_module = self._context.getMaterialmodule()
        self._region = self._context.getDefaultRegion()

        self._fieldmodule = self._region.getFieldmodule()
        self._scaled_coordinate_field = None
        self._image_based_material = None
        self._filename = filename

        self._ui = Ui_ZincViewGraphics()
        self._ui.setupUi(self)
        self._make_connections()
        self._ui.sceneviewerWidget.setContext(self._context)
        self._ui.sceneviewerWidget.graphicsInitialized.connect(self._graphics_initialized)

        self._create_model()
        self._load_image()

    def _graphics_initialized(self):
        sceneviewer = self._ui.sceneviewerWidget.getSceneviewer()
        sceneviewer.setBackgroundColourRGB([0.0, 0.0, 0.0])

    def _make_connections(self):
        self._ui.viewAllButton.clicked.connect(self._view_all_clicked)

    def _view_all_clicked(self):
        self._ui.sceneviewerWidget.getSceneviewer().viewAll()

    def _create_square_2d_finite_element(self, coordinate_field, node_coordinate_set):
        nodeset = self._fieldmodule.findNodesetByName('nodes')
        node_template = nodeset.createNodetemplate()
        node_template.defineField(coordinate_field)
        field_cache = self._fieldmodule.createFieldcache()

        node_identifiers = []
        # Create eight nodes to define a cube finite element
        for node_coordinate in node_coordinate_set:
            node = nodeset.createNode(-1, node_template)
            node_identifiers.append(node.getIdentifier())
            # Set the node coordinates, first set the field cache to use the current node
            field_cache.setNode(node)
            # Pass in floats as an array
            result = coordinate_field.assignReal(field_cache, node_coordinate)
            if result != ZINC_OK:
                raise ValueError('Could not create nodes for box.')

        # Use a 3D mesh to to create the 2D finite element.
        mesh = self._fieldmodule.findMeshByDimension(2)
        element_template = mesh.createElementtemplate()
        element_template.setElementShapeType(Element.SHAPE_TYPE_SQUARE)
        element_node_count = 4
        element_template.setNumberOfNodes(element_node_count)
        # Specify the dimension and the interpolation function for the element basis function
        linear_basis = self._fieldmodule.createElementbasis(2, Elementbasis.FUNCTION_TYPE_LINEAR_LAGRANGE)
        # the indecies of the nodes in the node template we want to use.
        node_indexes = [1, 2, 3, 4]

        # Define a nodally interpolated element field or field component in the
        # element_template
        element_template.defineFieldSimpleNodal(coordinate_field, -1, linear_basis, node_indexes)

        for i, node_identifier in enumerate(node_identifiers):
            node = nodeset.findNodeByIdentifier(node_identifier)
            result = element_template.setNode(i + 1, node)
            if result != ZINC_OK:
                raise ValueError('Could not create elements for box.')

        mesh.defineElement(-1, element_template)
        self._fieldmodule.defineAllFaces()

    def _create_model(self):
        coordinate_field = self._create_finite_element_field()
        scale_field = self._fieldmodule.createFieldConstant([2, 3, 1])
        scale_field.setName('scale')
        offset_field = self._fieldmodule.createFieldConstant([+0.5, +0.5, 0.0])
        self._scaled_coordinate_field = self._fieldmodule.createFieldMultiply(scale_field, coordinate_field)
        self._scaled_coordinate_field = self._fieldmodule.createFieldAdd(self._scaled_coordinate_field, offset_field)
        self._scaled_coordinate_field.setManaged(True)
        self._scaled_coordinate_field.setName('scaled_coordinates')
        self._create_square_2d_finite_element(coordinate_field, [[0.0, 0.0, 0.0],
                                                                 [1.0, 0.0, 0.0],
                                                                 [0.0, 1.0, 0.0],
                                                                 [1.0, 1.0, 0.0]])

    def _create_finite_element_field(self, dimension=3, field_name='coordinates', managed=True, type_coordinate=True):
        fieldmodule = self._region.getFieldmodule()
        fieldmodule.beginChange()

        # Create a finite element field with 3 components to represent 3 dimensions
        finite_element_field = fieldmodule.createFieldFiniteElement(dimension)

        # Set the name of the field
        finite_element_field.setName(field_name)
        # Set the attribute is managed to 1 so the field module will manage the field for us

        finite_element_field.setManaged(managed)
        finite_element_field.setTypeCoordinate(type_coordinate)
        fieldmodule.endChange()

        return finite_element_field

    def _create_image_field(self, image_filename, field_name='image'):
        image_field = self._fieldmodule.createFieldImage()
        image_field.setName(field_name)
        image_field.setFilterMode(image_field.FILTER_MODE_LINEAR)

        stream_information = image_field.createStreaminformationImage()
        stream_information.createStreamresourceFile(image_filename)
        result = image_field.read(stream_information)
        if result != ZINC_OK:
            raise ValueError('Could not read image.')

        return image_field

    def _create_material_using_image_field(self, image_field, colour_mapping_type=None, image_range=None):
        # create a graphics material from the graphics module, assign it a name
        # and set flag to true
        scene = self._region.getScene()
        material_module = scene.getMaterialmodule()
        spectrum_module = scene.getSpectrummodule()
        material = material_module.createMaterial()
        spectrum = spectrum_module.createSpectrum()
        component = spectrum.createSpectrumcomponent()
        if colour_mapping_type is None:
            colour_mapping_type = component.COLOUR_MAPPING_TYPE_RAINBOW
        component.setColourMappingType(colour_mapping_type)
        if image_range is not None:
            component.setRangeMinimum(image_range[0])
            component.setRangeMaximum(image_range[1])
        material.setTextureField(1, image_field)
        return material

    def _load_image(self):
        image_dimensions = [0, 0]
        image_based_material = None
        width, height = imagesize.get(self._filename)
        if width != -1 or height != -1:
            cache = self._fieldmodule.createFieldcache()
            # self._scaled_coordinate_field = self._fieldmodule.findFieldByName('scale')
            self._scaled_coordinate_field.assignReal(cache, [width, height, 1.0])
            image_dimensions = [width, height]
            image_field = self._create_image_field(self._filename)
            self._image_based_material = self._create_material_using_image_field(image_field)
            self._image_based_material.setName('images')
            self._image_based_material.setManaged(True)

        return image_dimensions, image_based_material

    def create_graphics(self):
        scene = self._region.getScene()
        # coordinate_field = self._scaled_coordinate_field
        scene.beginChange()
        scene.removeAllGraphics()
        xi = self._fieldmodule.findFieldByName('xi')
        lines = scene.createGraphicsLines()
        lines.setExterior(True)
        lines.setName('plane-lines')
        lines.setCoordinateField(self._scaled_coordinate_field)
        surfaces = scene.createGraphicsSurfaces()
        surfaces.setName('plane-surfaces')
        surfaces.setCoordinateField(self._scaled_coordinate_field)
        temp1 = self._fieldmodule.createFieldComponent(xi, [1, 2])
        texture_field = self._fieldmodule.createFieldConcatenate([temp1])
        result = surfaces.setTextureCoordinateField(texture_field)
        if result != ZINC_OK:
            raise ValueError('Texture coordinate was not successful.')
        surfaces.setMaterial(self._image_based_material)
        scene.endChange()


def main():
    app = QtGui.QApplication(sys.argv)

    image_filename = 'C:\\Users\\zekh167\\Desktop\\Stellate-documentation\\c.png'
    zinc_view_image = ZincViewImage(image_filename)
    zinc_view_image.create_graphics()
    zinc_view_image.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
