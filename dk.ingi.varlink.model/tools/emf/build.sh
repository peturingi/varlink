#!/bin/bash
# Compiles the Java helpers against the local Eclipse install and builds the OCL delegate agent.
set -e
. "$(dirname "$0")/lib.sh"
mkdir -p "$BUILD_DIR/classes"
javac -proc:none -Xlint:none -cp "$CODEGEN_CP" -d "$BUILD_DIR/classes" "$TOOLS_DIR"/src/*.java
printf 'Premain-Class: OclAgent\n' > "$BUILD_DIR/manifest.txt"
jar cfm "$BUILD_DIR/oclagent.jar" "$BUILD_DIR/manifest.txt" -C "$BUILD_DIR/classes" OclAgent.class
# Jars the OCL Pivot delegate needs at runtime (resolved by bundle name, so plugin versions may change).
: > "$BUILD_DIR/ocl-jars.txt"
for b in org.eclipse.ocl.pivot org.eclipse.ocl.common org.eclipse.ocl.xtext.base org.eclipse.ocl.xtext.essentialocl \
         org.eclipse.ocl.xtext.oclinecore org.eclipse.ocl.xtext.markup org.eclipse.ocl.xtext.completeocl org.eclipse.ocl.xtext.oclstdlib \
         org.eclipse.xtext org.eclipse.xtext.util org.eclipse.xtext.xbase.lib org.eclipse.xtend.lib org.eclipse.xtend.lib.macro \
         com.google.inject jakarta.inject.jakarta.inject-api com.google.guava com.google.guava.failureaccess \
         org.antlr.runtime org.apache.log4j org.eclipse.equinox.common org.eclipse.core.runtime org.eclipse.emf.ecore.change \
         org.eclipse.osgi org.eclipse.core.jobs org.eclipse.equinox.registry org.eclipse.core.contenttype org.eclipse.equinox.preferences \
         org.eclipse.core.resources org.eclipse.emf.edit org.eclipse.emf.ecore.edit org.eclipse.emf.codegen.ecore org.eclipse.emf.codegen \
         org.eclipse.emf.common.ui; do
  j=$(jar_of "$b"); [ -n "$j" ] && echo "$j" >> "$BUILD_DIR/ocl-jars.txt" || echo "warning: bundle $b not found" >&2
done
echo "built $(ls "$BUILD_DIR/classes" | wc -l | tr -d ' ') classes, agent $BUILD_DIR/oclagent.jar, $(wc -l < "$BUILD_DIR/ocl-jars.txt" | tr -d ' ') OCL runtime jars"
