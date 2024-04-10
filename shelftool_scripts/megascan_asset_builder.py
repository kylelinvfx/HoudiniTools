import os
from husd import assetutils

add_to_gallery = None
add_proxy = 1

## User Inputs
# Asset save folder
save_folder = hou.ui.selectFile(title="Select the folder to save the USD assets to.", file_type=hou.fileType.Directory)
# Add to Asset Gallery
if save_folder:
    add_to_gallery = hou.ui.displayMessage("Add to Layout Asset Gallery Automatically?",
                                           buttons=("Cancel", "Yes", "No"),
                                           default_choice=2, close_choice=0,
                                           details="Make sure the following settings are set when adding to gallery"
                                                   "automatically for\nclearer thumbnail.\n"
                                                   "\t1. Create or open asset database file in Layout Asset Gallery\n"
                                                   "\t2. Select imported Megascan assets in Object Level\n"
                                                   "\t3. Display geometry with smooth shaded\n"
                                                   "\t4. Disable Object Selection Outline\n"
                                                   "\t  (Hit D in viewport -> Guides -> Selection -> Object Selection)",
                                           details_expanded=True,
                                           title="Add to Layout Asset Gallery Automatically?")
    if add_to_gallery == 1:
        add_proxy = hou.ui.displayCustomConfirmation("Create Proxy?",
                                                     buttons=("No", "Yes (longer time)"),
                                                     default_choice=0, close_choice=-1,
                                                     title="Create Proxy?")

