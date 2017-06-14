import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# SegmentStatistics
#

class SegmentStatistics(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    import string
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Segment Statistics"
    self.parent.categories = ["Quantification"]
    self.parent.dependencies = ["SubjectHierarchy"]
    self.parent.contributors = ["Andras Lasso (PerkLab), Christian Bauer (University of Iowa), Steve Pieper (Isomics)"]
    self.parent.helpText = """
Use this module to calculate counts and volumes for segments plus statistics on the grayscale background volume.
Computed fields:
Segment labelmap stastistics (LM): voxel count, volume mm3, volume cc.
Requires segment labelmap representation.
Grayscale volume statistics (GS): voxel count, volume mm3, volume cc (where segments overlap grayscale volume),
min, max, mean, stdev (intensity statistics).
Requires segment labelmap representation and selection of a grayscale volume
Closed surface statistics (CS): surface mm2, volume mm3, volume cc (computed from closed surface).
Requires segment closed surface representation.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
Supported by NA-MIC, NAC, BIRN, NCIGT, and the Slicer Community. See http://www.slicer.org for details.
"""

  def setup(self):
    # Register subject hierarchy plugin
    import SubjectHierarchyPlugins
    scriptedPlugin = slicer.qSlicerSubjectHierarchyScriptedPlugin(None)
    scriptedPlugin.setPythonSource(SubjectHierarchyPlugins.SegmentStatisticsSubjectHierarchyPlugin.filePath)

#
# SegmentStatisticsWidget
#

class SegmentStatisticsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = SegmentStatisticsLogic()
    self.grayscaleNode = None
    self.labelNode = None
    self.parameterNode = None
    self.parameterNodeObserver = None
    self.fileName = None
    self.fileDialog = None

    # Instantiate and connect widgets ...
    #

    # Inputs
    inputsCollapsibleButton = ctk.ctkCollapsibleButton()
    inputsCollapsibleButton.text = "Inputs"
    self.layout.addWidget(inputsCollapsibleButton)
    inputsFormLayout = qt.QFormLayout(inputsCollapsibleButton)

    # Segmentation selector
    self.segmentationSelector = slicer.qMRMLNodeComboBox()
    self.segmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.segmentationSelector.addEnabled = False
    self.segmentationSelector.removeEnabled = True
    self.segmentationSelector.renameEnabled = True
    self.segmentationSelector.setMRMLScene( slicer.mrmlScene )
    self.segmentationSelector.setToolTip( "Pick the segmentation to compute statistics for" )
    inputsFormLayout.addRow("Segmentation:", self.segmentationSelector)

    # Grayscale volume selector
    self.grayscaleSelector = slicer.qMRMLNodeComboBox()
    self.grayscaleSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.grayscaleSelector.addEnabled = False
    self.grayscaleSelector.removeEnabled = True
    self.grayscaleSelector.renameEnabled = True
    self.grayscaleSelector.noneEnabled = True
    self.grayscaleSelector.showChildNodeTypes = False
    self.grayscaleSelector.setMRMLScene( slicer.mrmlScene )
    self.grayscaleSelector.setToolTip( "Select the grayscale volume for intensity statistics calculations")
    inputsFormLayout.addRow("Grayscale volume:", self.grayscaleSelector)

    # Output table selector
    outputCollapsibleButton = ctk.ctkCollapsibleButton()
    outputCollapsibleButton.text = "Output"
    self.layout.addWidget(outputCollapsibleButton)
    outputFormLayout = qt.QFormLayout(outputCollapsibleButton)

    self.outputTableSelector = slicer.qMRMLNodeComboBox()
    self.outputTableSelector.nodeTypes = ["vtkMRMLTableNode"]
    self.outputTableSelector.addEnabled = True
    self.outputTableSelector.selectNodeUponCreation = True
    self.outputTableSelector.renameEnabled = True
    self.outputTableSelector.removeEnabled = True
    self.outputTableSelector.noneEnabled = False
    self.outputTableSelector.setMRMLScene( slicer.mrmlScene )
    self.outputTableSelector.setToolTip( "Select the table where statistics will be saved into")
    outputFormLayout.addRow("Output table:", self.outputTableSelector)

    # Apply Button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Calculate Statistics."
    self.applyButton.enabled = False
    self.parent.layout().addWidget(self.applyButton)

    # Parameter set
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    #parametersCollapsibleButton.collapsed = True
    self.layout.addWidget(parametersCollapsibleButton)
    self.parametersLayout = qt.QFormLayout(parametersCollapsibleButton)

    # Parameter set selector
    self.parameterNodeSelector = slicer.qMRMLNodeComboBox()
    self.parameterNodeSelector.nodeTypes = ( ("vtkMRMLScriptedModuleNode"), "" )
    self.parameterNodeSelector.addAttribute( "vtkMRMLScriptedModuleNode", "ModuleName", "SegmentStatistics" )
    self.parameterNodeSelector.selectNodeUponCreation = True
    self.parameterNodeSelector.addEnabled = True
    self.parameterNodeSelector.renameEnabled = True
    self.parameterNodeSelector.removeEnabled = True
    self.parameterNodeSelector.noneEnabled = False
    self.parameterNodeSelector.showHidden = True
    self.parameterNodeSelector.showChildNodeTypes = False
    self.parameterNodeSelector.baseName = "SegmentStatistics"
    self.parameterNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.parameterNodeSelector.setToolTip( "Pick parameter set" )
    self.parametersLayout.addRow("Parameter set: ", self.parameterNodeSelector)

    # Add vertical spacer
    self.parent.layout().addStretch(1)

    # connections
    self.applyButton.connect('clicked()', self.onApply)
    self.grayscaleSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.segmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.outputTableSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onParameterSetSelected)

    self.parameterNodeSelector.setCurrentNode(self.logic.getParameterNode())
    self.onNodeSelectionChanged()
    self.updateOptions()

  def cleanup(self):
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)

  def onNodeSelectionChanged(self):
    self.applyButton.enabled = ( (self.segmentationSelector.currentNode() is not None) and
                                 (self.outputTableSelector.currentNode() is not None) and
                                 (self.parameterNodeSelector.currentNode() is not None) )
    if self.segmentationSelector.currentNode():
      self.outputTableSelector.baseName = self.segmentationSelector.currentNode().GetName() + ' statistics'

  def onApply(self):
    """Calculate the label statistics
    """
    # Lock GUI
    self.applyButton.text = "Working..."
    self.applyButton.setEnabled(False)
    slicer.app.processEvents()
    # Compute statistics
    self.logic.computeStatistics(self.segmentationSelector.currentNode(), self.grayscaleSelector.currentNode())
    self.logic.exportToTable(self.outputTableSelector.currentNode())
    # Unlock GUI
    self.applyButton.setEnabled(True)
    self.applyButton.text = "Apply"

    self.logic.showTable(self.outputTableSelector.currentNode())

  def updateOptions(self):
    #self.optionsFormLayout.clear()
    for calculator in self.logic.calculators:
      calculatorOptionsCollapsibleButton = ctk.ctkCollapsibleGroupBox()
      calculatorOptionsCollapsibleButton.setTitle( calculator.name )
      calculatorOptionsFormLayout = qt.QFormLayout(calculatorOptionsCollapsibleButton)
      calculatorOptionsFormLayout.addRow(calculator.optionsWidget)
      self.parametersLayout.addRow(calculatorOptionsCollapsibleButton)

  def onParameterSetSelected(self):
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)
    self.parameterNode = self.parameterNodeSelector.currentNode()
    if self.parameterNode:
      self.logic.setParameterNode(self.parameterNode)
      self.parameterNodeObserver = self.parameterNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGuiFromParameterNode)
    self.updateGuiFromParameterNode()

  def updateGuiFromParameterNode(self, caller=None, event=None):
    # NOTE: nothing to do so far; GUI updates are handled in the calculator classes
    pass

  def updateParameterNodeFromGui(self):
    # NOTE: nothing to do so far; paramter node updates are handled in the calculator classes
    pass

