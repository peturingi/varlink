#!/bin/bash
# Usage: oclprobe.sh model.ecore instance.xmi ...
# Evaluates every derived feature and OCL-bodied operation on every object of the instances and prints the
# values, then validates each root; use it to see what the OCL actually computes on real data.
. "$(dirname "$0")/lib.sh"; need_build
exec java "-javaagent:$BUILD_DIR/oclagent.jar=$BUILD_DIR/ocl-jars.txt" -cp "$EMF_CP:$BUILD_DIR/classes" OclProbe "$@" 2> >(grep -v 'sun.misc.Unsafe\|HiddenClassDefiner' >&2)
