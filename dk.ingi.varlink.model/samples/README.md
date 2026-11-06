# samples

Instances of `model/model.ecore`, all validated with EMF 2.42 + OCL Pivot 1.24 (`tools/emf/emfcheck-ocl.sh`).

| File(s) | What |
|---|---|
| `org.example.ftl.varlink` / `.xmi` | the spec's example interface, documentation verbatim |
| `MyType.xmi` | an interface with the spec's `type MyType` example: every type form, including `[string]()`, `?[](...)`, nested inline struct/enum, a method with empty input and output, an error without parameters |
| `service.xmi` | `service.Service`, `ServiceRegistry`, `http.HttpBridge` and `protocol.Exchange` roots with cross-resource links to interfaces |
| `negative.xmi`, `negative-packages.xmi` (+ `.probe`) | fixtures that violate each OCL constraint of the synthesis once; the `.probe` files list the expected violations |
| `refute-probe.xmi` | fixture for the constraints added in the refutation round: roots /0, /2, /3 are valid, /1 and /4 violate exactly the new constraints |
| `systemd-263/*.varlink` | the IDL of the 38 distinct interfaces introspected on nacos (systemd 263) on 2026-11-06; `nacos-introspect-2026-11-06.txt` is the raw `varlinkctl introspect` output they were split from (`tools/python/split_introspect.py`) |
| `systemd-263/*.xmi` | the same converted by `tools/python/varlink_xmi.py` |

To regenerate the XMI for an interface: `python3 tools/python/varlink_xmi.py samples/systemd-263/io.systemd.Machine.varlink out.xmi`.
