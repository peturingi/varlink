#!/bin/bash
# Usage: codegen.sh [project-dir]        (default: the dk.ingi.varlink.model project this tools/ dir is in)
# Runs the EMF generator headlessly on a scratch copy of the project (Equinox launcher jar + the JRE bundled
# with Eclipse; the Eclipse.app binary itself cannot run headless on macOS) and compiles the generated Java
# against EMF + OCL Pivot. Prints the scratch location; nothing in the real project is touched.
set -e
. "$(dirname "$0")/lib.sh"; need_build
PROJECT="${1:-$(cd "$TOOLS_DIR/../.." && pwd)}"
# The workspace project must be named after the plugin (modelPluginID in the genmodel), whatever the directory is called.
NAME=$(grep -o 'modelPluginID="[^"]*"' "$PROJECT"/model/*.genmodel | head -1 | sed 's/.*="//; s/"//')
[ -n "$NAME" ] || NAME=$(basename "$PROJECT")
[ -n "$JUSTJ_JAVA" ] || { echo "bundled JustJ JRE not found under $PLUGINS" >&2; exit 2; }
WS=$(mktemp -d "${TMPDIR:-/tmp}/varlink-codegen.XXXXXX")
mkdir -p "$WS/ws"
rsync -a --exclude bin --exclude src-gen --exclude .git "$PROJECT/" "$WS/ws/$NAME/"
GENMODEL=$(ls "$WS/ws/$NAME"/model/*.genmodel | head -1)
echo "workspace: $WS/ws  genmodel: $GENMODEL"
"$JUSTJ_JAVA" -Djava.awt.headless=true -jar "$LAUNCHER" -nosplash -consoleLog -data "$WS/ws" \
  -application org.eclipse.emf.codegen.ecore.Generator -model -forceOverwrite "$GENMODEL" > "$WS/generator.log" 2>&1 || true
grep -E '^>>  Generating (code|packages)' "$WS/generator.log" >/dev/null || { echo "generator did not run; see $WS/generator.log" >&2; exit 1; }
N=$(find "$WS/ws/$NAME/src-gen" -name '*.java' | wc -l | tr -d ' ')
echo "generated $N Java sources under $WS/ws/$NAME/src-gen"
mkdir -p "$WS/classes"
find "$WS/ws/$NAME/src-gen" -name '*.java' > "$WS/sources.txt"
if javac -proc:none -Xlint:none -cp "$OCL_RUNTIME_CP" -d "$WS/classes" @"$WS/sources.txt" > "$WS/javac.log" 2>&1; then
  echo "COMPILE OK ($(find "$WS/classes" -name '*.class' | wc -l | tr -d ' ') classes)"
else
  echo "COMPILE FAILED; see $WS/javac.log"; head -20 "$WS/javac.log"; exit 1
fi
