import vtk
import slicer
from SegmentStatisticsCalculators import SegmentStatisticsCalculatorBase


class ClosedSurfaceSegmentStatisticsCalculator(SegmentStatisticsCalculatorBase):
  """Statistical calculator for closed surfaces"""

  def __init__(self):
    super(ClosedSurfaceSegmentStatisticsCalculator,self).__init__()
    self.name = "Closed Surface"
    self.id = "CS"
    self.keys = tuple(self.name+'.'+m for m in ("surface_mm2", "volume_mm3", "volume_cc"))
    self.defaultKeys = self.keys # calculate all measurements by default
    super(ClosedSurfaceSegmentStatisticsCalculator,self).createDefaultOptionsWidget()
    #... developer may add extra options to configure other parameters

  def computeStatistics(self, segmentID):
    import vtkSegmentationCorePython as vtkSegmentationCore
    requestedKeys = self.getRequestedKeys()

    segmentationNode = slicer.mrmlScene.GetNodeByID(self.getParameterNode().GetParameter("Segmentation"))

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
    if "Closed Surface.surface_mm2" in requestedKeys:
      stats["Closed Surface.surface_mm2"] = massProperties.GetSurfaceArea()
    if "Closed Surface.volume_mm3" in requestedKeys:
      stats["Closed Surface.volume_mm3"] = massProperties.GetVolume()
    if "Closed Surface.volume_cc" in requestedKeys:
      stats["Closed Surface.volume_cc"] = massProperties.GetVolume() * ccPerCubicMM
    return stats

  def getMeasurementInfo(self, key):
    """Get information (name, description, units, ...) about the measurement for the given key"""
    info = {}

    # I searched BioPortal, and found seemingly most suitable code.
    # Prefixed with "99" since CHEMINF is not a recognized DICOM coding scheme.
    # See https://bioportal.bioontology.org/ontologies/CHEMINF?p=classes&conceptid=http%3A%2F%2Fsemanticscience.org%2Fresource%2FCHEMINF_000247
    #
    info["Closed Surface.surface_mm2"] = { \
      "name": "surface mm2", \
      "description": "surface area in mm2", \
      "units": "mm2", \
      'DICOM.QuantityCode': initCodedEntry("000247", "99CHEMINF", "surface area"),\
      'DICOM.UnitsCode': initCodedEntry("mm2", "UCUM", "squared millimeters") \
      }

    info["Closed Surface.volume_mm3"] = {\
      "name": "volume mm3", \
      "description": "volume in mm3", \
      "units": "mm3", \
      'DICOM.QuantityCode': initCodedEntry("G-D705", "SRT", "Volume"),\
      'DICOM.UnitsCode': initCodedEntry("mm3", "UCUM", "cubic millimeter") \
    }

    info["Closed Surface.volume_cc"] = {\
      "name": "volume cc", \
      "description": "volume in cc", \
      "units": "cc", \
      'DICOM.QuantityCode': initCodedEntry("G-D705", "SRT", "Volume"),\
      'DICOM.UnitsCode': initCodedEntry("cm3", "UCUM", "cubic centimeter") \
    }

    return info[key] if key in info else None
