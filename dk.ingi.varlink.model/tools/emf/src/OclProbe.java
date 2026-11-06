import java.util.*;
import org.eclipse.emf.common.util.*;
import org.eclipse.emf.ecore.*;
import org.eclipse.emf.ecore.resource.*;
import org.eclipse.emf.ecore.resource.impl.*;
import org.eclipse.emf.ecore.util.*;
import org.eclipse.emf.ecore.xmi.impl.*;

/** Usage (with the OCL agent): OclProbe model.ecore instance.xmi ...
 *  Evaluates every derived feature and every OCL-bodied EOperation on every object of the instances
 *  (so every OCL derivation/body is parsed and executed), then validates each root with Diagnostician
 *  (so every OCL constraint is parsed and executed). */
public class OclProbe {
    static int failures = 0;
    public static void main(String[] args) throws Exception {
        ResourceSet rs = new ResourceSetImpl();
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("ecore", new EcoreResourceFactoryImpl());
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("*", new XMIResourceFactoryImpl());
        Resource r = rs.getResource(URI.createFileURI(new java.io.File(args[0]).getAbsolutePath()), true);
        for (EObject root : r.getContents()) if (root instanceof EPackage p) registerAll(rs, p);
        for (int i = 1; i < args.length; i++) {
            System.out.println("== " + args[i]);
            Resource ir = rs.getResource(URI.createFileURI(new java.io.File(args[i]).getAbsolutePath()), true);
            EcoreUtil.resolveAll(ir);
            for (Resource.Diagnostic e : ir.getErrors()) { System.out.println("LOAD ERROR: " + e.getMessage()); failures++; }
            for (Iterator<EObject> it = ir.getAllContents(); it.hasNext();) {
                EObject o = it.next();
                String id = o.eClass().getName() + "@" + EcoreUtil.getURI(o).fragment();
                for (EStructuralFeature f : o.eClass().getEAllStructuralFeatures()) {
                    if (!f.isDerived()) continue;
                    try { System.out.println("  " + id + "." + f.getName() + " = " + show(o.eGet(f))); }
                    catch (Throwable t) { failures++; System.out.println("  FAIL " + id + "." + f.getName() + ": " + t); }
                }
                for (EOperation op : o.eClass().getEAllOperations()) {
                    if (EcoreUtil.getAnnotation(op, "http://www.eclipse.org/emf/2002/Ecore/OCL/Pivot", "body") == null) continue;
                    EList<Object> a = new BasicEList<>();
                    for (EParameter p : op.getEParameters()) a.add(sampleArg(o, op));
                    try { System.out.println("  " + id + "." + op.getName() + a + " = " + show(o.eInvoke(op, a))); }
                    catch (Throwable t) { failures++; System.out.println("  FAIL " + id + "." + op.getName() + a + ": " + t); }
                }
            }
            int errs = 0;
            for (EObject root : ir.getContents()) {
                Diagnostic d = Diagnostician.INSTANCE.validate(root);
                errs += dump(d, "  ");
            }
            System.out.println("  -> " + errs + " constraint violations in " + args[i]);
        }
        System.out.println(failures == 0 ? "PROBE: OK (all derivations and bodies evaluated)" : "PROBE: " + failures + " FAILURES");
    }
    static Object sampleArg(EObject o, EOperation op) {
        if (op.getName().equals("member") && o.eClass().getName().equals("Interface")) {
            EStructuralFeature m = o.eClass().getEStructuralFeature("members");
            List<?> l = (List<?>) o.eGet(m);
            if (!l.isEmpty()) { EObject first = (EObject) l.get(0); return first.eGet(first.eClass().getEStructuralFeature("name")); }
            return "Nothing";
        }
        return "org.varlink.service.MethodNotFound";
    }
    static int dump(Diagnostic d, String indent) {
        int n = 0;
        if (d.getSeverity() != Diagnostic.OK && d.getChildren().isEmpty()) {
            Object target = d.getData().isEmpty() ? null : d.getData().get(0);
            String where = (target instanceof EObject eo) ? " @ " + eo.eClass().getName() + "#" + EcoreUtil.getURI(eo).fragment() : "";
            System.out.println(indent + (d.getSeverity() >= Diagnostic.ERROR ? "ERROR" : "WARN") + ": " + d.getMessage() + where);
            if (d.getSeverity() >= Diagnostic.ERROR) n++;
        }
        for (Diagnostic c : d.getChildren()) n += dump(c, indent);
        return n;
    }
    static String show(Object v) {
        if (v instanceof EObject eo) return eo.eClass().getName() + "#" + EcoreUtil.getURI(eo).fragment();
        if (v instanceof List<?> l) { StringBuilder sb = new StringBuilder("["); for (Object x : l) sb.append(sb.length() > 1 ? ", " : "").append(show(x)); return sb + "]"; }
        return String.valueOf(v);
    }
    static void registerAll(ResourceSet rs, EPackage p) { rs.getPackageRegistry().put(p.getNsURI(), p); for (EPackage s : p.getESubpackages()) registerAll(rs, s); }
}