class SegmentStatisticsCalculatorBase(object):
  """Base class for statistics calculators operating on segments.
  Derived classes should specify: self.name, self.keys, self.defaultKeys
  and implement: computeStatistics, getMeasurementInfo
  """
  def __init__(self):
    self.name = "" # name of the statistics calculator
    self.keys = () # keys for all supported measurements
    self.defaultKeys = () # measurements that will be enabled by default
    self.optionsWidget = qt.QWidget()
    self.requestedKeysCheckboxes = {}
    self.parameterNode = None
    self.parameterNodeObserver = None

  def __del__(self):
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)

  def computeStatistics(self, segmentationNode, segmentID, grayscaleNode=None):
    """Compute measurements for requested keys on the given segment"""
    stats = {}
    #for key in self.getRequestedKeys():
    #  stats[key] = ...
    return stats

  def getMeasurementInfo(self, key, segmentationNode=None, grayscaleNode=None):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    if key not in self.keys:
      return None
    return {"name": key, "description": key, "units": None}

  def setDefaultParameters(self, parameterNode, overwriteExisting=False):
    for key in self.keys:
      parameter = key+'.enabled'
      if not parameterNode.GetParameter(parameter) or overwriteExisting:
        parameterNode.SetParameter(parameter, str(key in self.defaultKeys))

  def getRequestedKeys(self):
    if not self.parameterNode:
      return ()
    requestedKeys = tuple(key for key in self.keys if self.parameterNode.GetParameter(key+'.enabled')=='True')
    return requestedKeys

  def setParameterNode(self, parameterNode):
    if self.parameterNode==parameterNode:
        return
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)
    self.parameterNode = parameterNode
    if self.parameterNode:
      self.setDefaultParameters(self.parameterNode)
      self.parameterNodeObserver = self.parameterNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGuiFromParameterNode)
    self.updateGuiFromParameterNode()

  def getParameterNode(self):
    return self.parameterNode

  def createDefaultOptionsWidget(self):
    # create list of checkboxes that allow selection of requested keys
    form = qt.QFormLayout(self.optionsWidget)

    # select all/none/default buttons
    selectAllNoneFrame = qt.QFrame(self.optionsWidget)
    selectAllNoneFrame.setLayout(qt.QHBoxLayout())
    selectAllNoneFrame.layout().setSpacing(0)
    selectAllNoneFrame.layout().setMargin(0)
    selectAllNoneFrame.layout().addWidget(qt.QLabel("Select measurements: ",self.optionsWidget))
    selectAllButton = qt.QPushButton('all',self.optionsWidget)
    selectAllNoneFrame.layout().addWidget(selectAllButton)
    selectAllButton.connect('clicked()', self.requestAll)
    selectNoneButton = qt.QPushButton('none',self.optionsWidget)
    selectAllNoneFrame.layout().addWidget(selectNoneButton)
    selectNoneButton.connect('clicked()', self.requestNone)
    selectDefaultButton = qt.QPushButton('default',self.optionsWidget)
    selectAllNoneFrame.layout().addWidget(selectDefaultButton)
    selectDefaultButton.connect('clicked()', self.requestDefault)
    form.addRow(selectAllNoneFrame)

    # checkboxes for individual keys
    self.requestedKeysCheckboxes = {}
    requestedKeys = self.getRequestedKeys()
    for key in self.keys:
      label = key
      tooltip = "key: "+key
      info = self.getMeasurementInfo(key)
      if info and ("name" in info or "description" in info):
        label = info["description"] if "description" in info else info["name"]
        if "name" in info: tooltip += "\nname: " + str(info["name"])
        if "description" in info: tooltip += "\ndescription: " + str(info["description"])
        if "units" in info: tooltip += "\nunits: " + (str(info["units"]) if info["units"] else "n/a")
      checkbox = qt.QCheckBox(label,self.optionsWidget)
      checkbox.checked = key in requestedKeys
      checkbox.setToolTip(tooltip)
      form.addRow(checkbox)
      self.requestedKeysCheckboxes[key] = checkbox
      checkbox.connect('stateChanged(int)', self.updateParameterNodeFromGui)

  def updateGuiFromParameterNode(self, caller=None, event=None):
    if not self.parameterNode:
      return
    for (key, checkbox) in self.requestedKeysCheckboxes.iteritems():
      parameter = key+'.enabled'
      value = self.parameterNode.GetParameter(parameter)=='True'
      if checkbox.checked!=value:
        checkbox.blockSignals(True)
        checkbox.checked = value
        checkbox.blockSignals(False)

  def updateParameterNodeFromGui(self):
    if not self.parameterNode:
      return
    for (key, checkbox) in self.requestedKeysCheckboxes.iteritems():
      parameter = key+'.enabled'
      newValue = str(checkbox.checked)
      currentValue = self.parameterNode.GetParameter(parameter)
      if not currentValue or currentValue!=newValue:
        self.parameterNode.SetParameter(parameter, newValue)

  def requestAll(self):
    if not self.parameterNode:
      return
    for (key, checkbox) in self.requestedKeysCheckboxes.iteritems():
      parameter = key+'.enabled'
      newValue = str(True)
      currentValue = self.parameterNode.GetParameter(parameter)
      if not currentValue or currentValue!=newValue:
        self.parameterNode.SetParameter(parameter, newValue)

  def requestNone(self):
    if not self.parameterNode:
      return
    for (key, checkbox) in self.requestedKeysCheckboxes.iteritems():
      parameter = key+'.enabled'
      newValue = str(False)
      currentValue = self.parameterNode.GetParameter(parameter)
      if not currentValue or currentValue!=newValue:
        self.parameterNode.SetParameter(parameter, newValue)

  def requestDefault(self):
    if not self.parameterNode:
      return
    self.setDefaultParameters(self.parameterNode,overwriteExisting=True)

