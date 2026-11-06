import java.io.File;
import java.util.Collections;
import org.eclipse.emf.codegen.ecore.genmodel.*;
import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EcorePackage;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.xmi.impl.EcoreResourceFactoryImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;

/** Usage: GenModelBuilder <model.ecore> <model.genmodel> <modelPluginID> <basePackage> <modelName> <jdkLevel>
 *  Builds a GenModel from the Ecore with the genuine EMF codegen API (GenModel.initialize), then applies
 *  Pétur's project settings. Deterministic replacement for the Eclipse "EMF Generator Model" wizard. */
public class GenModelBuilder {
    public static void main(String[] args) throws Exception {
        File ecoreFile = new File(args[0]).getAbsoluteFile(), genFile = new File(args[1]).getAbsoluteFile();
        String pluginId = args[2], basePackage = args[3], modelName = args[4], jdk = args[5];
        GenModelPackage.eINSTANCE.eClass();
        ResourceSet rs = new ResourceSetImpl();
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("ecore", new EcoreResourceFactoryImpl());
        rs.getResourceFactoryRegistry().getExtensionToFactoryMap().put("genmodel", new XMIResourceFactoryImpl());
        rs.getPackageRegistry().put(EcorePackage.eNS_URI, EcorePackage.eINSTANCE);
        Resource ecoreRes = rs.getResource(URI.createFileURI(ecoreFile.getPath()), true);
        EPackage root = (EPackage) ecoreRes.getContents().get(0);
        Resource genRes = rs.createResource(URI.createFileURI(genFile.getPath()));
        GenModel gm = GenModelFactory.eINSTANCE.createGenModel();
        genRes.getContents().add(gm);
        gm.initialize(Collections.singleton(root));
        gm.setModelDirectory("/" + pluginId + "/src-gen");
        gm.setEditDirectory("/" + pluginId + ".edit/src-gen");
        gm.setEditorDirectory("/" + pluginId + ".editor/src-gen");
        gm.setModelPluginID(pluginId);
        gm.setModelName(modelName);
        gm.setRootExtendsClass("org.eclipse.emf.ecore.impl.MinimalEObjectImpl$Container");
        gm.setCreationIcons(false);
        gm.setCodeFormatting(true);
        gm.setImporterID("org.eclipse.emf.importer.ecore");
        gm.setCopyrightFields(false);
        gm.setOperationReflection(true);     // needed so OCL-bodied EOperations can be invoked reflectively
        gm.setImportOrganizing(true);
        gm.setFeatureDelegation(GenDelegationKind.DYNAMIC_LITERAL); // derived features go through the OCL setting delegate
        // OCL GenModel option "Use Delegates = true": do NOT compile OCL bodies into Java (the compiled form folds null
        // guards away and reports constraint violations as warnings); evaluate them through the Pivot delegates instead.
        GenAnnotation ocl = GenModelFactory.eINSTANCE.createGenAnnotation();
        ocl.setSource("http://www.eclipse.org/OCL/GenModel");
        ocl.getDetails().put("Use Delegates", "true");
        gm.getGenAnnotations().add(ocl);
        GenJDKLevel level = GenJDKLevel.get(jdk);
        if (level == null) { level = GenJDKLevel.VALUES.get(GenJDKLevel.VALUES.size() - 1); System.out.println("JDK level " + jdk + " unknown to this EMF, using " + level.getLiteral()); }
        gm.setComplianceLevel(level);
        gm.getForeignModel().add(ecoreFile.getName());
        for (GenPackage gp : gm.getGenPackages()) { gp.setBasePackage(basePackage); gp.setDisposableProviderFactory(true); gp.setPrefix(modelName); }
        genRes.save(null);
        System.out.println("wrote " + genFile + " (" + gm.getGenPackages().size() + " root genPackages, compliance " + gm.getComplianceLevel().getLiteral() + ", delegation " + gm.getFeatureDelegation() + ")");
        System.out.println("diagnostics: " + gm.diagnose().getSeverity());
    }
}
