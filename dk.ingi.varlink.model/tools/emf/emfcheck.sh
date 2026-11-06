#!/bin/bash
# Usage: emfcheck.sh model.ecore [instance.xmi ...]
# Loads the Ecore with the genuine EMF runtime, prints its structure, validates it with Diagnostician and
# validates the instances (multiplicities, unresolved proxies). OCL constraints on instances need emfcheck-ocl.sh.
. "$(dirname "$0")/lib.sh"; need_build
exec java -cp "$EMF_CP:$BUILD_DIR/classes" EmfCheck "$@"