class SegmentLabelmapStatisticsCalculator(SegmentStatisticsCalculatorBase):

  def __init__(self):
    super(SegmentLabelmapStatisticsCalculator,self).__init__()
    self.name = "Labelmap Statistics"
    self.keys = ("LM voxel count", "LM volume mm3", "LM volume cc")
    self.defaultKeys = ("LM voxel count", "LM volume mm3", "LM volume cc") # calculate all measurements by default
    super(SegmentLabelmapStatisticsCalculator,self).createDefaultOptionsWidget()
    #... developer may add extra options to configure other parameters

  def computeStatistics(self, segmentationNode, segmentID, grayscaleNode=None):
    import vtkSegmentationCorePython as vtkSegmentationCore
    requestedKeys = self.getRequestedKeys()

    if len(requestedKeys)==0:
      return {}

    containsLabelmapRepresentation = segmentationNode.GetSegmentation().ContainsRepresentation(
      vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName())
    if not containsLabelmapRepresentation:
      return {}

    segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
    segmentLabelmap = segment.GetRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName())

    # We need to know exactly the value of the segment voxels, apply threshold to make force the selected label value
    labelValue = 1
    backgroundValue = 0
    thresh = vtk.vtkImageThreshold()
    thresh.SetInputData(segmentLabelmap)
    thresh.ThresholdByLower(0)
    thresh.SetInValue(backgroundValue)
    thresh.SetOutValue(labelValue)
    thresh.SetOutputScalarType(vtk.VTK_UNSIGNED_CHAR)
    thresh.Update()

    #  Use binary labelmap as a stencil
    stencil = vtk.vtkImageToImageStencil()
    stencil.SetInputData(thresh.GetOutput())
    stencil.ThresholdByUpper(labelValue)
    stencil.Update()

    stat = vtk.vtkImageAccumulate()
    stat.SetInputData(thresh.GetOutput())
    stat.SetStencilData(stencil.GetOutput())
    stat.Update()

    # Add data to statistics list
    cubicMMPerVoxel = reduce(lambda x,y: x*y, segmentLabelmap.GetSpacing())
    ccPerCubicMM = 0.001
    stats = {}
    if "LM voxel count" in requestedKeys:
      stats["LM voxel count"] = stat.GetVoxelCount()
    if "LM volume mm3" in requestedKeys:
      stats["LM volume mm3"] = stat.GetVoxelCount() * cubicMMPerVoxel
    if "LM volume cc" in requestedKeys:
      stats["LM volume cc"] = stat.GetVoxelCount() * cubicMMPerVoxel* ccPerCubicMM
    return stats

  def getMeasurementInfo(self, key, segmentationNode=None, grayscaleNode=None):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    info = {}
    info["LM voxel count"] = {"name": "voxel count", "description": "number of voxels", "units": None}
    info["LM volume mm3"] = {"name": "volume", "description": "volume in mm3", "units": "mm3"}
    info["LM volume cc"] =  {"name": "volume", "description": "volume in cc", "units": "cc"}
    return info[key] if key in info else None

