import vtk
import qt

def initCodedEntry(codeValue, codingScheme, codeMeaning):
  entry = slicer.vtkCodedEntry()
  entry.SetValueSchemeMeaning(codeValue, codingScheme, codeMeaning)
  return entry

class SegmentStatisticsCalculatorBase(object):
  """Base class for statistics calculators operating on segments.
  Derived classes should specify: self.name, self.keys, self.defaultKeys
  and implement: computeStatistics, getMeasurementInfo
  """
  def __init__(self):
    self.name = "" # name of the statistics calculator
    self.id = "" # short unique identifier for calculator to distinguish between similar measurements by different calculators
    self.keys = () # keys for all supported measurements; should have format "CalculatorName.measurement"; e.g. "Labelmap.volume cc"
    self.defaultKeys = () # measurements that will be enabled by default
    self.optionsWidget = qt.QWidget()
    self.requestedKeysCheckboxes = {}
    self.parameterNode = None
    self.parameterNodeObserver = None

  def __del__(self):
    if self.parameterNode and self.parameterNodeObserver:
      self.parameterNode.RemoveObserver(self.parameterNodeObserver)

  def computeStatistics(self, segmentID):
    """Compute measurements for requested keys on the given segment"""
    stats = {}
    #segmentationNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("Segmentation"))
    #grayscaleNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("ScalarVolume"))
    #for key in self.getRequestedKeys():
    #  stats[key] = ...
    return stats

  def getMeasurementInfo(self, key):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    if key not in self.keys:
      return None
    if key.startswith(self.name+'.'):
      key = key[len(self.name+'.'):]
    return {"name": key, "description": key, "units": None}

  def getDICOMTriplet(self, codeValue, codingSchemeDesignator, codeMeaning):
    """Utility method to form DICOM triplets in getMeasurementInfo"""
    return {'CodeValue':codeValue,
            'CodingSchemeDesignator': codingSchemeDesignator,
            'CodeMeaning': codeMeaning}

  def setDefaultParameters(self, parameterNode, overwriteExisting=False):
    # enable calculator
    parameter = self.name+'.enabled'
    if not parameterNode.GetParameter(parameter):
      parameterNode.SetParameter(parameter, str(True))
    # enable all default keys
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

    # checkbox to enable/disable calculator
    self.calculatorCheckbox = qt.QCheckBox(self.name+" calculator enabled")
    self.calculatorCheckbox.checked = True
    self.calculatorCheckbox.connect('stateChanged(int)', self.updateParameterNodeFromGui)
    form.addRow(self.calculatorCheckbox)

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
    isEnabled = self.parameterNode.GetParameter(self.name+'.enabled')!='False'
    self.calculatorCheckbox.checked = isEnabled
    for (key, checkbox) in self.requestedKeysCheckboxes.iteritems():
      parameter = key+'.enabled'
      value = self.parameterNode.GetParameter(parameter)=='True'
      if checkbox.checked!=value:
        checkbox.blockSignals(True)
        checkbox.checked = value
        checkbox.blockSignals(False)
      if checkbox.enabled!=isEnabled:
        checkbox.blockSignals(True)
        checkbox.enabled = isEnabled
        checkbox.blockSignals(False)

  def updateParameterNodeFromGui(self):
    if not self.parameterNode:
      return
    self.parameterNode.SetParameter(self.name+'.enabled',str(self.calculatorCheckbox.checked))
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
