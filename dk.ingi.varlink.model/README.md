# dk.ingi.varlink.model — Ecore metamodel of UAPI.20 Varlink IPC

An EMF metamodel of the UAPI group specification **UAPI.20 Varlink IPC v0.1** (`docs/varlink20.txt`),
built as the first step of a model-driven pipeline:

1. this metamodel (`model/model.ecore`, root EPackage `varlink`, nsURI `https://ingi.dk/varlink`);
2. a generic Python 3.15 varlink binding (planned);
3. an Acceleo text generator that turns a parsed interface definition (e.g. the output of
   `varlinkctl introspect unix:/run/systemd/machine/io.systemd.Machine`) into a fully type-hinted
   Python client API per interface (planned).

## Layout

| Path | Content |
|---|---|
| `model/model.ecore` | the metamodel: package `varlink` (IDL abstract syntax) with subpackages `json`, `protocol`, `service`, `transport`, `http` |
| `model/model.genmodel` | generator model (basePackage `dk.ingi`, Java 27, operation reflection on) |
| `model/model.aird` | Sirius representation file (the diagram needs to be re-synchronised with the new classes) |
| `docs/varlink20.txt` | the specification |
| `docs/DESIGN.md` | class-by-class design document, coverage matrix, OCL inventory, decision log |
| `samples/*.varlink`, `samples/*.xmi` | instances: the spec examples, all 38 systemd 263 interfaces from nacos, negative fixtures |
| `tools/python/` | stdlib-only Python 3.15 IDL parser/formatter and IDL→XMI converter (seed of the binding) |
| `tools/emf/` | headless validation, OCL evaluation, genmodel creation and code generation with the local Eclipse install |

## Conventions worth knowing

- Every class, feature, enum and literal carries a GenModel `documentation` annotation quoting the spec.
- Well-formedness rules are OCL Pivot constraints (`http://www.eclipse.org/emf/2002/Ecore/OCL/Pivot`);
  they are evaluated in Eclipse (OCL is installed) and by `tools/emf/emfcheck-ocl.sh`.
- Because OCL Pivot is installed, "Generate Model Code" compiles the OCL bodies of derived features
  and operations to Java; the generated code therefore needs `org.eclipse.ocl.pivot` (already in
  `META-INF/MANIFEST.MF`).
- systemd's comment conventions (`# [Supports 'more' flag]`, `# [Requires 'more' flag]`,
  `# [Supports/Requires 'upgrade' flag]`, `# [Experimental]`) are first-class features
  (`Method.moreSupport`, `Method.upgradeSupport`, `Declaration.experimental`) and are documented as
  extensions beyond the UAPI.20 grammar.
- The model follows the spec grammar where systemd 263 is stricter: `[string]()`, `[]?T`, `[][]T`,
  `type T ()` and trailing commas are rejected by `varlinkctl validate-idl` but the first four are
  grammatical in UAPI.20 and representable here (trailing commas are not grammatical either).
