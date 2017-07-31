import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from SegmentStatisticsCalculators import *

#
# SegmentStatistics
#

class SegmentStatistics(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Segment Statistics"
    self.parent.categories = ["Quantification"]
    self.parent.dependencies = ["SubjectHierarchy"]
    self.parent.contributors = ["Andras Lasso (PerkLab), Christian Bauer (University of Iowa), Steve Pieper (Isomics)"]
    self.parent.helpText = """
Use this module to calculate counts and volumes for segments plus statistics on the grayscale background volume.
Computed fields:
Segment labelmap statistics (LM): voxel count, volume mm3, volume cc.
Requires segment labelmap representation.
Scalar volume statistics (SV): voxel count, volume mm3, volume cc (where segments overlap scalar volume),
min, max, mean, stdev (intensity statistics).
Requires segment labelmap representation and selection of a scalar volume
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
    
    import SegmentStatisticsCalculators

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

    # Scalar volume selector
    self.scalarSelector = slicer.qMRMLNodeComboBox()
    self.scalarSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.scalarSelector.addEnabled = False
    self.scalarSelector.removeEnabled = True
    self.scalarSelector.renameEnabled = True
    self.scalarSelector.noneEnabled = True
    self.scalarSelector.showChildNodeTypes = False
    self.scalarSelector.setMRMLScene( slicer.mrmlScene )
    self.scalarSelector.setToolTip( "Select the scalar volume for intensity statistics calculations")
    inputsFormLayout.addRow("Scalar volume:", self.scalarSelector)

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

    # Edit parameter set button to open SegmentStatisticsParameterEditorDialog
    # Note: we add the calculators' option widgets to the module widget instead of using the editor dialog
    #self.editParametersButton = qt.QPushButton("Edit Parameter Set")
    #self.editParametersButton.toolTip = "Editor Statistics Calculator Parameter Set."
    #self.parametersLayout.addRow(self.editParametersButton)
    #self.editParametersButton.connect('clicked()', self.onEditParameters)
    # add caclulator's option widgets
    self.addCalculatorOptionWidgets()

    # Add vertical spacer
    self.parent.layout().addStretch(1)

    # connections
    self.applyButton.connect('clicked()', self.onApply)
    self.scalarSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.segmentationSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.outputTableSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onNodeSelectionChanged)
    self.parameterNodeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onParameterSetSelected)

    self.parameterNodeSelector.setCurrentNode(self.logic.getParameterNode())
    self.onNodeSelectionChanged()
    self.onParameterSetSelected()

  def cleanup(self):
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)

  def onNodeSelectionChanged(self):
    self.applyButton.enabled = (self.segmentationSelector.currentNode() is not None and
                                self.outputTableSelector.currentNode() is not None and
                                self.parameterNodeSelector.currentNode() is not None)
    if self.segmentationSelector.currentNode():
      self.outputTableSelector.baseName = self.segmentationSelector.currentNode().GetName() + ' statistics'

  def onApply(self):
    """Calculate the label statistics
    """
    # Lock GUI
    self.applyButton.text = "Working..."
    self.applyButton.setEnabled(False)
    slicer.app.processEvents()
    # set up parameters for computation
    self.logic.getParameterNode().SetParameter("Segmentation", self.segmentationSelector.currentNode().GetID())
    if self.scalarSelector.currentNode():
      self.logic.getParameterNode().SetParameter("ScalarVolume", self.scalarSelector.currentNode().GetID())
    else:
      self.logic.getParameterNode().UnsetParameter("ScalarVolume")
    self.logic.getParameterNode().SetParameter("MeasurementsTable", self.outputTableSelector.currentNode().GetID())
    # Compute statistics
    self.logic.computeStatistics()
    self.logic.exportToTable(self.outputTableSelector.currentNode())
    # Unlock GUI
    self.applyButton.setEnabled(True)
    self.applyButton.text = "Apply"

    self.logic.showTable(self.outputTableSelector.currentNode())

  def onEditParameters(self, calculatorName=None):
    """Open dialog box to edit calculator's parameters"""
    if self.parameterNodeSelector.currentNode():
      SegmentStatisticsParameterEditorDialog.editParameters(self.parameterNodeSelector.currentNode(),calculatorName)

  def addCalculatorOptionWidgets(self):
    self.calculatorEnabledCheckboxes = {}
    self.parametersLayout.addRow(qt.QLabel("Enabled segment statistics calculators:"))
    for calculator in self.logic.calculators:
      checkbox = qt.QCheckBox(calculator.name+" Statistics")
      checkbox.checked = True
      checkbox.connect('stateChanged(int)', self.updateParameterNodeFromGui)
      optionButton = qt.QPushButton("Options")
      from functools import partial
      optionButton.connect('clicked()',partial(self.onEditParameters, calculator.name))
      editWidget = qt.QWidget()
      editWidget.setLayout(qt.QHBoxLayout())
      editWidget.layout().margin = 0
      editWidget.layout().addWidget(checkbox, 0)
      editWidget.layout().addStretch(1)
      editWidget.layout().addWidget(optionButton, 0)
      self.calculatorEnabledCheckboxes[calculator.name] = checkbox
      self.parametersLayout.addRow(editWidget)
    # embed widgets for editing calculators' parameters
    #for calculator in self.logic.calculators:
    #  calculatorOptionsCollapsibleButton = ctk.ctkCollapsibleGroupBox()
    #  calculatorOptionsCollapsibleButton.setTitle( calculator.name )
    #  calculatorOptionsFormLayout = qt.QFormLayout(calculatorOptionsCollapsibleButton)
    #  calculatorOptionsFormLayout.addRow(calculator.optionsWidget)
    #  self.parametersLayout.addRow(calculatorOptionsCollapsibleButton)

  def onParameterSetSelected(self):
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)
    self.parameterNode = self.parameterNodeSelector.currentNode()
    if self.parameterNode:
      self.logic.setParameterNode(self.parameterNode)
      self.parameterNodeObserver = self.parameterNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateGuiFromParameterNode)

  def updateGuiFromParameterNode(self, caller=None, event=None):
    if not self.parameterNode:
      return
    for calculator in self.logic.calculators:
      parameter = calculator.name+'.enabled'
      checkbox = self.calculatorEnabledCheckboxes[calculator.name]
      value = self.parameterNode.GetParameter(parameter)=='True'
      if checkbox.checked!=value:
        checkbox.blockSignals(True)
        checkbox.checked = value
        checkbox.blockSignals(False)

  def updateParameterNodeFromGui(self):
    if not self.parameterNode:
      return
    for calculator in self.logic.calculators:
      parameter = calculator.name+'.enabled'
      checkbox = self.calculatorEnabledCheckboxes[calculator.name]
      self.parameterNode.SetParameter(parameter, str(checkbox.checked))

