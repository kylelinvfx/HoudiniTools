# Discord Houdini Tracker Quick Setup
# This Python script is a shelftool for Discord Houdini Tracker quick setup
# By: Kyle Lin      (https://kylelinvfx.com)
# Created: 11 March 2024
# Modified: 13 March 2024


# Get the discord bot setting
bot_setting = hou.ui.displayCustomConfirmation("Is Discord Bot Token and User ID set in Environment Variable?",
                                               buttons=("Yes", "No, Enter manually", "Cancel"),
                                               default_choice=0, close_choice=2, title="Discord Tracker Quick Setup")

# Create a setup attribute for checking if continuing setup later
setup = True
if bot_setting == 2:    # User Canceled
    setup = False

# Ask for Discord Bot Setting if user needs to enter manually.
bot_token = ""
user_id = ""
if bot_setting == 1:
    bot_info = hou.ui.readMultiInput("Enter Discord Bot settings:", input_labels=("Bot Token", "User ID"),
                                     buttons=("OK", "Cancel"), default_choice=0, close_choice=1)
    if bot_info[0] == 0:
        bot_token = bot_info[1][0]
        user_id = bot_info[1][1]
        node = hou.selectedNodes()[0]
    else:   # User Canceled
        setup = False

if setup:
    # Get the topnet node and path
    top_path = hou.selectedNodes()[0].path().split("/")
    top_path.pop()
    top_path = "/".join(top_path)
    top = hou.node(top_path)

    # ADD BEGIN NODE
    # Check if there is a Discord Tracker Begin Node
    # Add to the list of nodes to connect if there isn't a Begin node
    found_begin = False
    nodes_to_connect = []
    begin = None
    begin_name = ""
    for node in hou.selectedNodes():
        # Check if the selected node is the begin node
        if "KyleLin::discord_tracker_begin" in node.type().name():
            found_begin = True
        input_nodes = node.inputAncestors()
        if len(input_nodes) == 0:
            nodes_to_connect.append(node)
        else:
            for input_node in input_nodes:
                if "KyleLin::discord_tracker_begin" in input_node.type().name():
                    found_begin = True
                    begin_name = input_node.name()
                else:
                    if len(input_node.inputs()) == 0:
                        nodes_to_connect.append(input_node)
    if not found_begin:
        # Create Discord Tracker Begin Node and connect to the nodes without input
        begin = top.createNode("KyleLin::discord_tracker_begin::1.0")
        begin_name = begin.name()
        for node in nodes_to_connect:
            node.setInput(0, begin)
        # Create a Sort list of the begin node and the first node without input for layout
        begin_sort_list = [begin, nodes_to_connect[0]]
        top.layoutChildren(items=begin_sort_list)
        # Set up Discord setting if chose to enter manually
        if bot_setting == 1:
            begin.parm("token_type").set(1)
            begin.parm("token").set(bot_token)
            begin.parm("id_type").set(1)
            begin.parm("id").set(user_id)

    # ADD TRACKER NODE
    for node in hou.selectedNodes():
        # Check if the selected node is any of the discord tracker node
        # because there's no need to add a tracker to track those nodes
        found_tracker = False
        out_nodes = node.outputs()
        if "KyleLin::discord_tracker" in node.type().name():
            found_tracker = True
        else:
            # Check if selected node already has a tracker connected
            for out in out_nodes:
                if "KyleLin::discord_tracker" in out.type().name():
                    found_tracker = True
        # Create Tracker Node to Selected Node if there's no tracker connected
        if not found_tracker:
            tracker = top.createNode("KyleLin::discord_tracker::1.0")
            # Connect Tracker to the Selected Node
            tracker.setInput(0, node)
            # Connect Tracker to Original Output Nodes
            for out_node in out_nodes:
                # Find the index of Original Output Node
                in_list = out_node.inputs()
                index = 0
                for i in range(len(in_list)):
                    if in_list[i] == node:
                        index = i
                out_node.setInput(index, tracker)
            tracker.moveToGoodPosition()
            # Set up Discord setting if chose to enter manually
            if bot_setting == 1 and not found_begin:
                tracker.parm("token_type").set(begin.parm("token_type"))
                tracker.parm("token").set(begin.parm("token"))
                tracker.parm("id_type").set(begin.parm("id_type"))
                tracker.parm("id").set(begin.parm("id"))
            # Check if the created tracker node is the end of the node.
            if node.isDisplayFlagSet():
                tracker.setDisplayFlag(1)

    # ADD END NODE
    # Get the node with display flag to use it to find if there is an end node above it
    children = top.children()
    display_node = None
    found_end = False
    for node in children:
        if node.isDisplayFlagSet():
            display_node = node
    # Check the node with display flag itself
    if "KyleLin::discord_tracker_end" in display_node.type().name():
        found_end = True
    # Check all the node above the node with display node
    node_list = display_node.inputAncestors()
    for node in node_list:
        if "KyleLin::discord_tracker_end" in node.type().name():
            found_end = True
    # Create an End node if there isn't one
    if not found_end:
        end = top.createNode("KyleLin::discord_tracker_end::1.0")
        # Connect it after the node with the display flag and flag the end node
        end.setInput(0, display_node)
        end.moveToGoodPosition()
        end.setDisplayFlag(1)
        # Set up Discord setting if chose to enter manually
        if bot_setting == 1 and not found_begin:
            end.parm("token_type").set(begin.parm("token_type"))
            end.parm("token").set(begin.parm("token"))
            end.parm("id_type").set(begin.parm("id_type"))
            end.parm("id").set(begin.parm("id"))
