# tools/emf — headless EMF with the local Eclipse install

No pyecore, no reimplementation: these scripts drive the genuine EMF 2.42 / OCL Pivot 1.24 runtime that
ships in `~/Applications/Eclipse.app` (override with `ECLIPSE=.../Eclipse.app/Contents/Eclipse`). Java 27 on
PATH is used for everything except the headless generator, which runs on the JRE bundled with Eclipse.

```
./build.sh                                   # compile src/*.java, build the OCL agent, resolve the OCL jars
./emfcheck.sh     ../../model/model.ecore ../../samples/org.example.ftl.xmi   # structure + Diagnostician
./emfcheck-ocl.sh ../../model/model.ecore ../../samples/*.xmi                 # same, with OCL evaluated
./oclprobe.sh     ../../model/model.ecore ../../samples/MyType.xmi            # print every derived value
./genmodel.sh     ../../model/model.ecore ../../model/model.genmodel          # rebuild the genmodel
./codegen.sh                                  # generate + compile Java in a scratch workspace
```

Results end with `RESULT: OK` / `RESULT: ERRORS`; exit code 0 means no errors.

Sources: `EmfCheck.java` (validator), `GenModelBuilder.java` (genmodel from Ecore), `OclAgent.java`
(`-javaagent` that appends the OCL/Xtext jars and calls `OCLDelegateDomain.initialize`, which is what
Eclipse does through its plugin registry), `OclProbe.java` (evaluates derivations and operation bodies).
