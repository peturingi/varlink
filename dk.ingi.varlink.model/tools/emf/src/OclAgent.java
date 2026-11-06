import java.lang.instrument.Instrumentation;
import java.nio.file.*;
import java.util.jar.JarFile;
/** -javaagent that puts the OCL Pivot + Xtext jars of the local Eclipse install on the system class path
 *  and registers the OCL Pivot delegate factories, so that EmfCheck really evaluates OCL annotations. */
public class OclAgent {
    public static void premain(String args, Instrumentation inst) throws Exception {
        int n = 0;
        for (String p : Files.readAllLines(Path.of(args))) {
            p = p.trim(); if (p.isEmpty() || p.startsWith("#")) continue;
            inst.appendToSystemClassLoaderSearch(new JarFile(p)); n++;
        }
        Class.forName("org.eclipse.ocl.xtext.essentialocl.EssentialOCLStandaloneSetup").getMethod("doSetup").invoke(null);
        Class<?> rs = Class.forName("org.eclipse.emf.ecore.resource.ResourceSet");
        Class.forName("org.eclipse.ocl.pivot.internal.delegate.OCLDelegateDomain").getMethod("initialize", rs).invoke(null, new Object[]{null});
        System.out.println("[ocl-agent] " + n + " jars appended; OCL Pivot delegates registered globally");
    }
}
