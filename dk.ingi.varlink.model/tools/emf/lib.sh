# Shared shell functions for the headless EMF tools. Sourced by the scripts next to it.
# Configure with ECLIPSE=<path to Eclipse.app/Contents/Eclipse> if the install is elsewhere.

ECLIPSE="${ECLIPSE:-$HOME/Applications/Eclipse.app/Contents/Eclipse}"
PLUGINS="$ECLIPSE/plugins"
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
BUILD_DIR="$TOOLS_DIR/build"

[ -d "$PLUGINS" ] || { echo "Eclipse plugins directory not found: $PLUGINS (set ECLIPSE=...)" >&2; exit 2; }

# jar_of <bundle symbolic name>  -> newest matching jar in the plugins directory
jar_of() {
  ls "$PLUGINS/$1"_[0-9]*.jar 2>/dev/null | grep -v '\.source_' | sort -V | tail -1
}

# join_cp <jar> ...  -> colon-joined classpath, skipping empties
join_cp() {
  local cp=""
  for j in "$@"; do [ -n "$j" ] && cp="${cp:+$cp:}$j"; done
  printf '%s' "$cp"
}

EMF_CP=$(join_cp "$(jar_of org.eclipse.emf.common)" "$(jar_of org.eclipse.emf.ecore)" "$(jar_of org.eclipse.emf.ecore.xmi)")
CODEGEN_CP=$(join_cp "$EMF_CP" "$(jar_of org.eclipse.emf.codegen.ecore)" "$(jar_of org.eclipse.emf.codegen)")
# Runtime classpath for Java generated with the OCL Pivot code generator (compiled OCL bodies).
OCL_RUNTIME_CP=$(join_cp "$EMF_CP" "$(jar_of org.eclipse.emf.ecore.change)" "$(jar_of org.eclipse.ocl.pivot)" "$(jar_of org.eclipse.ocl.common)" \
  "$(jar_of org.eclipse.jdt.annotation)" "$(jar_of com.google.guava)" "$(jar_of org.apache.log4j)" "$(jar_of org.eclipse.xtext.util)" "$(jar_of org.eclipse.xtext)")

# The bundled JustJ JRE Eclipse itself runs with (needed for the headless generator; Java 27 breaks the jgit weaving hooks).
JUSTJ_JAVA=$(ls -d "$PLUGINS"/org.eclipse.justj.openjdk.hotspot.jre.full.macosx.*/jre/bin/java 2>/dev/null | sort -V | tail -1)
LAUNCHER=$(jar_of org.eclipse.equinox.launcher)

need_build() {
  [ -f "$BUILD_DIR/classes/EmfCheck.class" ] && [ -f "$BUILD_DIR/oclagent.jar" ] && [ -f "$BUILD_DIR/ocl-jars.txt" ] || { echo "run $TOOLS_DIR/build.sh first" >&2; exit 2; }
}
