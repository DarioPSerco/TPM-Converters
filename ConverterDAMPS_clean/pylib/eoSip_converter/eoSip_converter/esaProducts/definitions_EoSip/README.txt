
Because of generic EoSip spec changes, it was neccesary to create subfolders containing the EoSip version branches. 
This to avoid having to maintain several converter.

It imply to have TWO packages paths in the classpath or PYTONPATH:
- <CONVERTER_HOME>    (the converter itself)
- <CONVERTER_HOME>/eoSip_converter/esaProducts/definitions_EoSip/v100    (the converter EoSip definition to be used)