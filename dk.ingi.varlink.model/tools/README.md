# tools

## python/ — IDL parser, formatter and XMI converter (Python 3.15, standard library only)

- `varlink_idl.py` — `parse_interface(text)` → frozen dataclass AST following the UAPI.20 PEG exactly
  (nullable only as the grammar allows, inline struct/enum at any depth, nested containers, docs per
  declaration and per field/value, systemd marker lines turned into flags); `format_interface(ast)`
  renders canonical IDL; `python3 varlink_idl.py *.varlink` parses and round-trips each file.
- `varlink_xmi.py` — `python3 varlink_xmi.py in.varlink out.xmi` writes an instance of
  `model/model.ecore` (root `varlink:Interface`, name-keyed `//@members[name='X']` references).
- `split_introspect.py` — `python3 split_introspect.py introspect.txt outdir/` splits concatenated `varlinkctl introspect`
  output into one `.varlink` file per distinct interface text, keeping the comment block above each `interface` line.

Verified: all 38 systemd 263 interfaces round-trip (`parse(format(parse(x))) == parse(x)`), the canonical
output is accepted by `varlinkctl validate-idl` on nacos, and the XMI validates under EMF + OCL.

## emf/ — headless use of the local Eclipse install (no pyecore)

All scripts expect `~/Applications/Eclipse.app` (EMF 2.42, OCL Pivot 1.24) and Java 27 on PATH.

- `emfcheck.sh model.ecore [instance.xmi ...]` — loads with the genuine EMF runtime, prints the structure,
  runs `Diagnostician`, validates instances (multiplicities, unresolved proxies). Without the OCL delegate
  it reports OCL constraints on instances as "Unable to find delegate".
- `emfcheck-ocl.sh model.ecore [instance.xmi ...]` — the same with the OCL Pivot delegate registered through
  the `oclagent/` Java agent, so every OCL constraint, derivation and operation body is evaluated.
- `genmodel.sh model.ecore model.genmodel` — builds the generator model from the Ecore with
  `GenModel.initialize` and the project settings (basePackage `dk.ingi`, Java 27, operation reflection).
- `codegen.sh` — runs the EMF generator headlessly (Equinox launcher jar + the bundled JustJ JRE) on a
  scratch copy of the project and compiles the generated Java against EMF + OCL Pivot.

Rebuild the Java helpers with `build.sh` if the jar versions in the Eclipse install change.
