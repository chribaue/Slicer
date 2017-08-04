set(${MODULE_NAME}Calculators_PYTHON_SCRIPTS
  #${MODULE_NAME}Calculators
  __init__
  ${MODULE_NAME}CalculatorBase
  Labelmap${MODULE_NAME}Calculator
  ScalarVolume${MODULE_NAME}Calculator
  ClosedSurface${MODULE_NAME}Calculator
  )

set(${MODULE_NAME}Calculators_PYTHON_RESOURCES
  )

ctkMacroCompilePythonScript(
  TARGET_NAME ${MODULE_NAME}Calculators
  SCRIPTS "${${MODULE_NAME}Calculators_PYTHON_SCRIPTS}"
  RESOURCES "${${MODULE_NAME}Calculators_PYTHON_RESOURCES}"
  DESTINATION_DIR ${Slicer_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}/SegmentStatisticsCalculators
  INSTALL_DIR ${Slicer_INSTALL_QTSCRIPTEDMODULES_LIB_DIR}/SegmentStatisticsCalculators
  NO_INSTALL_SUBDIR
  )