class SegmentGrayscaleVolumeStatisticsCalculator(SegmentStatisticsCalculatorBase):

  def __init__(self):
    super(SegmentGrayscaleVolumeStatisticsCalculator,self).__init__()
    self.name = "Grayscale Volume Statistics"
    self.keys = ("GS voxel count", "GS volume mm3", "GS volume cc", "GS min", "GS max", "GS mean", "GS stdev")
    self.defaultKeys = ("GS voxel count", "GS volume mm3", "GS volume cc", "GS min", "GS max", "GS mean", "GS stdev") # calculate all measurements by default
    super(SegmentGrayscaleVolumeStatisticsCalculator,self).createDefaultOptionsWidget()
    #... developer may add extra options to configure other parameters

  def computeStatistics(self, segmentationNode, segmentID, grayscaleNode):
    import vtkSegmentationCorePython as vtkSegmentationCore
    requestedKeys = self.getRequestedKeys()

    if len(requestedKeys)==0:
      return {}

    containsLabelmapRepresentation = segmentationNode.GetSegmentation().ContainsRepresentation(
      vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName())
    if not containsLabelmapRepresentation:
      return {}

    if grayscaleNode is None or grayscaleNode.GetImageData() is None:
      return {}

    # Get geometry of grayscale volume node as oriented image data
    referenceGeometry_Reference = vtkSegmentationCore.vtkOrientedImageData() # reference geometry in reference node coordinate system
    referenceGeometry_Reference.SetExtent(grayscaleNode.GetImageData().GetExtent())
    ijkToRasMatrix = vtk.vtkMatrix4x4()
    grayscaleNode.GetIJKToRASMatrix(ijkToRasMatrix)
    referenceGeometry_Reference.SetGeometryFromImageToWorldMatrix(ijkToRasMatrix)

    # Get transform between grayscale volume and segmentation
    segmentationToReferenceGeometryTransform = vtk.vtkGeneralTransform()
    slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(segmentationNode.GetParentTransformNode(),
      grayscaleNode.GetParentTransformNode(), segmentationToReferenceGeometryTransform)

    cubicMMPerVoxel = reduce(lambda x,y: x*y, referenceGeometry_Reference.GetSpacing())
    ccPerCubicMM = 0.001

    segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
    segmentLabelmap = segment.GetRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName())

    segmentLabelmap_Reference = vtkSegmentationCore.vtkOrientedImageData()
    vtkSegmentationCore.vtkOrientedImageDataResample.ResampleOrientedImageToReferenceOrientedImage(
    segmentLabelmap, referenceGeometry_Reference, segmentLabelmap_Reference,
    False, # nearest neighbor interpolation
    False, # no padding
    segmentationToReferenceGeometryTransform)

    # We need to know exactly the value of the segment voxels, apply threshold to make force the selected label value
    labelValue = 1
    backgroundValue = 0
    thresh = vtk.vtkImageThreshold()
    thresh.SetInputData(segmentLabelmap_Reference)
    thresh.ThresholdByLower(0)
    thresh.SetInValue(backgroundValue)
    thresh.SetOutValue(labelValue)
    thresh.SetOutputScalarType(vtk.VTK_UNSIGNED_CHAR)
    thresh.Update()

    #  Use binary labelmap as a stencil
    stencil = vtk.vtkImageToImageStencil()
    stencil.SetInputData(thresh.GetOutput())
    stencil.ThresholdByUpper(labelValue)
    stencil.Update()

    stat = vtk.vtkImageAccumulate()
    stat.SetInputData(grayscaleNode.GetImageData())
    stat.SetStencilData(stencil.GetOutput())
    stat.Update()

    # create statistics list
    stats = {}
    if "GS voxel count" in requestedKeys:
      stats["GS voxel count"] = stat.GetVoxelCount()
    if "GS volume mm3" in requestedKeys:
      stats["GS volume mm3"] = stat.GetVoxelCount() * cubicMMPerVoxel
    if "GS volume cc" in requestedKeys:
      stats["GS volume cc"] = stat.GetVoxelCount() * cubicMMPerVoxel * ccPerCubicMM
    if stat.GetVoxelCount()>0:
      if "GS min" in requestedKeys:
        stats["GS min"] = stat.GetMin()[0]
      if "GS max" in requestedKeys:
        stats["GS max"] = stat.GetMax()[0]
      if "GS mean" in requestedKeys:
        stats["GS mean"] = stat.GetMean()[0]
      if "GS stdev" in requestedKeys:
        stats["GS stdev"] = stat.GetStandardDeviation()[0]
    return stats

  def getMeasurementInfo(self, key, segmentationNode=None, grayscaleNode=None):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    info = {}
    info["GS voxel count"] = {"name": "voxel count", "description": "number of voxels", "units": None}
    info["GS volume mm3"] = {"name": "volume", "description": "volume in mm3", "units": "mm3"}
    info["GS volume cc"] = {"name": "volume", "description": "volume in cc", "units": "cc"}
    info["GS min"] = {"name": "minimum", "description": "minimum grayvalue", "units": None}
    info["GS max"] = {"name": "maximum", "description": "maximum grayvalue", "units": None}
    info["GS mean"] = {"name": "mean", "description": "mean grayvalue", "units": None}
    info["GS stdev"] = {"name": "standard deviation", "description": "standard deviation of grayvalues", "units": None}
    return info[key] if key in info else None

