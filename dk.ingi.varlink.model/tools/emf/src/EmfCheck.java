import java.util.*;
import org.eclipse.emf.common.util.*;
import org.eclipse.emf.ecore.*;
import org.eclipse.emf.ecore.resource.*;
import org.eclipse.emf.ecore.resource.impl.*;
import org.eclipse.emf.ecore.util.*;
import org.eclipse.emf.ecore.xmi.impl.*;

/** Usage: EmfCheck model.ecore [instance.xmi ...]
 *  Loads the Ecore with the genuine EMF runtime, validates it with Diagnostician,
 *  then (optionally) loads XMI instances against it and validates those too.
 *  Exit code: 0 = no errors, 1 = errors found, 2 = load failure. */
public class EmfCheck {
    static int worst = Diagnostic.OK;
    static void dump(Diagnostic d, String indent) {
        if (d.getSeverity() != Diagnostic.OK) {
            String sev = d.getSeverity() == Diagnostic.ERROR ? "ERROR" : d.getSeverity() == Diagnostic.WARNING ? "WARN" : "INFO";
            Object target = d.getData().isEmpty() ? null : d.getData().get(0);
            String where = (target instanceof EObject eo) ? " @ " + EcoreUtil.getURI(eo) : "";
            if (!d.getChildren().isEmpty() && d.getMessage().startsWith("Diagnosis of")) { /* root */ }
            else System.out.println(indent + sev + ": " + d.getMessage() + where);
            worst = Math.max(worst, d.getSeverity());
        }
        for (Diagnostic c : d.getChildren()) dump(c, indent + "  ");
    }
    public static void main(String[] args) throws Exception {
        ResourceSet rs = new ResourceSetImpl();
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("ecore", new EcoreResourceFactoryImpl());
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("*", new XMIResourceFactoryImpl());
        rs.getPackageRegistry().put(EcorePackage.eNS_URI, EcorePackage.eINSTANCE);
        Resource r = rs.getResource(URI.createFileURI(new java.io.File(args[0]).getAbsolutePath()), true);
        EcoreUtil.resolveAll(rs);
        int loadErr = 0;
        for (Resource res : rs.getResources()) for (Resource.Diagnostic e : res.getErrors()) { System.out.println("LOAD ERROR: " + e.getMessage()); loadErr++; }
        if (loadErr > 0) System.exit(2);
        List<EPackage> pkgs = new ArrayList<>();
        for (EObject root : r.getContents()) if (root instanceof EPackage p) { pkgs.add(p); registerAll(rs, p); }
        for (EPackage p : pkgs) {
            System.out.println("== EPackage " + p.getName() + " nsURI=" + p.getNsURI() + " classifiers=" + p.getEClassifiers().size() + " subpackages=" + p.getESubpackages().size());
            summarize(p, "   ");
            Diagnostic d = Diagnostician.INSTANCE.validate(p);
            dump(d, "");
            System.out.println("   -> ecore validation: " + (d.getSeverity() == Diagnostic.OK ? "OK" : d.getSeverity() == Diagnostic.WARNING ? "WARNINGS" : "ERRORS"));
        }
        for (int i = 1; i < args.length; i++) {
            Resource ir = rs.getResource(URI.createFileURI(new java.io.File(args[i]).getAbsolutePath()), true);
            EcoreUtil.resolveAll(ir);
            for (Resource.Diagnostic e : ir.getErrors()) { System.out.println("LOAD ERROR in " + args[i] + ": " + e.getMessage()); worst = Diagnostic.ERROR; }
            int n = 0; for (Iterator<EObject> it = ir.getAllContents(); it.hasNext(); it.next()) n++;
            int errs = 0;
            for (EObject root : ir.getContents()) {
                Diagnostic d = Diagnostician.INSTANCE.validate(root);
                dump(d, "   ");
                if (d.getSeverity() >= Diagnostic.ERROR) errs++;
                // unresolved proxies
                for (Iterator<EObject> it = EcoreUtil.getAllContents(root, true); it.hasNext();) {
                    EObject o = it.next();
                    for (EObject x : o.eCrossReferences()) if (x.eIsProxy()) { System.out.println("   ERROR: unresolved proxy " + ((InternalEObject) x).eProxyURI() + " from " + EcoreUtil.getURI(o)); worst = Diagnostic.ERROR; errs++; }
                }
            }
            System.out.println("== instance " + args[i] + ": " + n + " objects, " + (errs == 0 ? "valid" : "INVALID"));
        }
        System.out.println(worst >= Diagnostic.ERROR ? "RESULT: ERRORS" : worst == Diagnostic.WARNING ? "RESULT: OK (with warnings)" : "RESULT: OK");
        System.exit(worst >= Diagnostic.ERROR ? 1 : 0);
    }
    static void registerAll(ResourceSet rs, EPackage p) { rs.getPackageRegistry().put(p.getNsURI(), p); for (EPackage s : p.getESubpackages()) registerAll(rs, s); }
    static void summarize(EPackage p, String ind) {
        for (EClassifier c : p.getEClassifiers()) {
            if (c instanceof EClass k) {
                StringBuilder sb = new StringBuilder(ind + (k.isAbstract() ? "abstract " : "") + (k.isInterface() ? "interface " : "") + "class " + k.getName());
                if (!k.getESuperTypes().isEmpty()) { sb.append(" extends "); for (EClass s : k.getESuperTypes()) sb.append(s.getName()).append(' '); }
                System.out.println(sb);
                for (EStructuralFeature f : k.getEStructuralFeatures()) {
                    String kind = f instanceof EReference ref ? (ref.isContainment() ? "contains " : "ref ") : "attr ";
                    String opp = f instanceof EReference ref && ref.getEOpposite() != null ? " opposite=" + ref.getEOpposite().getName() : "";
                    String flags = (f.isDerived() ? " derived" : "") + (f.isTransient() ? " transient" : "") + (!f.isChangeable() ? " readonly" : "") + (f.isVolatile() ? " volatile" : "") + (f instanceof EAttribute a && a.isID() ? " id" : "");
                    System.out.println(ind + "   " + kind + f.getName() + " : " + (f.getEType() == null ? "<null>" : f.getEType().getName()) + " [" + f.getLowerBound() + ".." + (f.getUpperBound() == -1 ? "*" : f.getUpperBound()) + "]" + opp + flags);
                }
                for (EOperation op : k.getEOperations()) System.out.println(ind + "   op " + op.getName() + "() : " + (op.getEType() == null ? "void" : op.getEType().getName()));
            } else if (c instanceof EEnum e) {
                StringBuilder sb = new StringBuilder(ind + "enum " + e.getName() + " {");
                for (EEnumLiteral l : e.getELiterals()) sb.append(' ').append(l.getName());
                System.out.println(sb + " }");
            } else System.out.println(ind + "datatype " + c.getName() + " = " + ((EDataType) c).getInstanceTypeName());
        }
        for (EPackage s : p.getESubpackages()) { System.out.println(ind + "package " + s.getName() + " nsURI=" + s.getNsURI()); summarize(s, ind + "   "); }
    }
}
