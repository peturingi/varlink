#!/bin/bash
# Usage: emfcheck-ocl.sh model.ecore [instance.xmi ...]
# emfcheck.sh with the OCL Pivot delegate registered (Java agent), so every OCL constraint, derivation
# and operation body in the Ecore is parsed and evaluated while validating the instances.
. "$(dirname "$0")/lib.sh"; need_build
exec java "-javaagent:$BUILD_DIR/oclagent.jar=$BUILD_DIR/ocl-jars.txt" -cp "$EMF_CP:$BUILD_DIR/classes" EmfCheck "$@" 2> >(grep -v 'sun.misc.Unsafe\|HiddenClassDefiner' >&2)
