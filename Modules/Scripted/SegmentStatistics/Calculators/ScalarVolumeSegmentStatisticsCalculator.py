import vtk, slicer
from SegmentStatisticsCalculators import SegmentStatisticsCalculatorBase


class ScalarVolumeSegmentStatisticsCalculator(SegmentStatisticsCalculatorBase):
  """Statistical calculator for segmentations with scalar volumes"""

  def __init__(self):
    super(ScalarVolumeSegmentStatisticsCalculator,self).__init__()
    self.name = "Scalar Volume"
    self.id = "SV"
    self.keys = tuple(self.name+'.'+m for m in ("voxel_count", "volume_mm3", "volume_cc", "min", "max", "mean", "stdev"))
    self.defaultKeys = self.keys # calculate all measurements by default
    #... developer may add extra options to configure other parameters

  def computeStatistics(self, segmentID):
    import vtkSegmentationCorePython as vtkSegmentationCore
    requestedKeys = self.getRequestedKeys()

    segmentationNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("Segmentation"))
    grayscaleNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("ScalarVolume"))

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
    if "Scalar Volume.voxel_count" in requestedKeys:
      stats["Scalar Volume.voxel_count"] = stat.GetVoxelCount()
    if "Scalar Volume.volume_mm3" in requestedKeys:
      stats["Scalar Volume.volume_mm3"] = stat.GetVoxelCount() * cubicMMPerVoxel
    if "Scalar Volume.volume_cc" in requestedKeys:
      stats["Scalar Volume.volume_cc"] = stat.GetVoxelCount() * cubicMMPerVoxel * ccPerCubicMM
    if stat.GetVoxelCount()>0:
      if "Scalar Volume.min" in requestedKeys:
        stats["Scalar Volume.min"] = stat.GetMin()[0]
      if "Scalar Volume.max" in requestedKeys:
        stats["Scalar Volume.max"] = stat.GetMax()[0]
      if "Scalar Volume.mean" in requestedKeys:
        stats["Scalar Volume.mean"] = stat.GetMean()[0]
      if "Scalar Volume.stdev" in requestedKeys:
        stats["Scalar Volume.stdev"] = stat.GetStandardDeviation()[0]
    return stats

  def getMeasurementInfo(self, key):

    scalarVolumeNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("ScalarVolume"))

    try:
      scalarVolumeQuantity = scalarVolumeNode.GetVoxelValueQuantity()
      scalarVolumeUnits = scalarVolumeNode.GetVoxelValueUnits()
    except AttributeError:
      scalarVolumeQuantity = self.initCodedEntry("", "", "")
      scalarVolumeUnits = self.initCodedEntry("", "", "")

    noUnits = self.initCodedEntry("1", "UCUM", "no units", True)

    info = dict()

    """Get information (name, description, units, ...) about the measurement for the given key"""

    info["Scalar Volume.voxel_count"] = \
      self.generateMeasurementInfo(name="voxel count", description="number of voxels", units="voxels",
                                   quantityCode=self.initCodedEntry("nvoxels", "99QIICR", "Number of voxels", True),
                                   unitsCode=self.initCodedEntry("\{voxels\}", "UCUM", "voxels", True))

    info["Scalar Volume.volume_mm3"] = \
      self.generateMeasurementInfo(name="volume mm3", description="volume in mm3", units="mm3",
                                   quantityCode=self.initCodedEntry("G-D705", "SRT", "Volume", True),
                                   unitsCode=self.initCodedEntry("mm3", "UCUM", "cubic millimeter", True))

    info["Scalar Volume.volume_cc"] = \
      self.generateMeasurementInfo(name="volume cc", description="volume in cc", units="cc",
                                   quantityCode=self.initCodedEntry("G-D705", "SRT", "Volume", True),
                                   unitsCode=self.initCodedEntry("cm3","UCUM","cubic centimeter", True),
                                   measurementMethodCode=self.initCodedEntry("126030", "DCM",
                                                                             "Sum of segmented voxel volumes", True))

    info["Scalar Volume.min"] = \
      self.generateMeasurementInfo(name="minimum", description="minimum scalar value",
                                   units=scalarVolumeUnits.GetCodeMeaning(),
                                   quantityCode=scalarVolumeQuantity.GetAsString(),
                                   unitsCode=scalarVolumeUnits.GetAsString(),
                                   derivationCode=self.initCodedEntry("R-404FB", "SRT", "Minimum", True))

    info["Scalar Volume.max"] = \
      self.generateMeasurementInfo(name="maximum", description="maximum scalar value",
                                    units=scalarVolumeUnits.GetCodeMeaning(),
                                    quantityCode=scalarVolumeQuantity.GetAsString(),
                                    unitsCode=scalarVolumeUnits.GetAsString(),
                                    derivationCode=self.initCodedEntry("G-A437","SRT","Maximum", True))

    info["Scalar Volume.mean"] = \
      self.generateMeasurementInfo(name="mean", description="mean scalar value",
                                   units=scalarVolumeUnits.GetCodeMeaning(),
                                   quantityCode=scalarVolumeQuantity.GetAsString(),
                                   unitsCode=scalarVolumeUnits.GetAsString(),
                                   derivationCode=self.initCodedEntry("R-00317","SRT","Mean", True))

    info["Scalar Volume.stdev"] = \
      self.generateMeasurementInfo(name="standard deviation", description="standard deviation of scalar values",
                                   units=scalarVolumeUnits.GetCodeMeaning(),
                                   quantityCode=scalarVolumeQuantity.GetAsString(),
                                   unitsCode=scalarVolumeUnits.GetAsString(),
                                   derivationCode=self.getDICOMTriplet('R-10047','SRT','Standard Deviation'))

    return info[key] if key in info else None
