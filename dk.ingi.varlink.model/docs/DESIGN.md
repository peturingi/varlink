# UAPI.20 Varlink IPC v0.1 — Ecore metamodel design

Project `dk.ingi.varlink.model` (Eclipse plugin). This document describes `model/model.ecore` class by class, maps every
spec section and grammar production to model elements, lists all OCL invariants, and records the design decisions.
The model was produced on 2026-11-06 by three independent designs (grammar-first, generator-first, MOF-purist), three
judges, a synthesis, and an adversarial refutation round, each step validated with the genuine EMF 2.42 + OCL Pivot 1.24
runtime of the local Eclipse install.

| File | What |
|---|---|
| `model/model.ecore` | The metamodel: root EPackage `varlink` (nsURI `https://ingi.dk/varlink`, nsPrefix `varlink`) with the IDL abstract syntax, and five inline subpackages `json`, `protocol`, `service`, `transport`, `http` (nsURI `https://ingi.dk/varlink/<name>`). **47 EClasses, 13 EEnums, 70 OCL constraints, 23 OCL-derived features, 32 EOperations (31 with OCL bodies, 1 abstract and overridden), 6 EPackages.** Every EPackage, EClass, EAttribute, EReference, EOperation, EParameter, EEnum and EEnumLiteral carries a GenModel `documentation` annotation; every package carries the three OCL Pivot delegate keys. Single inheritance throughout; no package cycles. |
| `model/model.genmodel` | Generator model built from the Ecore (`tools/emf/genmodel.sh`): basePackage `dk.ingi`, prefix `Varlink`, Java 27, operation reflection on, feature delegation none (see section 14). |
| `samples/org.example.ftl.varlink`, `.xmi` | The spec's example interface with all documentation lines verbatim. 51 objects. |
| `samples/MyType.xmi` | Interface `org.example.types`: the spec's `type MyType (...)` verbatim, the enum `MyOtherType` it references (forward reference), `type Deep` with every nested form the grammar admits (`[][]int`, `[]?int`, `?[string]?[string]()`, inline struct/enum at depth 3, `[string][](p, q)`, a bare `()` field, `?any`, `?object`), `type Empty ()`, `method Nothing() -> ()`, methods with all four systemd flag markers and an `[Experimental]` member, `error Nope ()` and a parameterised error with a nested inline struct. 145 objects. |
| `samples/service.xmi` | Cross-package instance: Service, ServiceRegistry, HttpBridge, two Exchanges with JSON payloads, cross-resource name-keyed links into the two interface files. |
| `samples/negative.xmi`, `negative-packages.xmi` (+ `.probe`) | Planted violations covering the 61 constraints of the synthesis (the refutation round's 9 additions are exercised by `samples/refute-probe.xmi`); the `.probe` files list the expected violation names per root. |
| `samples/systemd-263/` | The IDL of the 38 distinct interfaces introspected on nacos (systemd 263; raw introspection output included) and their XMI, converted by `tools/python/varlink_xmi.py`. |
| `tools/python/` | Stdlib Python 3.15 IDL parser/formatter (`varlink_idl.py`, written from the spec grammar/PEG) and XMI converter (`varlink_xmi.py`). |
| `tools/emf/` | Headless validation (`emfcheck.sh`, `emfcheck-ocl.sh`), derivation probe (`oclprobe.sh`), genmodel creation and Java generation + compilation (`codegen.sh`) with the local Eclipse install. |

## 0. Validation results (reproducible from the project root)

```
tools/emf/emfcheck.sh model/model.ecore
    == EPackage varlink nsURI=https://ingi.dk/varlink classifiers=24 subpackages=5
       -> ecore validation: OK
    RESULT: OK                                              (stock runner, no warnings)

tools/emf/emfcheck-ocl.sh model/model.ecore samples/org.example.ftl.xmi samples/MyType.xmi samples/service.xmi
    -> ecore validation: OK                                 (OCL Pivot parses and type-checks every body)
    == instance samples/org.example.ftl.xmi: 51 objects, valid
    == instance samples/MyType.xmi: 145 objects, valid      (0 unresolved proxies)
    == instance samples/service.xmi: 60 objects, valid
    RESULT: OK

tools/emf/emfcheck-ocl.sh model/model.ecore samples/systemd-263/*.xmi   -> 38 instances valid (io.systemd.Unit = 2127 objects), RESULT: OK
tools/emf/emfcheck-ocl.sh model/model.ecore samples/negative.xmi        -> every planted violation reported by constraint name (see samples/*.probe)
tools/emf/codegen.sh   -> 149 generated Java sources (OCL evaluated through the Pivot delegates, see section 14), COMPILE OK (167 classes)
```

Independent cross-checks performed on 2026-11-06:

- Two converters written independently from the spec grammar (the synthesizer's and `tools/python/varlink_xmi.py`) produce
  canonically identical XMI for all 31 systemd interfaces of the first corpus (7 more were added afterwards).
- `tools/python/varlink_idl.py` round-trips all 38 interfaces exactly (`parse(format(parse(x))) == parse(x)`), and systemd 263's
  own `varlinkctl validate-idl` on nacos accepts all 38 canonical outputs and the spec's `org.example.ftl` example.
- The same validator rejects the spec's `[string]()` string-set idiom, `[]?int`, `[][]int`, `type T ()` and trailing commas
  (`Bad syntax`), and accepts digit-initial later interface-name components and hyphens: the model follows the UAPI.20 grammar
  for the first four (they are grammatical) and the grammar for the fifth (not grammatical, rejected by `varlink_idl.py` too).

**About the stock runner and instances.** `tools/emf/emfcheck.sh` has only `emf.common`, `emf.ecore`, `emf.ecore.xmi` on its
classpath, so when it validates an *instance* EMF reports every OCL constraint as `ERROR: Unable to find delegate to evaluate
the 'X' constraint`. That is a property of the classpath, not of the model: `emfcheck-ocl.sh` runs the same class with the OCL
Pivot delegate registered (the way Eclipse does through its plugin registry) and is the validator to use for instances.

Notes from the synthesis: two Pivot defects were caught only because the ecore itself was validated with the delegate active
(`-> ecore validation: OK` above means every OCL body was parsed and type-checked): `enclosingFields()` was declared as an
OrderedSet while its body built Sequences, and `positionPath()`'s `union` chain typed as `Collection(String)`. Both bodies now
use typed `let` variables and `prepend`/`append`. A third trap was found by a spot query: an *unsettable* enum attribute reads
as its default literal in OCL and dynamic EMF (an untagged socket inode would have been `client`), which changed the SocketInode
design (section 7).

## 1. Base choice

All three judges recommended **grammar-first** as the base (fidelity 34/40, generator 33.5/40, EMF craft 33/40, first in every ranking) and all three rejected generator-first as a base for the same verified structural defect (constraints on second supertypes are skipped by stock dynamic validation) plus its containment `Service.interfaces` and ill-formed closure OCL; mof-purist lost on an unconstrained empty interface, split nullability and a missing renderer. There was no disagreement to arbitrate; the synthesis therefore keeps grammar-first's structure (one `nullable` flag per type node, single inheritance, non-containment Service→Interface, Exchange sequencing rules, closed-set enums, lossless JSON numbers) and grafts the generator conveniences and the fidelity fixes the judges listed. Every defect and graft is accounted for in the decision log (section 12).

## 2. Package layout and resource roots

```
varlink            IDL abstract syntax (grammar transcribed production by production)      21 classes, 3 enums
  json             lossless RFC 8259 value model for message payloads                      8 classes
  protocol         Call, Reply, VendorExtension, Exchange (reply-sequencing invariants)    5 classes
  service          Service, ServiceInformation (GetInfo), StandardError, addresses,
                   ServiceRegistry/RegistryEntry                                           9 classes, 2 enums
  transport        SocketActivationEnvironment, SocketInode + SocketRole                   2 classes, 1 enum
  http             HttpBridge, HttpBridgeAddress, route/mode/media/failure/auth/status     2 classes, 7 enums
```
Dependencies: `json` ← `protocol` → `varlink`; `service` → `varlink`, `transport`; `http` → `service`. No cycles (the registry lives in `service`, not `transport`, precisely to avoid the `service ↔ transport` cycle generator-first had; the bridge address lives in `http` as a subclass of `service.ServiceAddress`, which is why `ServiceAddress.addressText()` is abstract and overridden rather than an `if oclIsKindOf` chain: the base must not name a subclass of a package that depends on it).

Resource roots: **`Interface`** is the natural root, one per `.varlink` file (`Interface.fileName()`); **`service.Service`** is a second root that *references* its interfaces (cross-resource `href`, or sibling roots in one XMI); **`service.ServiceRegistry`** (the `/run/varlink/registry` directory), **`http.HttpBridge`** and **`protocol.Exchange`** are further roots (`tests/service.xmi` has all of them). Containing interfaces inside a service was rejected (judges' major defect of generator-first): it makes `Interface` sometimes rooted and sometimes contained, forces every deployment model to copy definitions, and cannot represent a GetInfo answer (names only) as data.

URI fragments: `Interface.members`, `StructType.fields` and `EnumType.values` have `eKeys = name`, so references read `//@members[name='GetInfo']` instead of positional `//@members.4`; cross-resource links from calls, replies, registry entries and services therefore survive member reordering. Positional fragments still resolve on load. A bonus verified by `tests/negative.xmi`: EMF's own validator now reports duplicate member/field/value names as key collisions even without the OCL delegate.

## 3. Root package `varlink` (IDL abstract syntax)

Legend for constraints: name — OCL (Pivot) — meaning. `R` abbreviates the spec's interface_name regex `[A-Za-z]([-]*[A-Za-z0-9])*(\.[A-Za-z0-9]([-]*[A-Za-z0-9])*)+` (written `\\.` inside the OCL string).

### 3.1 Common abstractions

**`InterfaceElement`** (abstract). Any node of an interface definition tree. Operations: `owningInterface() : Interface` (walk containment up; the Interface itself for an Interface; null when detached); `enclosingMember() : Member` (the type definition / method / error containing this node, or the node itself); `effectiveExperimental() : Boolean` (systemd: this node or any enclosing Declaration is experimental). Spec: structure only.

**`Declaration`** (abstract, : InterfaceElement). The four documentable kinds (interface, member, field/parameter, enum value), which are exactly the four kinds systemd can mark experimental. Features: `name : EString[1]`; `documentation : EString[*]` ordered non-unique, one entry per `#` line, the single conventional separator space stripped, empty lines kept as empty strings (spec "Documentation Comments"); `documentationText : EString` derived (`let n = documentation->size() in Sequence{1..n}->iterate(i; acc : String = '' | acc + documentation->at(i) + (if i < n then '\n' else '' endif))`, `''` when undocumented — an attribute rather than an operation so AQL and Sirius labels read it directly); `experimental : EBoolean = false` (systemd `# [Experimental]`). Constraint `systemdMarkersNotInDocumentation` — `documentation->forAll(l | l <> '[Experimental]' and not l.matches('\[(Supports|Requires) \'(more|upgrade)\' flag\]'))` — marker lines are flags, never documentation (a gap all three designs had).

### 3.2 Interface and members

**`Interface`** (: Declaration). Grammar `interface ::= "interface" interface_name members`. Features: `members : Member[1..*]` containment, ordered, opposite `Member.interface`, eKeys `name` (grammar requires ≥ 1 member, PEG `member ++ eol`); derived `types`, `methods`, `errors` (`members->selectByKind(...)`); derived `nameSegments : EString[*]` (`name.tokenize('.')`, e.g. `['io','systemd','Machine']`); `source : EString[0..1]` (optional verbatim `GetInterfaceDescription` text). Operations: `findMember(memberName)`, `findType(typeName)`, `findMethod(methodName)`, `findError(errorName)` (all `select` + `isEmpty` guarded, null on miss), `fileName()` = `name + '.varlink'`. Constraints: `nameSyntax` — `name <> null and name.matches('R')` — spec "Names"/grammar `interface_name` (≥ 2 components, no leading/trailing hyphen); `memberNamesUnique` — `members->isUnique(name)` — "Types, methods and error names MUST be unique identifiers within an interface definition; they share the same namespace."

**`Member`** (abstract, : Declaration). Grammar `member ::= type_alias | method | error`. Features: `interface` (container opposite, [0..1] so a detached member is valid during construction); derived `qualifiedName` (`interface.name + '.' + name`, the wire form `org.example.test.GetInfo`). Constraint `nameSyntax` — `name.matches('[A-Z][A-Za-z0-9]*')` — grammar `name`.

**`TypeDefinition`** (abstract, : Member). Grammar `type_alias ::= "type" name struct | "type" name enum`; the two alternatives are the two concrete subclasses, so an Acceleo template dispatches `members->filter(StructDefinition)` / `filter(EnumDefinition)` without a cast. Features: `usages : NamedTypeReference[*]` transient opposite of `NamedTypeReference.definition` (dependency ordering, unused-type detection). Operation `definedType() : CompositeType` returns the typed body of whichever subclass (generic access for renderers).

**`StructDefinition`** (: TypeDefinition). `body : StructType[1]` containment. Constraint `bodyNotNullable` — `body <> null and not body.nullable` — the grammar's `struct` after `type name` is bare, never a `?`-type. `type X ()` is admitted (spec grammar), documented as refused by systemd.

**`EnumDefinition`** (: TypeDefinition). `body : EnumType[1]` containment (≥ 1 value by multiplicity). Constraint `bodyNotNullable` likewise.

**`Method`** (: Member). Grammar `method ::= "method" name struct "->" struct`. Features: `input`, `output : ParameterStruct[1]` containment (two separate namespaces); derived `inputParameters`, `outputParameters : Field[*]` (`input.fields` / `output.fields`, null-guarded); **systemd** `moreSupport`, `upgradeSupport : CallFlagSupport = unspecified`; derived **systemd** `supportsMore` (`moreSupport <> unspecified`), `requiresMore` (`= required`), `supportsUpgrade`, `requiresUpgrade`. Constraint `parameterStructsNotNullable` — `input <> null and output <> null and not input.nullable and not output.nullable` — parameter lists are bare structs.

**`CallFlagSupport`** (EEnum, systemd): `unspecified` (no marker; the only state UAPI.20 can express, *not* "unsupported"), `supported` (`# [Supports 'more' flag]`), `required` (`# [Requires 'more' flag]`, implies supported).

**`ErrorDefinition`** (: Member). Grammar `error ::= "error" name struct`. `parameters : StructType[1]` containment (`()` allowed). Constraint `parametersNotNullable`. Named `ErrorDefinition` because an EClass `Error` would generate a Java type shadowing `java.lang.Error`.

### 3.3 Fields and values

**`Field`** (: Declaration). Grammar `struct_field ::= field_name ":" type`; a field of a named struct, an inline struct, a parameter list or an error. Features: `type : TypeExpression[1]` containment; `structType` (container opposite of `StructType.fields`); derived `nullable` (`type <> null and type.nullable`, the most used template predicate). Constraints: `nameSyntax` — `name.matches('[A-Za-z](_?[A-Za-z0-9])*')` — grammar `field_name` (single inner underscores only); **systemd** `systemdExperimentalFieldNullable` — `experimental implies ((type <> null and type.nullable) or (structType <> null and structType.effectiveExperimental()))` — sd-varlink-idl: an experimental field of a non-experimental symbol must be nullable.

**`EnumValue`** (: Declaration). One `field_name` of `enum_fields`. `enumType` container opposite. Constraints: `nameSyntax` (field_name rule); **systemd** `systemdExperimentalValueInExperimentalEnum` — `experimental implies (enumType <> null and enumType.effectiveExperimental())`.

### 3.4 Type expressions

**`TypeExpression`** (abstract, : InterfaceElement). Grammar `type ::= element_type | "[]" type | "[string]" type | "?" element_type | "?" "[]" type | "?" "[string]" type` = an optional `?` followed by one of {element_type, `[]` type, `[string]` type}. `nullable : EBoolean = false` is that optional `?` **on this node**; the node is otherwise an ArrayType, a MapType or an ElementType. Hence `??T` is unrepresentable by construction (one slot per node), while `[][]int`, `[]?int`, `?[]?[string]()` are representable exactly as the grammar allows (systemd's narrower dialect is documented, not enforced). The same StructType/EnumType classes stand in the grammar's bare positions (definition bodies, parameter lists, error parameters) where the three `...NotNullable` constraints keep the slot false (requirement 2's "documented constraint"). Operations: `text()` — IDL rendering on one line (`?[]string`, `[string]()`, `(first: int, second: string)`, `MyOtherType`), verified to round-trip every form in `MyType.xmi`; `enclosingField()`; `enclosingFields() : Field[*]` outermost first; `positionPath() : EString[*]` — `[member, 'input'|'output'?, field names...]`, a stable interface-unique path for naming anonymous composites (`['Deep','nested','third','x']`, `['List','output','addresses']`, `['Detailed','more_data']`, `['Jump','input']`).

**`ArrayType`** (`"[]" type`): `elementType : TypeExpression[1]`. **`MapType`** (`"[string]" type`): `valueType : TypeExpression[1]`; derived `stringSet` (`valueType` is a non-nullable empty StructType: the `[string]()` idiom).

**`ElementType`** (abstract): `struct | enum | name | bool | int | float | string | object | any`.
**`BuiltinType`**: `kind : BuiltinKind[1]`; `keyword()` gives the IDL keyword string. **`BuiltinKind`** (EEnum): `bool int float string object any`, each literal documenting the spec's JSON mapping, integer range and NaN rules.
**`NamedTypeReference`**: `typeName : EString[1]` (raw token, kept so a two-pass parser can create the node before resolution and `text()` works unresolved); `definition : TypeDefinition[1]` non-containment, `resolveProxies=false` (interface-local), opposite `usages`. Constraints: `typeNameMatchesDefinition` — `definition <> null implies typeName = definition.name`; `definitionInSameInterface` — `definition.interface = self.owningInterface()` — type names are interface-local; **systemd** `systemdExperimentalTypeUsedInExperimentalContext` — `definition <> null implies (definition.experimental implies self.effectiveExperimental())` — sd-varlink-idl.c:1742 "Non-experimental field refers to experimental type, refusing".
**`CompositeType`** (abstract): struct or enum, in a named-body position or inline at any depth; derived `inline` (container is a Field, ArrayType or MapType) tells the positions apart without `eContainingFeature()` reflection.
**`StructType`** (`struct ::= "(" struct_fields ")" | "(" ")"`): `fields : Field[*]` ordered containment, opposite `Field.structType`, eKeys `name`; `findField(fieldName)`. Constraint `fieldNamesUnique` — `fields->isUnique(name)` — fields are keys of one JSON object. `()` is always a StructType (an EnumType has ≥ 1 value), which resolves the PEG's `venum`/`vstruct` ambiguity.
**`ParameterStruct`** (: StructType): the two `struct` positions of the `method` production. Derived `method` (container) and `direction : ParameterDirection`. Constraint `containedByMethod` — `let c = self.oclContainer() in c <> null and c.oclIsKindOf(Method)`. **`ParameterDirection`** (EEnum): `input`, `output`.
**`EnumType`** (`enum ::= "(" enum_fields ")"`): `values : EnumValue[1..*]` ordered containment, opposite `EnumValue.enumType`, eKeys `name`. Constraint `valueNamesUnique`.

## 4. Package `json` (spec "Mapping the Type System to JSON", "Integers", "Floating Point Numbers", "Nullable Fields and Absent Fields", "Unknown Fields")

`JsonValue` (abstract) ← `JsonObject` (`members : JsonMember[*]`; `member(memberName)`; constraint `memberNamesUnique`), `JsonMember` (`name[1]`, `value : JsonValue[1]`), `JsonArray` (`elements`), `JsonString` (`value`), `JsonNumber` (`lexical : EString[1]`, the number exactly as written so `1e3` and the 64-bit ranges survive; `isInteger()`; constraint `lexicalSyntax` = RFC 8259 number regex), `JsonBoolean` (`value : EBoolean[1]`), `JsonNull` (the explicit encoding of an absent nullable value). The type-to-JSON table is documented on the package and on every type class and `BuiltinKind` literal; checking a payload against a `TypeExpression` is runtime behaviour of a binding and deliberately not modelled.

## 5. Package `protocol` (spec "Wire Protocol", "Call", "Reply", "oneway", "more", "upgrade", "Errors", "Vendor Extensions", "Connection Lifecycle")

**`Message`** (abstract): `parameters : JsonObject[0..1]` containment (absent = null; `{}` = empty object; the spec's absent/null/`{}` equivalence is documented), `vendorExtensions : VendorExtension[*]`. Constraint `vendorsUnique` — `vendorExtensions->isUnique(vendor)`.
**`Call`**: `method : EString[1]`, `oneway`, `more`, `upgrade : EBoolean = false` (the spec's `?bool`; absent = false), optional `methodDefinition → Method`, derived `interfaceName`, `methodName`. Constraints: `atMostOneFlag` — `(if oneway then 1 else 0 endif) + ... <= 1`; `methodQualified` — `method.matches('R\.[A-Z][A-Za-z0-9]*')`; `methodDefinitionMatches` — `methodDefinition <> null implies methodDefinition.qualifiedName = method`.
**`Reply`**: `continues : EBoolean = false`, `error : EString[0..1]`, optional `errorDefinition → ErrorDefinition`, derived `errorReply` (`error <> null`; renamed from `isError` so Java generates `isErrorReply()`). Constraints `errorReplyNeverContinues`, `errorQualified`, `errorDefinitionMatches`.
**`VendorExtension`**: `vendor : EString[1]`, `value : JsonObject[1]`; constraint `vendorReverseDomain` (`vendor.matches('R')`, hence at least one dot).
**`Exchange`** (modelling convenience, a legal root): `call : Call[1]`, `replies : Reply[*]` ordered. Constraints encode the reply-sequencing prose: `onewayHasNoReplies` (`call.oneway implies replies->isEmpty()`), `singleReplyUnlessMore` (`not call.more implies replies->size() <= 1`), `continuesOnlyWhenMore` (`not call.more implies replies->forAll(r | not r.continues)`), `finalReplyTerminates` (`replies->notEmpty() implies not replies->last().continues`), `intermediateRepliesContinue` (`Sequence{1..replies->size() - 1}->forAll(i | replies->at(i).continues)`), `upgradeConfirmedOnce` (`call.upgrade implies replies->size() <= 1`).
Documented only: framing (NUL belongs to the transport), ordering/pipelining, the MUST-close rules for malformed messages, size limits.

## 6. Package `service` (spec "Terminology", "The org.varlink.service Interface", "Service Addresses", "Service Registry Directory")

**`Service`** (root): `name : EString[0..1]` (the spec gives services no intrinsic name; the bridge/registry convention is the primary interface name), `information : ServiceInformation[0..1]` containment, `interfaces → Interface[*]` **non-containment**, `addresses : ServiceAddress[*]` containment, `socketActivation : transport.SocketActivationEnvironment[0..1]`, `sockets : transport.SocketInode[*]`, `registryEntries → RegistryEntry[*]` non-containment opposite of `RegistryEntry.service` (EMF serializes both ends; a hand-written file may list the links on either end, the loader completes the other, as `samples/service.xmi` does on the service). Operation `implementsInterface(interfaceName)`. Constraints: `interfaceNamesUnique`; `informationListsImplementedInterfaces` — `information <> null implies interfaces->forAll(i | information.interfaces->includes(i.name))`; `registryEntriesNameImplementedInterfaces` — `(interfaces->notEmpty() or information <> null) implies registryEntries->forAll(e | self.implementsInterface(e.interfaceName))` (an entry may name an interface known only from GetInfo).
**`ServiceInformation`**: exact mirror of `GetInfo() -> (vendor, product, version, url, interfaces: []string)`. Constraints `includesVarlinkService` (`interfaces->includes('org.varlink.service')`, "The list MUST include org.varlink.service itself"), `interfaceNamesWellFormed`.
**`StandardError`** (EEnum): the seven generic errors (`InterfaceNotFound` … `ExpectedUpgrade`), each literal documenting meaning, parameters and HTTP status. The closed set a Python binding needs for its generic exception classes; the org.varlink.service IDL itself is also just an Interface instance (`samples/systemd-263/org.varlink.service.xmi`).
**`ServiceAddress`** (abstract): `properties : EString[*]` non-unique (the `;` extension rule; opaque segments, the spec defines no syntax); `text()` = `addressText() + properties->iterate(p; acc : String = '' | acc + ';' + p)`; `addressText()` abstract, overridden per concrete class (Ecore operation overriding, dispatched polymorphically by Pivot, verified for all four kinds). Constraint `propertiesWellFormed` — `properties->forAll(p | p.size() > 0 and p.indexOf(';') = 0)`.
**`UnixSocketAddress`** (abstract) ← **`UnixPathAddress`** (`path[1]`; `addressText` = `'unix:' + path`; `pathNotEmpty` also rejects a leading `@`) and **`UnixAbstractAddress`** (`name[1]`; `'unix:@' + name`; `nameNotEmpty`). **`TcpAddress`**: `host[1]` (IPv6 without brackets), `port : EInt[1]`, derived `hostKind : TcpHostKind` (ipv6 if it contains `:`, ipv4 if dotted quad, else hostname); `addressText` brackets IPv6; constraints `portRange` (1..65535), `hostNotBracketed`. **`TcpHostKind`** (EEnum): the three host rows of the spec table.
**`ServiceRegistry`** (root): `directory : EString[1] = /run/varlink/registry`, `entries : RegistryEntry[*]` containment opposite `RegistryEntry.registry`. Constraints `directoryAbsolute` (`startsWith('/')`; a trailing slash as the spec spells it is accepted and normalised by `RegistryEntry.path`), `entryNamesUnique` (`entries->isUnique(interfaceName)`).
**`RegistryEntry`**: `interfaceName[1]` (the file name = advertised interface), `symlink : EBoolean = false`, `targetPath[0..1]`, `interface → Interface[0..1]`, `service → Service[0..1]` (opposite above), `registry` (container opposite), derived `path` (`registry.directory + '/' + interfaceName`, the spec default when detached). Constraints `interfaceNameSyntax` (varlinkctl's registry reader skips inodes not named like an interface before it looks at their type, so the spec's SHOULD is effectively a MUST), `interfaceMatches` (`interface <> null implies interface.name = interfaceName`), `targetOnlyForSymlink` (`targetPath <> null implies symlink`).

## 7. Package `transport` (spec "Socket Activation", "Transport: AF_UNIX Stream Sockets")

**`SocketActivationEnvironment`**: `listenFds : EInt[1]` (may be 0), `listenPid : ELongObject[0..1]`, `listenPidfdId : ELongObject[0..1]`, `listenFdNames : EString[*]` non-unique (LISTEN_FDNAMES split at `:`). Operation `varlinkFileDescriptor() : EIntegerObject` — `if listenFdNames->includes('varlink') then 2 + listenFdNames->indexOf('varlink') else if listenFds = 1 then 3 else null endif endif` (fixed: a single descriptor is the Varlink one whatever its name, as the spec says LISTEN_FDNAMES only disambiguates when more than one is passed). Constraints `listenFdsNonNegative`, `fdNamesMatchCount` (`listenFdNames->notEmpty() implies listenFdNames->size() = listenFds`), `varlinkSocketNamed` (`listenFds > 1 implies listenFdNames->includes('varlink')`).
**`SocketInode`**: `attributeValue : EString[0..1]` — the raw `user.varlink` value, null when absent (consumers MUST tolerate absence), possibly a value outside the four roles ("Unknown values SHOULD be ignored, to allow the definition of further roles"); derived `role : SocketRole` — the recognised role, null when absent or unknown; `path : EString[0..1]`. Constraints `entrypointHasPath` (`role = SocketRole::entrypoint implies path <> null`), `sockfsRolesHaveNoPath` (`(role = client or server or listen) implies path = null`). This replaces grammar-first's `role : SocketRole[0..1]` (and the EMF judge's `unsettable` suggestion): verified by OCL query, an unset enum attribute evaluates to its default literal `client`, which would have made an untagged, path-bound inode violate `sockfsRolesHaveNoPath`; the string + derived-enum pair represents absent, known and unknown values exactly (`tests/service.xmi` has all three; `role` evaluates to `null` for the absent and the `future-role` inode). **`SocketRole`** (EEnum): `client server listen entrypoint`, quoting the spec table.
Documented only (package documentation): framing, access control (0644), peer authentication (SO_PEERCRED/SO_PEERPIDFD), authorization, file descriptor passing rules, protocol upgrade on the same socket. Peer credentials and passed descriptors are deliberately not classes (section 12).

## 8. Package `http` (spec "Transport: HTTP")

**`HttpBridge`** (root): `baseUrl[1]`, `authentication : BridgeAuthentication = none`, `services → Service[*]` non-containment. Operations encode the spec tables: `statusForError(errorName)` (400/404/501/403/else 500), `statusForFailure(failure : BridgeFailure)` (502/400/404/401), `serviceNameForMethod(qualifiedMethod)` (strip the last component), `callUrl(qualifiedMethod)`, `webSocketUrl(serviceName)`. Constraints `baseUrlSyntax` (http(s)://…/), `servicesNamed` (`services->forAll(s | s.name <> null)`, "each identified by their name"), `serviceNamesUnique`.
**`HttpBridgeAddress`** (: service.ServiceAddress): `scheme : BridgeUrlScheme[1]`, `host[1]`, `port : EIntegerObject[0..1]`, `basePath[1] = /`, `serviceName[1]`; `url()` = `scheme://host[:port]basePath + 'ws/services/' + serviceName`; `addressText()` overrides with `url()`. Constraints `hostNotEmpty`, `basePathSlashes`, `portRange`, `serviceNameWellFormed`.
EEnums: **`BridgeUrlScheme`** (ws, wss, http, https), **`BridgeRoute`** (the seven rows of the URL schema table, each literal documenting method, path and payload), **`BridgeMode`** (simple, webSocket — framing and limitation rules documented on the literals), **`MediaType`** (`applicationJson` literal `application/json`, `applicationJsonSeq` literal `application/json-seq`), **`BridgeFailure`** (transportFailure, malformedRequest, unknownService, authenticationFailed), **`BridgeAuthentication`** (none, mutualTls), **`HttpStatus`** (literal values = status codes 200/400/401/403/404/500/501/502).

## 9. Coverage matrix

### 9.1 Grammar productions → elements

| Production | Element(s) | Admits more than the grammar? |
|---|---|---|
| `interface ::= "interface" interface_name members` | `Interface(name, members[1..*])` | no |
| `members` (≥ 1) | `Interface.members` lowerBound 1 | no |
| `member ::= type_alias \| method \| error` | abstract `Member` → `TypeDefinition`, `Method`, `ErrorDefinition` | no |
| `type_alias ::= "type" name struct \| "type" name enum` | `StructDefinition.body : StructType`, `EnumDefinition.body : EnumType` | the body's inherited `nullable` slot, closed by `bodyNotNullable` |
| `method ::= "method" name struct "->" struct` | `Method.input/output : ParameterStruct` | `nullable` slot closed by `parameterStructsNotNullable`; `ParameterStruct` elsewhere closed by `containedByMethod` |
| `error ::= "error" name struct` | `ErrorDefinition.parameters : StructType` | `nullable` slot closed by `parametersNotNullable` |
| `type ::= [?] (element_type \| "[]" type \| "[string]" type)` | `TypeExpression.nullable` + `ArrayType.elementType` / `MapType.valueType` / `ElementType` | no (`??T` impossible) |
| `element_type ::= struct \| enum \| name \| bool…any` | `StructType`, `EnumType`, `NamedTypeReference`, `BuiltinType(kind)` | no |
| `struct ::= "(" struct_fields ")" \| "(" ")"` | `StructType.fields[0..*]` | no |
| `struct_field ::= field_name ":" type` | `Field(name, type)` | no |
| `enum ::= "(" enum_fields ")"` (≥ 1) | `EnumType.values[1..*]` of `EnumValue` | no |
| `interface_name`, `name`, `field_name` regexes | `nameSyntax` constraints on Interface / Member / Field+EnumValue | no |
| `[string]()` string-set idiom | `MapType.stringSet` | — |
| inline struct/enum at any depth | `CompositeType` under `Field.type`, `ArrayType.elementType`, `MapType.valueType` | — |
| forward references, interface-local names | `NamedTypeReference.definition` resolved after parse, `definitionInSameInterface` | — |
| PEG lexical rules (whitespace, eol, comments) | out of scope (text, not abstract syntax); doc comments per spec in `Declaration.documentation` | — |

### 9.2 Spec sections → elements (M modelled, C constrained, D documented only)

| Spec section | Element(s) | Depth |
|---|---|---|
| Design principles, Terminology | package docs; `Interface`, `Service`, `Message` | D/M |
| Interface Definition, Example | `Interface` …; `org.example.ftl.xmi` | M + instance |
| Keywords, Names | `Interface/TypeDefinition/Method/ErrorDefinition`, `memberNamesUnique`, `qualifiedName`, `nameSyntax` ×4, `nameSegments` | M, C |
| Types table, string set, inline/named | `BuiltinKind`, `StructType`, `EnumType`, `MapType(+stringSet)`, `ArrayType`, `TypeExpression.nullable`, `NamedTypeReference`, `CompositeType.inline` | M |
| Methods, Errors | `Method(input, output)`, `ErrorDefinition(parameters)` | M |
| Documentation Comments | `Declaration.documentation/documentationText`, `systemdMarkersNotInDocumentation` | M, C |
| Grammar / PEG | 9.1 | M |
| Interface Evolution | documented on `TypeExpression.nullable`, `EnumType`, `Interface`, `StandardError.InvalidParameter` | D |
| Mapping the Type System to JSON, Integers, Floats, Nullable/Absent, Unknown Fields | `json` package + docs on every type class/literal; `JsonNumber.lexical/isInteger`, `JsonNull` | M (values) + D (mapping) |
| Wire Protocol, Call, Reply | `protocol.Message/Call/Reply` + 8 constraints | M, C |
| Simple Method Call example | `tests/service.xmi` Exchange /3 carries the spec payload | instance |
| oneway / more / upgrade | `Call` flags, `Exchange` ×6 constraints, systemd `Method.moreSupport/upgradeSupport` | M, C |
| Errors (wire), Vendor Extensions, Connection Lifecycle | `Reply.error/errorDefinition`, `VendorExtension` + `vendorReverseDomain`/`vendorsUnique`; lifecycle D | M, C, D |
| org.varlink.service (IDL, methods, examples, errors table) | `ServiceInformation` (+2 C), `StandardError`, `Service.interfaces`, `Interface.source` | M |
| Service Addresses table, `;` rule | `UnixPathAddress`, `UnixAbstractAddress`, `TcpAddress(+hostKind)`, `ServiceAddress.properties/text()`, 6 C | M, C |
| Socket Activation table | `SocketActivationEnvironment` + 3 C + `varlinkFileDescriptor()` | M, C |
| AF_UNIX framing, access control, peer auth, authorization, fd passing, upgrade | transport package docs | D (decision 12.G11) |
| Recognizing Varlink Socket Inodes | `SocketInode(attributeValue, role, path)`, `SocketRole`, 2 C | M, C |
| Service Registry Directory | `ServiceRegistry`, `RegistryEntry` + 5 C, `Service.registryEntriesNameImplementedInterfaces` | M, C |
| HTTP URL schema, simple mode, streaming, limitations, introspection, WebSocket, auth | `HttpBridge` (+5 ops, 3 C), `BridgeRoute`, `BridgeMode`, `MediaType`, `BridgeFailure`, `HttpStatus`, `BridgeAuthentication`, `HttpBridgeAddress` (+4 C) | M, C (+ D for framing prose) |
| References | out of scope | — |

### 9.3 Corpus check (38 systemd 263 interfaces, including org.varlink.service)

Converted by `tools/python/varlink_xmi.py` (the first 31 also, independently, by the synthesizer's converter, with identical
results), validated under OCL: 38/38 valid. Content: 175+ struct definitions, 114+ enum definitions, 130+ methods (17
`# [Supports 'more' flag]`, 10 `# [Requires 'more' flag]`, and in io.systemd.PTYBroker two `# [Supports 'upgrade' flag]` and
one `# [Requires 'upgrade' flag]`), 140+ errors; 24 interfaces carry interface-level documentation and two carry the
interface-level `# [Experimental]` marker (io.systemd.SysUpdate, io.systemd.SysUpdate.Notify); the `any` builtin occurs in
io.systemd.Metrics. Type-node shapes `ArrayType`, `?ArrayType`, `BuiltinType`, `?BuiltinType`, `?MapType`, `NamedTypeReference`,
`?NamedTypeReference` (no inline composites, nested containers or `[string]()` occur in the corpus; those are covered by
`MyType.xmi`). Keyword field names (`type`, `interface`), Python-keyword enum values (`null`, `continue`, `default`), the
two-component interface name `io.systemd`, non-ASCII `µs` in comments, and io.systemd.Unit at 2127 objects are all representable.
Note that introspected text is not in author order: systemd's formatter emits enum types, struct types, methods, then errors.

## 10. systemd extensions (not in the UAPI.20 grammar)

Facts from `sd-varlink-idl.c/.h` (treated as data): symbol flags `SUPPORTS_MORE`, `REQUIRES_MORE`, `SUPPORTS_UPGRADE`, `REQUIRES_UPGRADE`; `SD_VARLINK_EXPERIMENTAL` on interface, symbol, field and enum value. The formatter emits, before `method`, first the more line (`# [Requires 'more' flag]` if the REQUIRES bit is set, else `# [Supports 'more' flag]`), then the upgrade line, then `# [Experimental]` ("Output this last … since the parser turns those into regular comments"); `# [Experimental]` precedes `interface`, `type`, `method`, `error` and (indented) a field or enum value; the parser recognises exactly that text and strips it. systemd's parser does **not** turn the flag comments back into bits (varlink-http-bridge interprets the text; systemd declares it API: "don't change, only extend"). Validator rules (`varlink_idl_symbol_consistent`): (1) an experimental field of a non-experimental symbol must be nullable; (2) an experimental enum value may only appear in an experimental enum; (3) line 1742: a non-experimental field must not refer to an experimental type.

Modelled, each documented with the leading sentence "systemd extension, not in UAPI.20 grammar":

| Element | Meaning |
|---|---|
| `Method.moreSupport`, `Method.upgradeSupport : CallFlagSupport {unspecified, supported, required}` | the flag lines; `unspecified` is the only state a pure UAPI.20 parser produces and does not mean "unsupported" |
| `Method.supportsMore / requiresMore / supportsUpgrade / requiresUpgrade` (derived) | the two questions a template asks per flag |
| `Declaration.experimental` on Interface, Member, Field, EnumValue | the `# [Experimental]` line |
| `InterfaceElement.effectiveExperimental()` | inherited experimental context |
| `Field.systemdExperimentalFieldNullable`, `EnumValue.systemdExperimentalValueInExperimentalEnum`, `NamedTypeReference.systemdExperimentalTypeUsedInExperimentalContext` | the three validator rules, prefixed `systemd` |
| `Declaration.systemdMarkersNotInDocumentation` | marker lines never enter `documentation` |

Parsing rule for a modeller: a comment block before a declaration is split into documentation lines and marker lines; marker lines set the flags and are removed. In the corpus the flag line is always the last comment line before `method` (e.g. `# List running machines` / `# [Supports 'more' flag]`).

## 11. Navigating the model for the Python generator

### 11.1 `io.systemd.Machine.List`

Source (corpus, abbreviated):
```
# List running machines
# [Supports 'more' flag]
method List(
    # If non-null the name of a machine.
    name: ?string,
    # If non-null the PID of a machine. Special value 0 means ...
    pid: ?ProcessId,
    allowInteractiveAuthentication: ?bool,
    acquireMetadata: ?AcquireMetadata
) -> (
    # Name of the machine
    name: string,
    id: ?string, service: ?string,
    # The class of this machine
    class: MachineClass,
    leader: ?ProcessId, ..., addresses: ?[]Address, OSRelease: ?[]string, UIDShift: ?int, ..., UID: ?int
)
```
Model (`samples/systemd-263/io.systemd.Machine.xmi`): `Interface(name='io.systemd.Machine').members[name='List']` is a `Method` with `documentation = ['List running machines']`, `moreSupport = supported`, `input = ParameterStruct(direction=input, fields=[Field('name', BuiltinType(string, nullable)), Field('pid', NamedTypeReference(typeName='ProcessId', definition → StructDefinition ProcessId, nullable)), Field('allowInteractiveAuthentication', BuiltinType(bool, nullable)), Field('acquireMetadata', NamedTypeReference(→ EnumDefinition AcquireMetadata, nullable))])`, `output = ParameterStruct(direction=output, fields=[Field('name', BuiltinType(string)), …, Field('class', NamedTypeReference(→ EnumDefinition MachineClass)), Field('addresses', ArrayType(nullable, elementType=NamedTypeReference(→ StructDefinition Address))), …])`.

Acceleo 4 / AQL steps, no string parsing anywhere (every expression is either a stored feature, a resolved reference or an OCL-derived feature; pure-AQL fallbacks exist for the derived ones, e.g. `i.name.tokenize('.')`):

1. **Module**: `i.nameSegments` → `['io','systemd','Machine']` → one module per interface, e.g. `io_systemd_machine.py` (a 1:1 package path does not work: `io.systemd` and `io.systemd.Machine` both exist, `Import` is a keyword); module docstring `i.documentationText` (lines verbatim, `\n`-joined).
2. **Types, in dependency order**: `[for (d : StructDefinition | i.members->filter(StructDefinition))]` → `@dataclass class ProcessId:` with one attribute per `d.body.fields` (typed by step 4; `f.documentationText` as the attribute comment); `[for (e : EnumDefinition | i.members->filter(EnumDefinition))]` → `class MachineClass(enum.StrEnum)` with one member per `e.body.values` (`v.name`, escaped if a Python keyword; `v.documentationText`). Order by `d.usages`/`definition` edges if forward references matter for the target language.
3. **Method**: `[for (m : Method | i.methods)]`; Python name from `m.name` (`List` → `list_` to avoid the builtin); docstring `m.documentationText`; wire name `m.qualifiedName` = `'io.systemd.Machine.List'`.
4. **Parameters**: `[for (f : Field | m.inputParameters)]` in order; name `f.name` (escape `class` → `class_`, keep the real key for the wire); annotation `py(f.type)` with the template
   `py(t) = [if (t.nullable)]Optional[[core(t)/]][else][core(t)/][/if]`,
   `core(t : BuiltinType)` by `t.kind` (bool→`bool`, int→`int`, float→`float`, string→`str`, object→`dict[str, Any]`, any→`Any`),
   `core(t : ArrayType)` → `list[[py(t.elementType)/]]`, `core(t : MapType)` → `set[str]` if `t.stringSet` else `dict[str, [py(t.valueType)/]]`,
   `core(t : NamedTypeReference)` → `t.definition.name`,
   `core(t : StructType)` / `core(t : EnumType)` (inline, `t.inline`) → a class named `t.positionName()` (e.g. `List__output__addresses`; `'__'` is the only collision-free separator, since field names may contain single underscores) or `Literal['a', 'b']`.
   Required parameters first: `m.inputParameters->select(f | not f.nullable)` then the nullable ones with default `None`.
   Result: `async def list_(self, *, name: Optional[str] = None, pid: Optional[ProcessId] = None, allow_interactive_authentication: Optional[bool] = None, acquire_metadata: Optional[AcquireMetadata] = None) -> ListReply`.
5. **Reply type**: `ListReply` dataclass from `m.outputParameters` (`class_: MachineClass`, `addresses: Optional[list[Address]] = None`, …); name from `m.output.positionName()` = `List__output`.
6. **Flags**: `[if (m.requiresMore)]` emit only `async def list_(...) -> AsyncIterator[ListReply]`; `[elseif (m.supportsMore)]` (this case) emit both the single-reply coroutine and `list_more(...) -> AsyncIterator[ListReply]`; otherwise single only. `m.supportsUpgrade`/`requiresUpgrade` likewise select an upgrade variant returning the raw connection.
7. **Wire call**: the binding builds `protocol.Call(method = m.qualifiedName, parameters = JsonObject from the kwargs by f.name, more = True)`, reads `Reply.parameters` until a reply with `continues = false` (`Exchange` states the rules), and maps `Reply.error` to an exception class (step 11.2).

### 11.2 Errors

`io.systemd.Machine.NoSuchMachine` (`# No matching machine currently running` / `error NoSuchMachine()`): `ErrorDefinition(name='NoSuchMachine', documentation=['No matching machine currently running'], parameters=StructType(fields=[]))`. Template: `[for (e : ErrorDefinition | i.errors)] class [e.name/](VarlinkError): """[e.documentationText/]"""  NAME = '[e.qualifiedName/]'` with one dataclass attribute per `e.parameters.fields` (none here). `org.varlink.service.InvalidParameter (parameter: string)` gives `parameter: str` from `e.parameters.fields->first()` (`f.name`, `py(f.type)`); the seven generic errors are also available as the closed `service.StandardError` set for a binding's base exceptions, and `http.HttpBridge.statusForError(e.qualifiedName)` gives the bridge status. A reply is dispatched by `Reply.error` (`Reply.errorReply` true) → `i.findError(Call.methodName…)`/`Reply.errorDefinition` when the link is resolved.

### 11.3 Where the judges' template warts went

| Judge wart (grammar-first) | Now |
|---|---|
| `t.body.oclAsType(EnumType)` casts at the TypeDefinition boundary | `StructDefinition.body : StructType`, `EnumDefinition.body : EnumType`; polymorphic templates |
| `f.type.nullable` | `f.nullable` (derived) |
| `m.moreSupport = CallFlagSupport::required` | `m.requiresMore` / `m.supportsMore` |
| `isStringSet()` operation | `stringSet` attribute |
| `eContainingFeature().name` to tell parameter lists / inline composites from bodies | `ParameterStruct.direction`, `CompositeType.inline`, `TypeExpression.positionPath()` |
| naming anonymous types by hand | `positionPath()` (unique, stable) + `enclosingField()`, `enclosingFields()`, `enclosingMember()` |
| no `usages` inverse | `TypeDefinition.usages` |
| `member(name)` only | `findMember/findType/findMethod/findError/findField` |

## 12. Decision log

### 12.1 Defects reported against grammar-first (the base)

| # | Defect (judge) | Applied? | How / why |
|---|---|---|---|
| D1 | Third systemd rule missing (fidelity) | yes | `NamedTypeReference.systemdExperimentalTypeUsedInExperimentalContext`; fires on `tests/negative.xmi` /2 |
| D2 | `CallFlagSupport.unsupported` mislabels the no-marker state (all three) | yes | literal renamed `unspecified`, documentation from generator-first ("the only state an interface definition can express; does not mean not supported") |
| D3 | `nullable` slot on bare-struct positions, closed only by constraints (fidelity, generator) | kept, documented | the alternative is the Struct/Enumeration mixin layering that loses constraints under stock validation (the judges' major defect of generator-first) or a wrapper node per inline composite; `ParameterStruct` now at least makes the parameter positions a distinct class and `TypeExpression`'s documentation states that the slot is always false in bare positions. Requirement 2 explicitly allows a documented constraint. |
| D4 | No `usages` inverse, raw type name derived only (all three) | yes | `TypeDefinition.usages` transient opposite, `definition.resolveProxies=false`; `typeName` is now a **required stored** token with `typeNameMatchesDefinition` (mof-purist's form, chosen by two judges over generator-first's optional one, which gave one syntax two encodings) |
| D5 | `HttpBridgeAddress`/`BridgeUrlScheme` in `service`; no registry root (fidelity, EMF) | yes | both moved to `http`; `ServiceRegistry` root added (12.2 G8) |
| D6 | `Reply.isError` generates `isIsError()` (EMF) | yes | renamed `errorReply` |
| D7 | `SocketInode.role` [0..1] without `unsettable` (EMF) | yes, differently | `attributeValue : EString[0..1]` + derived `role`; an unsettable enum reads as `client` in OCL (verified), and the spec's "unknown values" need a string anyway (section 7) |
| D8 | `AddressProperty` class for an opaque string (EMF) | yes | `ServiceAddress.properties : EString[*]` + `propertiesWellFormed` |
| D9 | operation parameters named `name` (EMF) | yes | `memberName`, `typeName`, `methodName`, `errorName`, `fieldName`, `interfaceName`, `qualifiedMethod`, `serviceName`; every EParameter documented |
| D10 | `Interface.members [1..*]` makes a fresh Interface invalid in Sirius (EMF, generator) | kept | the grammar requires ≥ 1 member and the fidelity judge gave mof-purist a *major* for admitting an empty interface; a Sirius creation tool adds the first member |
| D11 | no eKeys (EMF) | yes | `eKeys = name` on `members`, `fields`, `values`; name-keyed fragments used in all instances |
| D12 | `HttpBridge.serviceNamesUnique` over an optional name rejects two unnamed services (generator) | yes | `servicesNamed` + `serviceNamesUnique`: a bridge identifies services by name, so an unnamed served service is the error |
| D13 | `StandardError` duplicates the org.varlink.service IDL; `statusForError` takes a string (generator) | kept, documented | the closed set is what a binding and the bridge mapping need; `statusForError(e.qualifiedName)` works for any error; the IDL remains an ordinary Interface instance |
| D14 | `Exchange` is a non-wire convenience (generator) | kept | it is the only way the oneway/more/upgrade sequencing prose becomes checkable (fidelity judge counted it as a strength) |
| D15 | `varlinkFileDescriptor()` null for `LISTEN_FDS=1` + `LISTEN_FDNAMES=other` (EMF, "debatable") | yes | returns 3 whenever exactly one descriptor is passed (spec: names only disambiguate when more than one is passed); null otherwise (never *invalid*, unlike generator-first) |
| D16 | `listenFds >= 0` nit (generator) | kept | LISTEN_FDS=0 is a legal environment (variable set, nothing passed); documented |
| D17 | EParameters undocumented (all three) | yes | all 12 documented; `ecorecheck.py` enforces it |

### 12.2 Grafts proposed by the judges

| # | Graft | Applied? | How / why |
|---|---|---|---|
| G1 | `unspecified` literal + documentation (all three) | yes | see D2 |
| G2 | third systemd rule (fidelity) | yes | see D1 |
| G3 | derived `Field.nullable`, `Method.inputParameters/outputParameters`, `supportsMore/requiresMore/supportsUpgrade/requiresUpgrade` (fidelity, generator, EMF) | yes | all six derived; the enums stay the stored truth (three states), the booleans are the template view |
| G4 | `enclosingField()`, `enclosingMember()` + a stable anonymous-type name (fidelity, generator, EMF) | yes, extended | plus `enclosingFields()` and `positionPath()` (a *path*, so the generator chooses its own join/casing convention; uniqueness argued in the ecore documentation and verified on `MyType.xmi`) |
| G5 | `TypeDefinition.usages` transient opposite (all three) | yes | see D4 |
| G6 | stored raw token (mof-purist form, required) vs optional `typeName` (generator-first form) | mof form | required avoids two encodings of one syntax; `text()` uses it |
| G7 | `findType/findMethod/findError` and `Interface.source` (fidelity, generator; EMF: "only if wanted") | yes | lookups added (plus `findField`); `source` added as optional because a binding serves the original text and it is not an alternative encoding of the syntax (documented) |
| G8 | `ServiceRegistry(directory, entries)` root with `RegistryEntry.registry` opposite and derived `path` (all three) | yes | in `service` (not `transport`) to avoid a package cycle; `Service.registryEntries` kept as the non-containment opposite of `RegistryEntry.service`, so grammar-first's `registryEntriesNameImplementedInterfaces` survives; serialization side documented |
| G9 | `MediaType` EEnum with literal values (all three) | yes | in `http` |
| G10 | move the bridge address to `http` (fidelity, EMF) | yes | see D5; required the polymorphic `addressText()` (G13) |
| G11 | `transport.PeerCredentials`, `PassedFileDescriptor`, `Message.fileDescriptors` (generator; fidelity: credentials optional, fd passing prose; EMF: scope creep) | **no** | the spec keeps the protocol "intentionally free of such transport-specific side channels" and the fidelity judge flagged `Message.fileDescriptors` as a defect; credentials are a property of a *connection*, and the model has no connection object (adding one was the scope creep the EMF judge dinged). Both are documented in full on the `transport` package; a fd-carrying `int` field has no IDL syntax to key on (the spec gap all designs noted, open question 14.3). |
| G12 | `ParameterStruct` with derived `method`/`direction` (generator) | yes | single-inheritance subclass of `StructType`, so dynamic validation still runs `fieldNamesUnique` on it (verified: the `Dup` method's duplicate-free input is fine, `tests/negative.xmi` reports `fieldNamesUnique` on a named body); `containedByMethod` keeps it out of other positions |
| G13 | abstract `ServiceAddress.toText()` overridden per class (EMF) | yes | as `addressText()`; `text()` adds the `;` properties (mof-purist omitted them) |
| G14 | `properties : EString[*]` (EMF) | yes | see D8 |
| G15 | `documentationText` as a derived attribute (EMF) | yes | returns `''` when undocumented (string-safe for templates) |
| G16 | `StructDefinition`/`EnumDefinition` concrete subclasses (generator, EMF) | yes, with typed bodies | `body : StructType` / `body : EnumType` on the subclasses instead of a shared `body : CompositeType` plus `oclIsKindOf` constraints: the two grammar alternatives become structure, two constraints disappear, templates need no cast; `definedType()` gives the generic view |
| G17 | `MapType.isStringSet()` → derived `stringSet` (generator) | yes | |
| G18 | genmodel `basePackage dk.ingi`, Feature Delegation = Dynamic, Operation Reflection = true (EMF) | noted (section 14) | the genmodel is not part of this deliverable |
| G19 | rename `IdlElement`-style abbreviations / `Enumeration` / `Method.more` (all, about generator-first) | n/a | the base never had them; grammar-first's names kept (`InterfaceElement`, `BuiltinType`, `moreSupport`) |

### 12.3 Things taken from the other designs without a judge asking

* `BuiltinType.keyword()` (generator-first) so `text()` and templates share one keyword mapping.
* `JsonNumber.lexical` documentation example values (generator-first).
* `Declaration.systemdMarkersNotInDocumentation` (the gap the generator judge listed for all three).
* The spec's "Unknown values SHOULD be ignored" for socket inodes, which no design represented.

### 12.4 Adversarial refutation round (five finders, two skeptics per finding)

Applied (each demonstrated with executable evidence by a finder and not refuted by both skeptics):

| Finding | Change |
|---|---|
| emf-1/2/3: the OCL Pivot code generator embeds compiled OCL that folds null guards (generated getters threw on incomplete objects), reports violations as warnings and needs `org.eclipse.ocl.pivot` at compile time | genmodel annotation `http://www.eclipse.org/OCL/GenModel` `Use Delegates = true` + feature delegation Dynamic: bodies are evaluated by the Pivot delegates (section 14) |
| emf-4: label derivations not total on fresh elements | null-safe `fileName()`, `nameSegments`, `qualifiedName`, `text()`, `Call.methodName` |
| emf-6: unnamed siblings share a name-keyed fragment | documented on `Interface.members`; creation tools assign default names |
| emf-7: wrong serialization claim | corrected on `Service.registryEntries` / `RegistryEntry.service` and in section 6 |
| emf-9: `isSupportsMore()` accessors | derived booleans renamed `supportsMore`, `requiresMore`, `supportsUpgrade`, `requiresUpgrade` |
| emf-10 / critic-4: enums typed by no feature | documented as closed documentation sets (`StandardError`, `BridgeRoute`, `BridgeMode`, `MediaType`) |
| emf-11: silent enum default, loose IPv4 regex | `HttpBridgeAddress.scheme` documented; `TcpAddress.hostKind` uses an exact octet regex |
| fidelity-1 / corpus-2: wrong trailing-comma sentence | `StructType` documentation corrected (rejected by spec and systemd) |
| fidelity-2: separators inside address components | `pathWithoutPropertySeparator`, `nameWithoutPropertySeparator`, `hostWithoutPropertySeparator`, `hostColonOnlyInIpv6`, `serviceNameWithoutPropertySeparator`, `fdNamesWithoutColon` |
| fidelity-3: documentation entries with embedded line terminators | `Declaration.documentationLinesSingle` |
| fidelity-4: registry entry for an interface known only from GetInfo rejected | `registryEntriesNameImplementedInterfaces` now uses `implementsInterface()` |
| fidelity-5 / critic-2: aborted 'more' stream | `Exchange` documented as a complete exchange (not a structural change) |
| fidelity-7 (refuted, partly kept): registry directory spelled with a trailing slash | `directoryAbsolute` accepts it and `path` normalises; `interfaceNameSyntax` stays, since systemd 263's `varlinkctl list-registry` skips entries not named like an interface (verified on nacos) |
| fidelity-8: unattributed quotations | `ServiceInformation` documentation attributes them to systemd's org.varlink.service.varlink |
| fidelity-9: `Interface.source` unchecked | `sourceNamesThisInterface` |
| corpus-1: interface-level documentation and `[Experimental]` markers were dropped by the corpus splitter | corpus rebuilt (`tools/python/split_introspect.py`), 24 interfaces with interface docs, two experimental |
| corpus-3: comment attachment rule unformalised | stated in `Declaration.documentation` |
| corpus-4: a flag-marker line before a non-method is ordinary text for systemd but was forbidden everywhere | `systemdMarkersNotInDocumentation` now covers only `[Experimental]`; new `Method.flagMarkersNotInDocumentation` |
| corpus-5: 7 more nacos interfaces (upgrade flags, `any`) | added to the corpus (38 interfaces); member order note |
| corpus-6: converter nits | `varlink_xmi.py` writes `true`; flag lines before non-methods stay in documentation |
| generator-2: anonymous-type naming collisions | new `positionName()` joins `positionPath()` with `'__'`, the only separator no segment can contain |
| critic-3: members `[1..*]` stricter than systemd | kept (spec grammar), dialect difference documented on `Interface.members` |
| critic-6: module path collisions in section 11 | corrected (one module per interface) |

Refuted by both skeptics and therefore not applied: critic-1 / generator-1 (a modeller-set `Field.fileDescriptorIndex`; the
spec has no syntax for it and keeps fd passing out of the protocol — left as the open question in section 14), critic-5
(dropping or splitting off the deployment packages), fidelity-6 (vendor-key regex), emf-8 (Java 27 compliance: the JDT in
this Eclipse formats at 26 and warns, which is harmless; the level follows the project's own JRE setting), emf-9 (renaming
`supportsMore` etc.: verb-phrase booleans are EMF's own house style and the names are the camelCase of systemd's
`SD_VARLINK_SUPPORTS_MORE` flags), generator-3 (`inline` is grammatically true for the `[string]()` value struct; `stringSet`
is the rendering hint), generator-4 (an error's parameter struct has the bare member name as its `positionPath()`, like a
type definition's body; only methods need a direction token). fidelity-7 and fidelity-9 were refuted as cosmetic but their
trailing-slash relaxation and the `sourceNamesThisInterface` sanity check were kept.

## 13. OCL inventory (all executed by OCL Pivot 1.24 through the unchanged Diagnostician)

Constraints (70): root 21 — `Declaration.systemdMarkersNotInDocumentation/documentationLinesSingle`, `Interface.nameSyntax/memberNamesUnique/sourceNamesThisInterface`, `Member.nameSyntax`, `StructDefinition.bodyNotNullable`, `EnumDefinition.bodyNotNullable`, `Method.parameterStructsNotNullable/flagMarkersNotInDocumentation`, `ErrorDefinition.parametersNotNullable`, `Field.nameSyntax/systemdExperimentalFieldNullable`, `EnumValue.nameSyntax/systemdExperimentalValueInExperimentalEnum`, `NamedTypeReference.typeNameMatchesDefinition/definitionInSameInterface/systemdExperimentalTypeUsedInExperimentalContext`, `StructType.fieldNamesUnique`, `ParameterStruct.containedByMethod`, `EnumType.valueNamesUnique`; json 2 — `JsonObject.memberNamesUnique`, `JsonNumber.lexicalSyntax`; protocol 14 — `Message.vendorsUnique`, `Call.atMostOneFlag/methodQualified/methodDefinitionMatches`, `Reply.errorReplyNeverContinues/errorQualified/errorDefinitionMatches`, `VendorExtension.vendorReverseDomain`, `Exchange.onewayHasNoReplies/singleReplyUnlessMore/continuesOnlyWhenMore/finalReplyTerminates/intermediateRepliesContinue/upgradeConfirmedOnce`; service 19 — `Service.interfaceNamesUnique/informationListsImplementedInterfaces/registryEntriesNameImplementedInterfaces`, `ServiceInformation.includesVarlinkService/interfaceNamesWellFormed`, `ServiceAddress.propertiesWellFormed`, `UnixPathAddress.pathNotEmpty/pathWithoutPropertySeparator`, `UnixAbstractAddress.nameNotEmpty/nameWithoutPropertySeparator`, `TcpAddress.portRange/hostNotBracketed/hostWithoutPropertySeparator/hostColonOnlyInIpv6`, `ServiceRegistry.directoryAbsolute/entryNamesUnique`, `RegistryEntry.interfaceNameSyntax/interfaceMatches/targetOnlyForSymlink`; transport 6 — `SocketActivationEnvironment.listenFdsNonNegative/fdNamesMatchCount/varlinkSocketNamed/fdNamesWithoutColon`, `SocketInode.entrypointHasPath/sockfsRolesHaveNoPath`; http 8 — `HttpBridge.baseUrlSyntax/servicesNamed/serviceNamesUnique`, `HttpBridgeAddress.hostNotEmpty/basePathSlashes/portRange/serviceNameWellFormed/serviceNameWithoutPropertySeparator`. The 61 constraints inherited from the synthesis are planted and fire by name in `samples/negative.xmi` (root package) and `samples/negative-packages.xmi` (the other packages; the `.probe` files list the expected names per root); the 9 added by the refutation round are exercised by `samples/refute-probe.xmi`. All 70 evaluate to true on the positive instances (`org.example.ftl.xmi`, `MyType.xmi`, `service.xmi`, the 38 corpus files).

Derived features (23): `Declaration.documentationText`, `Interface.types/methods/errors/nameSegments`, `Member.qualifiedName`, `Method.inputParameters/outputParameters/supportsMore/requiresMore/supportsUpgrade/requiresUpgrade`, `Field.nullable`, `MapType.stringSet`, `CompositeType.inline`, `ParameterStruct.method/direction`, `Call.interfaceName/methodName`, `Reply.errorReply`, `TcpAddress.hostKind`, `RegistryEntry.path`, `SocketInode.role`.

Operations (32): `InterfaceElement.owningInterface/enclosingMember/effectiveExperimental`, `Interface.findMember/findType/findMethod/findError/fileName`, `TypeDefinition.definedType`, `TypeExpression.text/enclosingField/enclosingFields/positionPath/positionName`, `BuiltinType.keyword`, `StructType.findField`, `JsonObject.member`, `JsonNumber.isInteger`, `Service.implementsInterface`, `ServiceAddress.text/addressText` (abstract), `UnixPathAddress/UnixAbstractAddress/TcpAddress/HttpBridgeAddress.addressText`, `SocketActivationEnvironment.varlinkFileDescriptor`, `HttpBridge.statusForError/statusForFailure/serviceNameForMethod/callUrl/webSocketUrl`, `HttpBridgeAddress.url`.

Pivot facts relied on (confirmed by execution): `indexOf`/`substring` are 1-based and `indexOf` returns 0 when absent; `Sequence{1..0}` is empty; `oclContainer()` is null at a root; `->select` + `isEmpty()` instead of `->any()` (invalid on no match); enum literal `toString()` is fully qualified (hence `keyword()` and the scheme if-chain); typed `let x : Sequence(String) = Sequence{}` is needed to give an empty literal a useful type; an EOperation returning a Sequence must be `unique="false"`; overriding an abstract EOperation in subclasses dispatches on the runtime type even when called from the base's own body; a derived EEnum attribute may evaluate to null, a stored unsettable one reads as its default.

## 14. GenModel notes and open questions

1. `model/model.genmodel` is generated from the Ecore by `tools/emf/genmodel.sh` with basePackage `dk.ingi` (root package
   `varlink` → Java packages `dk.ingi.varlink`, `dk.ingi.varlink.json`, …), prefix `Varlink`, Java 27, *Operation Reflection*
   on, *Feature Delegation* Dynamic and the OCL GenModel option *Use Delegates* = true. With OCL Pivot installed, EMF would
   otherwise compile every OCL body into the `*Impl` classes; the refutation round showed that this compiled form folds the
   null guards away (derived getters throw on half-built objects, e.g. while editing in Sirius), reports constraint violations
   as warnings and needs `org.eclipse.ocl.pivot` on the compile classpath. With delegates the generated code evaluates the
   bodies through the Pivot setting/invocation/validation delegates at runtime (the bundle still requires
   `org.eclipse.ocl.pivot` so the delegate is present). Verified headlessly: 149 sources, 167 classes compile. No EClass
   clashes with `java.lang` (`ErrorDefinition`, `TypeDefinition`, `Json*`, `BuiltinKind.object`), `Member.interface` follows
   Ecore's own `EClass.interface` precedent, `errorReply` avoids `isIsError()`; the flag booleans read `isSupportsMore()` etc., EMF's usual verb-phrase form.
2. `Interface.members[1..*]`: a Sirius creation tool should create the first member with the interface; otherwise the fresh diagram shows one multiplicity error until it does.
3. File-descriptor-carrying `int` fields (e.g. io.systemd.Machine.Open's pty descriptor index) have no IDL syntax; a modeller-set `Field.fileDescriptorIndex` would let a generator return a real fd object but is neither in the spec nor in systemd's IDL. Left out; open question for Pétur.
4. Non-documentation comments (trailing comments, comments before `)`) are not documentation per the spec and have no node; a round-tripping formatter would need an extra `Comment` node. Out of scope by design.
5. An EEnum attribute with lowerBound 1 (`BuiltinType.kind`, `HttpBridgeAddress.scheme`) is never reported as unset by EMF (eGet yields the first literal), so an XMI `<type xsi:type="varlink:BuiltinType"/>` silently means `bool`. An EMF-wide idiom, shared by all three designs; `tools/python/varlink_xmi.py` always writes `kind`.
6. `tools/emf/emfcheck-ocl.sh` is the project's validator for instances (the stock checker plus the OCL Pivot delegate); Eclipse's own validation (right-click → Validate) does the same inside the IDE.
