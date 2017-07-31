import vtk
import slicer
from SegmentStatisticsCalculators import SegmentStatisticsCalculatorBase


class LabelmapSegmentStatisticsCalculator(SegmentStatisticsCalculatorBase):
  """Statistical calculator for Labelmaps"""

  def __init__(self):
    super(LabelmapSegmentStatisticsCalculator,self).__init__()
    self.name = "Labelmap"
    self.id = "LM"
    self.keys = tuple(self.name+'.'+m for m in ("voxel_count", "volume_mm3", "volume_cc"))
    self.defaultKeys = self.keys # calculate all measurements by default
    super(LabelmapSegmentStatisticsCalculator,self).createDefaultOptionsWidget()
    #... developer may add extra options to configure other parameters

  def computeStatistics(self, segmentID):
    import vtkSegmentationCorePython as vtkSegmentationCore
    requestedKeys = self.getRequestedKeys()

    segmentationNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("Segmentation"))

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
    if "Labelmap.voxel_count" in requestedKeys:
      stats["Labelmap.voxel_count"] = stat.GetVoxelCount()
    if "Labelmap.volume_mm3" in requestedKeys:
      stats["Labelmap.volume_mm3"] = stat.GetVoxelCount() * cubicMMPerVoxel
    if "Labelmap.volume_cc" in requestedKeys:
      stats["Labelmap.volume_cc"] = stat.GetVoxelCount() * cubicMMPerVoxel* ccPerCubicMM
    return stats

  def getMeasurementInfo(self, key):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    info = {}
    info["Labelmap.voxel_count"] = {"name": "voxel count", "description": "number of voxels", "units": None}
    info["Labelmap.volume_mm3"] = {"name": "volume mm3", "description": "volume in mm3", "units": "mm3"}
    info["Labelmap.volume_cc"] =  {"name": "volume cc", "description": "volume in cc", "units": "cc"}
    return info[key] if key in info else None