class SegmentStatisticsParameterEditorDialog(qt.QDialog):
    """Dialog to edit parameters of segment statistics calculators.
    Most users will only need to call the static method editParameters(...)
    """

    @staticmethod
    def editParameters(parameterNode, calculatorName=None):
      """Executes a modal dialog to edit a segment statistics parameter node if a calculatorName is specified, only
      options for this calculator are displayed"
      """
      dialog = SegmentStatisticsParameterEditorDialog(parent=None, parameterNode=parameterNode, calculatorName=calculatorName)
      return dialog.exec_()

    def __init__(self,parent=None, parameterNode=None, calculatorName=None):
      super(qt.QDialog,self).__init__(parent)
      self.title = "Edit Segment Statistics Parameters"
      self.parameterNode = parameterNode
      self.calculatorName = calculatorName
      self.logic = SegmentStatisticsLogic() # for access to calculators and editor widgets
      self.setup()

    def setParameterNode(self, parameterNode):
      """Set the parameter node the dialog will operate on"""
      if parameterNode==self.parameterNode:
        return
      self.parameterNode = parameterNode
      self.logic.setParameterNode(self.parameterNode)

    def setup(self):
      self.setLayout(qt.QVBoxLayout())

      self.descriptionLabel = qt.QLabel("Edit segment statistics calculator parameters:",0)

      self.doneButton = qt.QPushButton("Done")
      self.doneButton.toolTip = "Finish editing."
      doneWidget = qt.QWidget(self)
      doneWidget.setLayout(qt.QHBoxLayout())
      doneWidget.layout().addStretch(1)
      doneWidget.layout().addWidget(self.doneButton, 0)

      parametersScrollArea = qt.QScrollArea(self)
      self.parametersWidget = qt.QWidget(parametersScrollArea)
      self.parametersLayout = qt.QFormLayout(self.parametersWidget)
      self._addCalculatorOptionWidgets()
      parametersScrollArea.setWidget(self.parametersWidget)
      parametersScrollArea.widgetResizable = True
      parametersScrollArea.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded )
      parametersScrollArea.setHorizontalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded)

      self.layout().addWidget(self.descriptionLabel,0)
      self.layout().addWidget(parametersScrollArea, 1)
      self.layout().addWidget(doneWidget, 0)
      self.doneButton.connect('clicked()', lambda: self.done(1))

    def _addCalculatorOptionWidgets(self):
      description = "Edit segment statistics calculator parameters:"
      if self.calculatorName:
        description = "Edit "+self.calculatorName+" calculator parameters:"
      self.descriptionLabel.text = description
      if self.calculatorName:
        for calculator in self.logic.calculators:
          if calculator.name==self.calculatorName:
            self.parametersLayout.addRow(calculator.optionsWidget)
      else:
        for calculator in self.logic.calculators:
          calculatorOptionsCollapsibleButton = ctk.ctkCollapsibleGroupBox(self.parametersWidget)
          calculatorOptionsCollapsibleButton.setTitle( calculator.name )
          calculatorOptionsFormLayout = qt.QFormLayout(calculatorOptionsCollapsibleButton)
          calculatorOptionsFormLayout.addRow(calculator.optionsWidget)
          self.parametersLayout.addRow(calculatorOptionsCollapsibleButton)