class SegmentClosedSurfaceStatisticsCalculator(SegmentStatisticsCalculatorBase):

  def __init__(self):
    super(SegmentClosedSurfaceStatisticsCalculator,self).__init__()
    self.name = "Closed Surface Statistics"
    self.keys = ("CS surface mm2", "CS volume mm3", "CS volume cc")
    self.defaultKeys = ("CS surface mm2", "CS volume mm3", "CS volume cc") # calculate all measurements by default
    super(SegmentClosedSurfaceStatisticsCalculator,self).createDefaultOptionsWidget()
    #... developer may add extra options to configure other parameters

  def computeStatistics(self, segmentationNode, segmentID, grayscaleNode=None):
    import vtkSegmentationCorePython as vtkSegmentationCore
    requestedKeys = self.getRequestedKeys()

    if len(requestedKeys)==0:
      return {}

    containsClosedSurfaceRepresentation = segmentationNode.GetSegmentation().ContainsRepresentation(
      vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName())
    if not containsClosedSurfaceRepresentation:
      return {}

    segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
    segmentClosedSurface = segment.GetRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName())

    # Compute statistics
    massProperties = vtk.vtkMassProperties()
    massProperties.SetInputData(segmentClosedSurface)

    # Add data to statistics list
    ccPerCubicMM = 0.001
    stats = {}
    if "CS surface mm2" in requestedKeys:
      stats["CS surface mm2"] = massProperties.GetSurfaceArea()
    if "CS volume mm3" in requestedKeys:
      stats["CS volume mm3"] = massProperties.GetVolume()
    if "CS volume cc" in requestedKeys:
      stats["CS volume cc"] = massProperties.GetVolume() * ccPerCubicMM
    return stats

  def getMeasurementInfo(self, key, segmentationNode=None, grayscaleNode=None):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    info = {}
    info["CS surface mm2"] = {"name": "surface", "description": "surface area in mm2", "units": "mm2"}
    info["CS volume mm3"] = {"name": "volume", "description": "volume in mm3", "units": "mm3"}
    info["CS volume cc"] = {"name": "volume", "description": "volume in cc", "units": "cc"}
    return info[key] if key in info else None

#
# SegmentStatisticsLogic
#

