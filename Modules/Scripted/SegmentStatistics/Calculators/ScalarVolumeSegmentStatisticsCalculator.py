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
    super(ScalarVolumeSegmentStatisticsCalculator,self).createDefaultOptionsWidget()
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
    """Get information (name, description, units, ...) about the measurement for the given key"""
    info = {}
    info["Scalar Volume.voxel_count"] = {"name": "voxel count", "description": "number of voxels", "units": None}
    info["Scalar Volume.volume_mm3"] = {"name": "volume mm3", "description": "volume in mm3", "units": "mm3"}
    info["Scalar Volume.volume_cc"] = {"name": "volume cc", "description": "volume in cc", "units": "cc", 'DICOM.QuantityCode': self.getDICOMTriplet('G-D705','SRT','Volume'), 'DICOM.MeasurementMethodCode': self.getDICOMTriplet('126030','DCM','Sum of segmented voxel volumes'), 'DICOM.UnitsCode': self.getDICOMTriplet('ml','UCUM','Milliliter')}
    info["Scalar Volume.min"] = {"name": "minimum", "description": "minimum scalar value", "units": None, 'DICOM.DerivationCode': self.getDICOMTriplet('R-404FB','SRT','Minimum')}
    info["Scalar Volume.max"] = {"name": "maximum", "description": "maximum scalar value", "units": None, 'DICOM.DerivationCode': self.getDICOMTriplet('G-A437','SRT','Maximum')}
    info["Scalar Volume.mean"] = {"name": "mean", "description": "mean scalar value", "units": None, 'DICOM.DerivationCode': self.getDICOMTriplet('R-00317','SRT','Mean')}
    info["Scalar Volume.stdev"] = {"name": "standard deviation", "description": "standard deviation of scalar values", "units": None, 'DICOM.DerivationCode': self.getDICOMTriplet('R-10047','SRT','Standard Deviation')}
    return info[key] if key in info else None