#
# SegmentStatisticsLogic
#

class SegmentStatisticsLogic(ScriptedLoadableModuleLogic):
  """Implement the logic to calculate label statistics.
  Nodes are passed in as arguments.
  Results are stored as 'statistics' instance variable.
  Additional 'Calculators' for computation of other statistical measurements may be registered.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  registeredCalculators = [LabelmapSegmentStatisticsCalculator, ScalarVolumeSegmentStatisticsCalculator, ClosedSurfaceSegmentStatisticsCalculator]

  @staticmethod
  def registerCalculator(calculator):
    """Register a subclass of SegmentStatisticsCalculatorBase for calculation of additional measurements"""
    if not isinstance(calculator, SegmentStatisticsCalculatorBase):
      return
    if calculator.name.find(".")>0:
      logging.warning("Calculator name should not contain '.' as it might mix calculatorname.measurementkey in the parameter node")
    for key in calculator.keys:
      if key.count(".")>1:
        logging.warning("Calculator keys should not contain extra '.' as it might mix calculatorname.measurementkey in the parameter node")
    if not calculator.__class__ in SegmentStatisticsLogic.registeredCalculators and \
       not calculator.id in [c().id for c in SegmentStatisticsLogic.registeredCalculators]:
      SegmentStatisticsLogic.registeredCalculators.append(calculator.__class__)
    else:
      logging.warning("SegmentStatisticsLogic.registerCalculator will not register calculator because \
                       another calculator with the same name or id has already been registered")

  def __init__(self, parent = None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    self.calculators = [ x() for x in SegmentStatisticsLogic.registeredCalculators]

    self.isSingletonParameterNode = False
    self.parameterNode = None

    self.keys = ("Segment",)
    self.notAvailableValueString = ""
    self.reset()

  def getParameterNode(self):
    """Returns the current parameter node and creates one if it doesn't exist yet"""
    if not self.parameterNode:
      self.setParameterNode( ScriptedLoadableModuleLogic.getParameterNode(self) )
    return self.parameterNode

  def setParameterNode(self, parameterNode):
    """Set the current parameter node and initialize all unset parameters to their default values"""
    if self.parameterNode==parameterNode:
      return
    self.setDefaultParameters(parameterNode)
    self.parameterNode = parameterNode
    for calculator in self.calculators:
      calculator.setParameterNode(parameterNode)

  def setDefaultParameters(self, parameterNode):
    """Set all calculators to enabled and all calculators' parameters to their default value"""
    for calculator in self.calculators:
      calculator.setDefaultParameters(parameterNode)
    if not parameterNode.GetParameter('visibleSegmentsOnly'):
      parameterNode.SetParameter('visibleSegmentsOnly', str(True))

  def getStatistics(self):
    """Get the calculated statistical measurements"""
    params = self.getParameterNode()
    if not hasattr(params,'statistics'):
      params.statistics = {"SegmentIDs": []}
    return params.statistics

  def reset(self):
    """Clear all computation results"""
    self.keys = ("Segment",)
    for calculator in self.calculators:
      self.keys += calculator.keys
    params = self.getParameterNode()
    params.statistics = {"SegmentIDs":[]}

  def computeStatistics(self):
    """Compute statistical measures for all (visible) segments"""
    self.reset()

    segmentationNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("Segmentation"))

    # Get segment ID list
    visibleSegmentIds = vtk.vtkStringArray()
    if self.getParameterNode().GetParameter('visibleSegmentsOnly')=='True':
      segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
    else:
      segmentationNode.GetSegmentation().GetSegmentIDs(visibleSegmentIds)
    if visibleSegmentIds.GetNumberOfValues() == 0:
      logging.debug("computeStatistics will not return any results: there are no visible segments")

    # update statistics for all segment IDs
    for segmentIndex in range(visibleSegmentIds.GetNumberOfValues()):
      segmentID = visibleSegmentIds.GetValue(segmentIndex)
      self.updateStatisticsForSegment(segmentID)

  def updateStatisticsForSegment(self, segmentID):
    """
    Update statistical measures for specified segment.
    Note: This will not change or reset measurement results of other segments
    """
    segmentationNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("Segmentation"))

    if not segmentationNode.GetSegmentation().GetSegment(segmentID):
      logging.debug("updateStatisticsForSegment will not update any results because the segment doesn't exist")
      return

    segment = segmentationNode.GetSegmentation().GetSegment(segmentID)
    statistics = self.getStatistics()
    if segmentID not in statistics["SegmentIDs"]:
      statistics["SegmentIDs"].append(segmentID)
    statistics[segmentID,"Segment"] = segment.GetName()

    # apply all enabled calculators
    for calculator in self.calculators:
      if self.getParameterNode().GetParameter(calculator.name+'.enabled')=='True':
        stats = calculator.computeStatistics(segmentID)
        for key in stats:
          statistics[segmentID,key] = stats[key]

  def getCalculatorByKey(self, key):
    """Get calculator responsible for obtaining measurement value for given key"""
    for calculator in self.calculators:
      if key in calculator.keys:
        return calculator
    return None

  def getMeasurementInfo(self, key):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    calculator = self.getCalculatorByKey(key)
    if calculator:
      return calculator.getMeasurementInfo(key)
    return None

  def getStatisticsValueAsString(self, segmentID, key):
    statistics = self.getStatistics()
    if statistics.has_key((segmentID, key)):
      value = statistics[segmentID, key]
      if isinstance(value, float):
        return "%0.3f" % value # round to 3 decimals
      else:
        return str(value)
    else:
      return self.notAvailableValueString

  def getNonEmptyKeys(self):
    # Fill columns
    statistics = self.getStatistics()
    nonEmptyKeys = []
    for key in self.keys:
      for segmentID in statistics["SegmentIDs"]:
        if statistics.has_key((segmentID, key)):
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

    # Count number of calculators that produced measurements
    calculatorsWithResults = set([self.getCalculatorByKey(k) for k in keys if k is not None])

    # Define table columns
    for key in keys:
      col = table.AddColumn() if key=='Segment' else table.AddColumn(vtk.vtkDoubleArray())
      calculator = self.getCalculatorByKey(key)
      measurementInfo = self.getMeasurementInfo(key)
      columnName =  measurementInfo['name'] if measurementInfo and 'name' in measurementInfo else key
      columnName += ' ['+calculator.id+']' if (calculator and len(calculatorsWithResults)>1) else ''
      col.SetName( columnName )
      if measurementInfo:
        for mik, miv in measurementInfo.iteritems():
          if mik=='name':
            table.SetColumnLongName(columnName, str(miv))
          elif mik=='description':
            table.SetColumnDescription(columnName, str(miv))
          elif mik=='units':
            table.SetColumnUnitLabel(columnName, str(miv))
          else:
            table.SetColumnProperty(columnName, str(mik), str(miv))

    # Fill columns
    statistics = self.getStatistics()
    for segmentID in statistics["SegmentIDs"]:
      rowIndex = table.AddEmptyRow()
      columnIndex = 0
      for key in keys:
        value = statistics[segmentID, key] if statistics.has_key((segmentID, key)) else None
        if value is None and key!='Segment':
          value = float('nan')
        table.GetTable().GetColumn(columnIndex).SetValue(rowIndex, value)
        columnIndex += 1

    table.Modified()
    table.EndModify(tableWasModified)

  def showTable(self, table):
    """
    Switch to a layout where tables are visible and show the selected table
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
    statistics = self.getStatistics()
    for segmentID in statistics["SegmentIDs"]:
      csv += "\n" + str(statistics[segmentID,keys[0]])
      for key in keys[1:]:
        if statistics.has_key((segmentID, key)):
          csv += "," + str(statistics[segmentID,key])
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

    self.setUp()
    self.test_SegmentStatisticsCalculatorPlugins()

  def test_SegmentStatisticsBasic(self):
    """
    This tests some aspects of the label statistics
    """

    self.delayDisplay("Starting test_SegmentStatisticsBasic")

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
    segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
    segStatLogic.getParameterNode().SetParameter("ScalarVolume", masterVolumeNode.GetID())
    segStatLogic.computeStatistics()

    self.delayDisplay("Check a few numerical results")
    self.assertEqual( segStatLogic.getStatistics()["Test_2","Labelmap.voxel_count"], 9807)
    self.assertEqual( segStatLogic.getStatistics()["Test_4","Scalar Volume.voxel_count"], 380)

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
    segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
    segStatLogic.getParameterNode().SetParameter("ScalarVolume", masterVolumeNode.GetID())
    segStatLogic.updateStatisticsForSegment('Test_2')
    resultsTableNode = slicer.vtkMRMLTableNode()
    slicer.mrmlScene.AddNode(resultsTableNode)
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    self.assertEqual( segStatLogic.getStatistics()["Test_2","Labelmap.voxel_count"], 9807)
    with self.assertRaises(KeyError): segStatLogic.getStatistics()["Test_4","Scalar Volume.voxel count"] # assert there are no result for this segment
    segStatLogic.updateStatisticsForSegment('Test_4')
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    self.assertEqual( segStatLogic.getStatistics()["Test_2","Labelmap.voxel_count"], 9807)
    self.assertEqual( segStatLogic.getStatistics()["Test_4","Labelmap.voxel_count"], 380)
    with self.assertRaises(KeyError): segStatLogic.getStatistics()["Test_5","Scalar Volume.voxel count"] # assert there are no result for this segment

    # calculate measurements for all segments
    segStatLogic.computeStatistics()
    self.assertEqual( segStatLogic.getStatistics()["Test","Labelmap.voxel_count"], 2948)
    self.assertEqual( segStatLogic.getStatistics()["Test_1","Labelmap.voxel_count"], 23281)

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
    self.assertEqual( segStatLogic.getStatistics()["Test","Labelmap.voxel_count"], 2948)
    self.assertEqual( segStatLogic.getStatistics()["Test_1","Labelmap.voxel_count"], 23281)
    segStatLogic.updateStatisticsForSegment('Test_1')
    self.assertEqual( segStatLogic.getStatistics()["Test","Labelmap.voxel_count"], 2948)
    self.assertTrue( segStatLogic.getStatistics()["Test_1","Labelmap.voxel_count"]!=23281)
    segStatLogic.updateStatisticsForSegment('Test')
    self.assertTrue( segStatLogic.getStatistics()["Test","Labelmap.voxel_count"]!=2948)
    self.assertTrue( segStatLogic.getStatistics()["Test_1","Labelmap.voxel_count"]!=23281)

    # test enabling/disabling of individual measurements
    self.delayDisplay("Test disabling of individual measurements")
    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
    segStatLogic.getParameterNode().SetParameter("ScalarVolume", masterVolumeNode.GetID())
    segStatLogic.getParameterNode().SetParameter("Labelmap.voxel_count.enabled",str(False))
    segStatLogic.getParameterNode().SetParameter("Labelmap.volume_cc.enabled",str(False))
    segStatLogic.computeStatistics()
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertFalse('voxel count [LM]' in columnHeaders)
    self.assertTrue('volume mm3 [LM]' in columnHeaders)
    self.assertFalse('volume cc [LM]' in columnHeaders)

    self.delayDisplay("Test re-enabling of individual measurements")
    segStatLogic.getParameterNode().SetParameter("Labelmap.voxel_count.enabled",str(True))
    segStatLogic.getParameterNode().SetParameter("Labelmap.volume_cc.enabled",str(True))
    segStatLogic.computeStatistics()
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertTrue('voxel count [LM]' in columnHeaders)
    self.assertTrue('volume mm3 [LM]' in columnHeaders)
    self.assertTrue('volume cc [LM]' in columnHeaders)

    # test enabling/disabling of individual calculators
    self.delayDisplay("Test disabling of calculator")
    segStatLogic.getParameterNode().SetParameter("Labelmap.enabled",str(False))
    segStatLogic.computeStatistics()
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertFalse('voxel count [LM]' in columnHeaders)
    self.assertFalse('volume mm3 [LM]' in columnHeaders)
    self.assertFalse('volume cc [LM]' in columnHeaders)

    self.delayDisplay("Test re-enabling of calculator")
    segStatLogic.getParameterNode().SetParameter("Labelmap.enabled",str(True))
    segStatLogic.computeStatistics()
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertTrue('voxel count [LM]' in columnHeaders)
    self.assertTrue('volume mm3 [LM]' in columnHeaders)
    self.assertTrue('volume cc [LM]' in columnHeaders)

    # test unregistering/registering of calculators
    self.delayDisplay("Test of removing all registered calculators")
    SegmentStatisticsLogic.registeredCalculators = [] # remove all registered calculators
    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
    segStatLogic.getParameterNode().SetParameter("ScalarVolume", masterVolumeNode.GetID())
    segStatLogic.computeStatistics()
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertEqual(len(columnHeaders),1) # only header element should be "Segment"
    self.assertEqual(columnHeaders[0],"Segment") # only header element should be "Segment"

    self.delayDisplay("Test registering calculators")
    SegmentStatisticsLogic.registerCalculator(LabelmapSegmentStatisticsCalculator())
    SegmentStatisticsLogic.registerCalculator(ScalarVolumeSegmentStatisticsCalculator())
    SegmentStatisticsLogic.registerCalculator(ClosedSurfaceSegmentStatisticsCalculator())
    segStatLogic = SegmentStatisticsLogic()
    segStatLogic.getParameterNode().SetParameter("Segmentation", segmentationNode.GetID())
    segStatLogic.getParameterNode().SetParameter("ScalarVolume", masterVolumeNode.GetID())
    segStatLogic.computeStatistics()
    segStatLogic.exportToTable(resultsTableNode)
    segStatLogic.showTable(resultsTableNode)
    columnHeaders = [resultsTableNode.GetColumnName(i) for i in range(resultsTableNode.GetNumberOfColumns())]
    self.assertTrue('voxel count [LM]' in columnHeaders)
    self.assertTrue('voxel count [SV]' in columnHeaders)
    self.assertTrue('surface mm2 [CS]' in columnHeaders)

    self.delayDisplay('test_SegmentStatisticsCalculatorPlugins passed!')


class Slicelet(object):
  """A slicer slicelet is a module widget that comes up in stand alone mode
  implemented as a python class.
  This class provides common wrapper functionality used by all slicer modlets.
  """
  # TODO: put this in a SliceletLib
  # TODO: parse command line args

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
