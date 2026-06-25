# Java home
$env:JAVA_HOME = Split-Path -Parent (Get-Command java).Path
$env:OPENJMS = "C:\Program Files (x86)\Common Files\Java\openjms-0.7.7-beta-1"

# xmlValidator property file
# $env:CONFIGURATION_xmlValidator = ".\serviceServer\TestXmlValidatorRequestHandler.props"
$env:CONFIGURATION_xmlValidator = ".\serviceServer\TestXmlValidatorRequestHandler.props"

# polygonToTown property file
$env:CONFIGURATION_polygonToTown = ".\serviceServer\TestPolygonToTownWfsRequestHandler.props"

# polygonToCountry property file
$env:CONFIGURATION_polygonToCountry = ".\serviceServer\TestPolygonToCountryWfsRequestHandler.props"

# polygonShapeFile property file
$env:CONFIGURATION_polygonToShape = ".\serviceServer\TestPolygonShapeFileWfsRequestHandler.props"

# polygonShapeFile spot4 take5 property file
$env:CONFIGURATION_polygonToShape_spot4_take5 = ".\serviceServer\TestPolygonShapeFileWfsRequestHandler_spot4_take5.props"

# polygonShapeFile spot5 take5 property file
$env:CONFIGURATION_polygonToShape_spot5_take5 = ".\serviceServer\TestPolygonShapeFileWfsRequestHandler_spot5_take5.props"

# worldview2
$env:CONFIGURATION_worldviewLuzResolver = ".\serviceServer\TestWorldviewLuzResolverRequestHandler.props"

# Add java;openJms to PATH
$env:PATH = "$($env:JAVA_HOME)\bin;$env:OPENJMS;$env:PATH"
Write-Output "new PATH=$env:PATH"
