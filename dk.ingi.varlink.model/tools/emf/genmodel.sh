#!/bin/bash
# Usage: genmodel.sh model.ecore model.genmodel
# Builds the generator model from the Ecore with GenModel.initialize and this project's settings
# (plugin dk.ingi.varlink.model, basePackage dk.ingi, prefix Varlink, Java 27, operation reflection on).
. "$(dirname "$0")/lib.sh"; need_build
exec java -cp "$CODEGEN_CP:$BUILD_DIR/classes" GenModelBuilder "$1" "$2" dk.ingi.varlink.model dk.ingi Varlink 27.0