class SegmentStatisticsLogic(ScriptedLoadableModuleLogic):
  """Implement the logic to calculate label statistics.
  Nodes are passed in as arguments.
  Results are stored as 'statistics' instance variable.
  Additional 'Calculators' for computation of other statistical measuements may be registered.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  registeredCalculators = [SegmentLabelmapStatisticsCalculator, SegmentGrayscaleVolumeStatisticsCalculator, SegmentClosedSurfaceStatisticsCalculator]

  @staticmethod
  def registerCalculator(calculator):
    """Register a subclass of SegmentStatisticsCalculatorBase for calculation of additional measurements"""
    if not isinstance(calculator, SegmentStatisticsCalculatorBase):
      return
    if not calculator.__class__ in SegmentStatisticsLogic.registeredCalculators:
      SegmentStatisticsLogic.registeredCalculators.append(calculator.__class__)

  def __init__(self, parent = None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    self.calculators = [ x() for x in SegmentStatisticsLogic.registeredCalculators]

    self.isSingletonParameterNode = False
    self.parameterNode = None

    self.keys = ("Segment",)
    self.notAvailableValueString = ""
    self.reset()

  def getParameterNode(self):
    if not self.parameterNode:
      self.setParameterNode( ScriptedLoadableModuleLogic.getParameterNode(self) )
    return self.parameterNode

  def setParameterNode(self, parameterNode):
    """Set the current paramter node and initialize all unset paramters to their default values"""
    if self.parameterNode==parameterNode:
      return
    self.setDefaultParameters(parameterNode)
    self.parameterNode = parameterNode
    for calculator in self.calculators:
      calculator.setParameterNode(parameterNode)

  def setDefaultParameters(self, parameterNode):
    """Set all calculators to enabled and all calculators' parameters to their default value"""
    for calculator in self.calculators:
      parameter = calculator.name+'.enabled'
      if not parameterNode.GetParameter(parameter):
        parameterNode.SetParameter(parameter, str(True))
      calculator.setDefaultParameters(parameterNode)

  def reset(self):
    """Clear all computation results"""
    self.keys = ("Segment",)
    for calculator in self.calculators:
      self.keys += calculator.keys
    self.statistics = {}
    self.statistics["SegmentIDs"] = []

  def computeStatistics(self, segmentationNode, grayscaleNode, visibleSegmentsOnly = True):
    """Compute statistical measures for all (visibile) segments"""
    import vtkSegmentationCorePython as vtkSegmentationCore

    self.reset()

    self.segmentationNode = segmentationNode
    self.grayscaleNode = grayscaleNode

    # Get segment ID list
    visibleSegmentIds = vtk.vtkStringArray()
    if visibleSegmentsOnly:
      self.segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
    else:
      self.segmentationNode.GetSegmentation().GetSegmentIDs(visibleSegmentIds)
    if visibleSegmentIds.GetNumberOfValues() == 0:
      logging.debug("computeStatistics will not return any results: there are no visible segments")

    # update statistics for all segment IDs
    for segmentIndex in range(visibleSegmentIds.GetNumberOfValues()):
      segmentID = visibleSegmentIds.GetValue(segmentIndex)
      self.updateStatisticsForSegment(segmentID, segmentationNode, grayscaleNode)

  def updateStatisticsForSegment(self, segmentID, segmentationNode, grayscaleNode=None):
    """
    Update statistical measures for specified segment.
    Note: This will not change or reset measurement results of other segments
    """
    self.segmentationNode = segmentationNode
    self.grayscaleNode = grayscaleNode

    if not self.segmentationNode.GetSegmentation().GetSegment(segmentID):
      logging.debug("updateStatisticsForSegment will not update any results because the segment doesn't exist")
      return

    segment = self.segmentationNode.GetSegmentation().GetSegment(segmentID)
    if segmentID not in self.statistics["SegmentIDs"]:
      self.statistics["SegmentIDs"].append(segmentID)
    self.statistics[segmentID,"Segment"] = segment.GetName()

    # apply all enabled calculators
    for calculator in self.calculators:
      if self.getParameterNode().GetParameter(calculator.name+'.enabled')=='True':
        stats = calculator.computeStatistics(self.segmentationNode, segmentID, self.grayscaleNode)
        for key in stats:
          self.statistics[segmentID,key] = stats[key]

  def getCalculatorByKey(self, key):
    """Get calculator responsible for obtaining measurement value for given key"""
    for calculator in self.calculators:
      if key in calculator.keys:
        return calculator
    return None

  def getMeasurementInfo(self, key, segmentationNode=None, grayscaleNode=None):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    calculator = self.getCalculatorByKey(key)
    if calculator:
      return calculator.getMeasurementInfo(key, segmentationNode, grayscaleNode)
    return None

  def getStatisticsValueAsString(self, segmentID, key):
    if self.statistics.has_key((segmentID, key)):
      value = self.statistics[segmentID, key]
      if isinstance(value, float):
        return "%0.3f" % value # round to 3 decimals
      else:
        return str(value)
    else:
      return self.notAvailableValueString

  def getNonEmptyKeys(self):
    # Fill columns
    nonEmptyKeys = []
    for key in self.keys:
      for segmentID in self.statistics["SegmentIDs"]:
        if self.statistics.has_key((segmentID, key)):
          nonEmptyKeys.append(key)
          break
    return nonEmptyKeys

  def exportToTable(self, table, nonEmptyKeysOnly = True):
    """
    Export statistics to table node
    """
    tableWasModified = table.StartModify()
    table.RemoveAllColumns()

    keys = self.getNonEmptyKeys() if nonEmptyKeysOnly else self.keys

    # Define table columns
    for k in keys:
      col = table.AddColumn()
      col.SetName(k)
      measurementInfo = self.getMeasurementInfo(k, self.segmentationNode, self.grayscaleNode)
      if measurementInfo:
        for mik, miv in measurementInfo.iteritems():
          if mik=='name':
            table.SetColumnLongName(k, str(miv))
          elif mik=='description':
            table.SetColumnDescription(k, str(miv))
          elif mik=='units':
            table.SetColumnUnitLabel(k, str(miv))
          else:
            table.SetColumnProperty(k, mik, str(miv))

    # Fill columns
    for segmentID in self.statistics["SegmentIDs"]:
      rowIndex = table.AddEmptyRow()
      columnIndex = 0
      for k in keys:
        table.SetCellText(rowIndex, columnIndex, str(self.getStatisticsValueAsString(segmentID, k)))
        columnIndex += 1

    table.Modified()
    table.EndModify(tableWasModified)

  def showTable(self, table):
    """
    Switch to a layou where tables are visible and show the selected table
    """
    currentLayout = slicer.app.layoutManager().layout
    layoutWithTable = slicer.modules.tables.logic().GetLayoutWithTable(currentLayout)
    slicer.app.layoutManager().setLayout(layoutWithTable)
    slicer.app.applicationLogic().GetSelectionNode().SetReferenceActiveTableID(table.GetID())
    slicer.app.applicationLogic().PropagateTableSelection()

  def exportToString(self, nonEmptyKeysOnly = True):
    """
    Returns string with comma separated values, with header keys in quotes.
    """
    keys = self.getNonEmptyKeys() if nonEmptyKeysOnly else self.keys
    # Header
    csv = '"' + '","'.join(keys) + '"'
    # Rows
    for segmentID in self.statistics["SegmentIDs"]:
      csv += "\n" + str(self.statistics[segmentID,keys[0]])
      for key in keys[1:]:
        if self.statistics.has_key((segmentID, key)):
          csv += "," + str(self.statistics[segmentID,key])
        else:
          csv += ","
    return csv

  def exportToCSVFile(self, fileName, nonEmptyKeysOnly = True):
    fp = open(fileName, "w")
    fp.write(self.exportToString(nonEmptyKeysOnly))
    fp.close()

class SegmentStatisticsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self,scenario=None):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SegmentStatisticsBasic()
    self.test_SegmentStatisticsCalculatorPlugins()

  def test_SegmentStatisticsBasic(self):
    """
    This tests some aspects of the label statistics
    """

    self.delayDisplay("Starting test_SegmentStatisticsBasic")

    import vtkSegmentationCorePython as vtkSegmentationCore
    import vtkSlicerSegmentationsModuleLogicPython as vtkSlicerSegmentationsModuleLogic
    import SampleData
    from SegmentStatistics import SegmentStatisticsLogic

    self.delayDisplay("Load master volume")

    sampleDataLogic = SampleData.SampleDataLogic()
    masterVolumeNode = sampleDataLogic.downloadMRBrainTumor1()

    self.delayDisplay("Create segmentation containing a few spheres")

    segmentationNode = slicer.vtkMRMLSegmentationNode()
    slicer.mrmlScene.AddNode(segmentationNode)
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)

    # Geometry for each segment is defined by: radius, posX, posY, posZ
    segmentGeometries = [[10, -6,30,28], [20, 0,65,32], [15, 1, -14, 30], [12, 0, 28, -7], [5, 0,30,64], [12, 31, 33, 27], [17, -42, 30, 27]]
    for segmentGeometry in segmentGeometries:
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(segmentGeometry[0])
      sphereSource.SetCenter(segmentGeometry[1], segmentGeometry[2], segmentGeometry[3])
      sphereSource.Update()
      segmentationNode.AddSegmentFromClosedSurfaceRepresentation (sphereSource.GetOutput(), segmentationNode.GetSegmentation().GenerateUniqueSegmentID("Test"))

    self.delayDisplay("Compute statistics")

    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)

    self.delayDisplay("Check a few numerical results")
    self.assertEqual( segStatLogic.statistics["Test_2","LM voxel count"], 9807)
    self.assertEqual( segStatLogic.statistics["Test_4","GS voxel count"], 380)

    self.delayDisplay("Export results to table")
    resultsTableNode = slicer.vtkMRMLTableNode()
    slicer.mrmlScene.AddNode(resultsTableNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)

    self.delayDisplay("Export results to string")
    logging.info(segStatLogic.exportToString())

    outputFilename = slicer.app.temporaryPath + '/SegmentStatisticsTestOutput.csv'
    self.delayDisplay("Export results to CSV file: "+outputFilename)
    segStatLogic.exportToCSVFile(outputFilename)

    self.delayDisplay('test_SegmentStatisticsBasic passed!')

  def test_SegmentStatisticsCalculatorPlugins(self):
    """
    This tests some aspects of the segment statistics calculator plugins
    """

    self.delayDisplay("Starting test_SegmentStatisticsCalculatorPlugins")

    import vtkSegmentationCorePython as vtkSegmentationCore
    import vtkSlicerSegmentationsModuleLogicPython as vtkSlicerSegmentationsModuleLogic
    import SampleData
    from SegmentStatistics import SegmentStatisticsLogic

    self.delayDisplay("Load master volume")

    sampleDataLogic = SampleData.SampleDataLogic()
    masterVolumeNode = sampleDataLogic.downloadMRBrainTumor1()

    self.delayDisplay("Create segmentation containing a few spheres")

    segmentationNode = slicer.vtkMRMLSegmentationNode()
    slicer.mrmlScene.AddNode(segmentationNode)
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)

    # Geometry for each segment is defined by: radius, posX, posY, posZ
    segmentGeometries = [[10, -6,30,28], [20, 0,65,32], [15, 1, -14, 30], [12, 0, 28, -7], [5, 0,30,64], [12, 31, 33, 27], [17, -42, 30, 27]]
    for segmentGeometry in segmentGeometries:
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(segmentGeometry[0])
      sphereSource.SetCenter(segmentGeometry[1], segmentGeometry[2], segmentGeometry[3])
      sphereSource.Update()
      segment = vtkSegmentationCore.vtkSegment()
      segment.SetName(segmentationNode.GetSegmentation().GenerateUniqueSegmentID("Test"))
      segment.AddRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(), sphereSource.GetOutput())
      segmentationNode.GetSegmentation().AddSegment(segment)

    # test calculating only measurements for selected segments
    self.delayDisplay("Test calculating only measurements for individual segments")
    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.updateStatisticsForSegment('Test_2',segmentationNode, masterVolumeNode)
    resultsTableNode = slicer.vtkMRMLTableNode()
    slicer.mrmlScene.AddNode(resultsTableNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    self.assertEqual( segStatLogic.statistics["Test_2","LM voxel count"], 9807)
    with self.assertRaises(KeyError): segStatLogic.statistics["Test_4","GS voxel count"] # assert there are no result for this segment
    segStatLogic.updateStatisticsForSegment('Test_4',segmentationNode, masterVolumeNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    self.assertEqual( segStatLogic.statistics["Test_2","LM voxel count"], 9807)
    self.assertEqual( segStatLogic.statistics["Test_4","GS voxel count"], 380)
    with self.assertRaises(KeyError): segStatLogic.statistics["Test_5","GS voxel count"] # assert there are no result for this segment

    # calculate measurements for all segments
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)
    self.assertEqual( segStatLogic.statistics["Test","LM voxel count"], 2948)
    self.assertEqual( segStatLogic.statistics["Test_1","LM voxel count"], 23281)

    # test updating measurements for segments one by one
    self.delayDisplay("Update some segments in the segmentation")
    segmentGeometriesNew = [[5, -6,30,28], [21, 0,65,32]]
    for i in range(len(segmentGeometriesNew)):
      segmentGeometry  = segmentGeometriesNew[i]
      sphereSource = vtk.vtkSphereSource()
      sphereSource.SetRadius(segmentGeometry[0])
      sphereSource.SetCenter(segmentGeometry[1], segmentGeometry[2], segmentGeometry[3])
      sphereSource.Update()
      segment = segmentationNode.GetSegmentation().GetNthSegment(i)
      segment.RemoveAllRepresentations()
      segment.AddRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName(), sphereSource.GetOutput())
    self.assertEqual( segStatLogic.statistics["Test","LM voxel count"], 2948)
    self.assertEqual( segStatLogic.statistics["Test_1","LM voxel count"], 23281)
    segStatLogic.updateStatisticsForSegment('Test_1',segmentationNode, masterVolumeNode)
    self.assertEqual( segStatLogic.statistics["Test","LM voxel count"], 2948)
    self.assertTrue( segStatLogic.statistics["Test_1","LM voxel count"]!=23281)
    segStatLogic.updateStatisticsForSegment('Test',segmentationNode, masterVolumeNode)
    self.assertTrue( segStatLogic.statistics["Test","LM voxel count"]!=2948)
    self.assertTrue( segStatLogic.statistics["Test_1","LM voxel count"]!=23281)

    # test enabling/disabling of individual measurements
    self.delayDisplay("Test disabling of individual measurements")
    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.getParameterNode().SetParameter("LM voxel count.enabled",str(False))
    segStatLogic.getParameterNode().SetParameter("LM volume cc.enabled",str(False))
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertFalse('LM voxel count' in columnHeaders)
    self.assertTrue('LM volume mm3' in columnHeaders)
    self.assertFalse('LM volume cc' in columnHeaders)

    self.delayDisplay("Test re-disabling of individual measurements")
    segStatLogic.getParameterNode().SetParameter("LM voxel count.enabled",str(True))
    segStatLogic.getParameterNode().SetParameter("LM volume cc.enabled",str(True))
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertTrue('LM voxel count' in columnHeaders)
    self.assertTrue('LM volume mm3' in columnHeaders)
    self.assertTrue('LM volume cc' in columnHeaders)

    # test enabling/disabling of individual calculators
    self.delayDisplay("Test disabling of calculator")
    segStatLogic.getParameterNode().SetParameter("Labelmap Statistics.enabled",str(False))
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertFalse('LM  voxel count' in columnHeaders)
    self.assertFalse('LM  volume mm3' in columnHeaders)
    self.assertFalse('LM  volume cc' in columnHeaders)

    self.delayDisplay("Test re-enabling of calculator")
    segStatLogic.getParameterNode().SetParameter("Labelmap Statistics.enabled",str(True))
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertTrue('LM voxel count' in columnHeaders)
    self.assertTrue('LM volume mm3' in columnHeaders)
    self.assertTrue('LM volume cc' in columnHeaders)

    # test unregistering/registering of calculators
    self.delayDisplay("Test of removing all registered calculators")
    SegmentStatisticsLogic.registeredCalculators = [] # remove all registered calculators
    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertEqual(len(columnHeaders),1) # only header element should be "Segment"
    self.assertEqual(columnHeaders[0],"Segment") # only header element should be "Segment"

    self.delayDisplay("Test registering calculators")
    SegmentStatisticsLogic.registerCalculator(SegmentLabelmapStatisticsCalculator())
    SegmentStatisticsLogic.registerCalculator(SegmentGrayscaleVolumeStatisticsCalculator())
    SegmentStatisticsLogic.registerCalculator(SegmentClosedSurfaceStatisticsCalculator())
    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.computeStatistics(segmentationNode, masterVolumeNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertTrue('LM voxel count' in columnHeaders)
    self.assertTrue('GS voxel count' in columnHeaders)
    self.assertTrue('CS surface mm2' in columnHeaders)

    self.delayDisplay('test_SegmentStatisticsCalculatorPlugins passed!')

class Slicelet(object):
  """A slicer slicelet is a module widget that comes up in stand alone mode
  implemented as a python class.
  This class provides common wrapper functionality used by all slicer modlets.
  """
  # TODO: put this in a SliceletLib
  # TODO: parse command line arge

  def __init__(self, widgetClass=None):
    self.parent = qt.QFrame()
    self.parent.setLayout( qt.QVBoxLayout() )

    # TODO: should have way to pop up python interactor
    self.buttons = qt.QFrame()
    self.buttons.setLayout( qt.QHBoxLayout() )
    self.parent.layout().addWidget(self.buttons)
    self.addDataButton = qt.QPushButton("Add Data")
    self.buttons.layout().addWidget(self.addDataButton)
    self.addDataButton.connect("clicked()",slicer.app.ioManager().openAddDataDialog)
    self.loadSceneButton = qt.QPushButton("Load Scene")
    self.buttons.layout().addWidget(self.loadSceneButton)
    self.loadSceneButton.connect("clicked()",slicer.app.ioManager().openLoadSceneDialog)

    if widgetClass:
      self.widget = widgetClass(self.parent)
      self.widget.setup()
    self.parent.show()

class SegmentStatisticsSlicelet(Slicelet):
  """ Creates the interface when module is run as a stand alone gui app.
  """

  def __init__(self):
    super(SegmentStatisticsSlicelet,self).__init__(SegmentStatisticsWidget)

#
# Class for avoiding python error that is caused by the method SegmentStatistics::setup
# http://www.na-mic.org/Bug/view.php?id=3871
#
class SegmentStatisticsFileWriter:
  def __init__(self, parent):
    pass


if __name__ == "__main__":
  # TODO: need a way to access and parse command line arguments
  # TODO: ideally command line args should handle --xml

  import sys
  print( sys.argv )

  slicelet = SegmentStatisticsSlicelet()