if save_folder and add_to_gallery != 0:
    print(" ----- Creating Asset Component Builder! -----")
    asset_list = []
    counter = 1
    stage = hou.node("/stage")
    for node in hou.selectedNodes():

        # Check if the node contains variants
        childrens = len(node.children())

        # Read selected nodes
        node_path = node.path()
        node_name = node.name()

        # Get Megascan asset location on disk
        matnet = hou.node(f"{node_path}/Asset_Material").children()
        for material in matnet:
            mat_node = material
        megascan_mat_path = mat_node.parm("basecolor_texture").eval()

        # Removing the shader type name to get material base name
        mega_loc = os.path.dirname(megascan_mat_path)
        filename = os.path.basename(megascan_mat_path)
        filename = filename.split("_")
        filename.pop()
        mat_base_name = "_".join(filename)

        # Check if megascan texture is converted to RAT when imported
        ext = os.path.splitext(megascan_mat_path)[1]

        # Check if there is opacity map
        mat_opac = mat_node.parm("opaccolor_useTexture").eval()

        # Create component builder
        comp = stage.createNode("my_megascan_component_builder::1.0", node_name)
        comp_path = comp.path()
        asset_list.append(comp)

        # Set component builder inputs
        comp.parm("name").set(node_name)
        comp.parm("object_path").set(f"{node_path}")
        comp.parm("save_folder").set(save_folder)
        comp.parm("mega_loc").set(mega_loc)
        comp.parm("mat_base_name").set(f"{mat_base_name}_")
        comp.parm("add_proxy").set(add_proxy)

        # Change texture extention in componet builder is texture isnt rat
        mat_change_list = [("colormap", "Albedo"), ("roughmap", "Roughness"),
                           ("opacmap", "Opacity"), ("normalmap", "Normal_LOD0"),
                           ("dispmap", "Displacement")]
        if ext != ".rat":
            for item in mat_change_list:
                comp.parm(item[0]).set(f'`chs("mega_loc")`/`chs("mat_base_name")`{item[1]}.jpg')

        # Set Variant Parameters
        if not hou.node(f"{node_path}/Asset_Geometry"):
            variant = True
            comp.parm("variant").set(1)
            if childrens > 2:
                comp.parm("numvar").set(childrens - 1)
            else:
                numvar = (len(hou.node(f"{node_path}/lod0").children()) - 5) / 2
                comp.parm("numvar").set(numvar)
        else:
            variant = False

        # Connect opacity map if opacity map is used
        if mat_opac == 1:
            comp.allowEditingOfContents()
            comp_stand = hou.node(f"{comp_path}/materiallibrary1/mtlxsubnet/mtlxstandard_surface1")
            comp_opac = hou.node(f"{comp_path}/materiallibrary1/mtlxsubnet/Opacity")
            comp_stand.setInput(38, comp_opac, 0)

        # Adjust Component Builder if the asset variants are all in one object node
        if variant and childrens == 2:
            comp.allowEditingOfContents()
            # Get the amount of zero padding
            for nodes in hou.node(f"{node_path}/lod0").children():
                if "00_LOD0" in nodes.name():
                    temp = nodes.name().split("_")
                    temp.pop()
                    padding = len(temp[-1])
            # Componet Geometry nodes
            hou.node(f"{comp_path}/variant1").parm("name").set(f"*_`padzero({padding}, @ITERATIONVALUE)`_LOD0")
            hou.node(f"{comp_path}/variants").parm("name").set(f"*_`padzero({padding}, @ITERATIONVALUE)`_LOD0")
            # Object Merge
            new_path = '`chsop("../../../../object_path")`/lod0/`chsop("../../../name")`'
            hou.node(f"{comp_path}/variant1/sopnet/geo/object_merge1").parm("objpath1").set(new_path)
            hou.node(f"{comp_path}/variants/sopnet/geo/object_merge1").parm("objpath1").set(new_path)
            # For each iteration number
            hou.node(f"{comp_path}/foreach_end1").parm("firstiteration").set(0)
            hou.node(f"{comp_path}/foreach_end1").parm("iterations").deleteAllKeyframes()
            hou.node(f"{comp_path}/foreach_end1").parm("iterations").setExpression('ch("../numvar")')
            hou.node(f"{comp_path}/foreach_end1").parm("lastiteration").deleteAllKeyframes()
            hou.node(f"{comp_path}/foreach_end1").parm("lastiteration").setExpression('ch("../numvar")')

        # Save and Add to Layout Asset Gallery if Specified
        if add_to_gallery == 1:
            # Generate Thumbnail
            # Turn off all object level display flags and only turn on the one that is running
            obj = hou.node("/obj")
            for nodes in obj.children():
                nodes.setDisplayFlag(0)
            node.setDisplayFlag(1)
            # Set SOP level Display Flag
            # No variant
            if not variant:
                asset_geo = hou.node(f"{node.path()}/Asset_Geometry")
                asset_geo.setDisplayFlag(1)
                sop_geo = hou.node(f"{node_path}/Asset_Geometry/{node_name}_lod0")
            # With vairants
            elif childrens > 2:
                # Create a bbox geo to merge in all varaint to calculate correct bbox size
                # DEBUG - delete bbox geo if it already exits to prevent errors when running mutiple times
                if hou.node(f"{node_path}/bbox") in node.children():
                    hou.node(f"{node_path}/bbox").destroy()
                    childrens -= 1
                bbox_geo = node.createNode("geo", "bbox")
                node.layoutChildren(items=node.children())
                var_merge = bbox_geo.createNode("merge")
                var_out = bbox_geo.createNode("null", f"OUT_{node_name}_BBOX")
                var_out.setInput(0, var_merge, 0)
                var_out.setDisplayFlag(1)
                var_out.setRenderFlag(1)
                # For each variant, create object merge in the bbox geo and merge with others
                for i in range(1, childrens):
                    var_geo = hou.node(f"{node.path()}/Var{i}_LOD0")
                    var_geo.setDisplayFlag(0)
                    var_om = bbox_geo.createNode("object_merge", f"Var{i}_LOD0")
                    var_om.parm("objpath1").set(f"{node.path()}/Var{i}_LOD0/{node_name}_Var{i}_LOD0")
                    var_merge.setNextInput(var_om, 0)
                    bbox_geo.layoutChildren(items=bbox_geo.children())
                sop_geo = var_out
            else:
                for nodes in hou.node(f"{node_path}/lod0").children():
                    if "00_LOD0" in nodes.name():
                        nodes.setDisplayFlag(1)
                        nodes.setRenderFlag(1)
                        sop_geo = nodes
            # Turn off displacement for thumbnails
            mat_node.parm("dispTex_enable").set(0)
            # Set base color map to jpg for better viewport thumbnail,
            # also refresh material loading when opening old file
            old_color = mat_node.parm("basecolor_texture").eval()
            new_color = ".".join([old_color.split(".")[0], "jpg"])
            mat_node.parm("basecolor_texture").set(new_color)
            ## Focus the camera to the object
            # Create Bounding Box of the Geometry from Geometry in Object Level
            geo = sop_geo.geometry()
            bbox = geo.boundingBox()
            # Frame the obejct by the Bounding Box
            sceneViewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
            viewport = sceneViewer.curViewport()
            viewport.frameBoundingBox(bbox)
            # Generate and save the Thumbnail
            res = (256, 256)
            output = f"$HIP/asset/{node_name}/thumbnail.png"
            assetutils.saveThumbnailFromViewer(output=output, res=res)
            # Turn Displacement back on
            mat_node.parm("dispTex_enable").set(1)
            # Change base color texture back
            mat_node.parm("basecolor_texture").set(old_color)

            # Save USD File and Load from Disk
            comp.parm("execute").pressButton()
            comp.parm("loadfromdisk").set(1)
            # Add to Gallery
            comp.parm("addtogallery").pressButton()

        print(f"{counter}. {node_name} - Created")
        counter += 1

    # Layout Asset Componet Builders Created
    stage.layoutChildren(items=asset_list)
    print(" ----- All Asset Component Builder Created! -----")
