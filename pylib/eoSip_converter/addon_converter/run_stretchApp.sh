#!/bin/bash
#
# this script will create a stretched PNG image from the worldview TIFF, for worldview products
#
# Lavaux Gilles 09/2015
#

# unset the DISPLAY, because we dont want that ssh or other things 'lock' the display and avoid exiting the shell if some processes runs.
# also because DISPLAY is not needed/wanted. See GL for more info
unset DISPLAY


#
PWD=`pwd`
cd `dirname $0`
soft_PATH=`pwd`
libs_PATH="${soft_PATH}/libs"
echo "soft_PATH=${soft_PATH}"
echo "libs_PATH=${libs_PATH}"

. ${soft_PATH}/env

SRV_NAME="StretchApp"

# java
echo ""
echo "using java:"
java -version

#
CLASSPATH="${soft_PATH}"
#for jar in `ls ${libs_PATH}/*.jar`
#do
#	echo "add jar:$jar" 
#        CLASSPATH=$jar:$CLASSPATH
#done

echo ""
echo ""
echo "using CLASSPATH=$CLASSPATH"
echo "using PATH=$PATH"

echo ""
echo "starting..."

exit_code=0
echo "COMMAND:java -cp ${CLASSPATH}:${libs_PATH}/stretchApp.jar histogramStretcher.StretchApp $1 $2 $3 $4 $5 $6 $7 $8 $9 ${10}"
java -Djava.awt.headless=true -cp ${CLASSPATH}:${libs_PATH}/stretchApp.jar histogramStretcher.StretchApp $1 $2 $3 $4 $5 $6 $7 $8 $9

exit_code=$?
if [ $exit_code -eq 0 ]; then
  echo " PNG generation OK: $exit_code"
else
  echo " PNG generation FAILURE: $exit_code"
fi

cd $PWD
exit $exit_code