# Getting Started

Welcome to tono, a node-based SPM image analysis tool. This guide covers the basics of building and running workflows.

## The Canvas

The main area is an infinite canvas where you build workflows by placing and connecting nodes. You can pan by holding middle click and dragging (two-finger drag on a trackpad), and zoom by holding right click and dragging (pinching on a trackpad). You can make a box selection by left clicking and dragging.

### Adding Nodes

Right-click anywhere on the canvas to open the **Add Node** menu. Nodes are organized into categories — hover a category to see the available nodes, then click one to place it. The same nodes can be found in different categories, if they share similar features.

You can also search for nodes by name using the search bar at the top of the **Add Node** menu.

When you drag a connection from an output socket and drop it on empty space, tono will automatically show a filtered menu with only compatible nodes for that output type.

### Connecting Nodes

Click and drag from an output socket (right side of a node) to an input socket (left side of another node). Connections carry data between nodes — images, numbers, text, and other types.

Handles are color-coded by type. You can only connect compatible types — tono will snap to valid sockets as you drag.

You can select a connection and press Delete to delete the node.

You are not allowed to create cyclic node graphs.

### Creating Groups

Drag a box over a set of nodes to select them, then right click and **Create Group**. 
Groups can be collapsed to only show their inputs and outputs, making their internal structure easier to ignore. You can freely drag nodes in and out of unfolded groups.
Groups can be renamed to make it easier to remember what you put in them. Groups can be copy/pasted like normal groups, as well as cloned.

### Running a Workflow

Nodes will process in order from inputs to outputs, with each node showing a glow when processing, and a timestamp of how long it took to run when it finishes.

The node graph will automatically run whenever something has been added or changed. It will only run nodes which have been changed or added, so nodes at the end of the graph do not cause the entire tree to re-run.

You can manually run the workflow using the **Run** button in the toolbar (or press **Ctrl+Enter** / **Cmd+Enter**) to execute the workflow. 

### Uploading Images

To load an image, add an **Image** node (found in the **Input** category). Click the **Browse** button on the node to select a file from your computer.

You can also type or paste a file path directly into the text field.

## Finding Help

Every node has a **?** button in its title bar. Click it to open the documentation for that node in the help panel. The help panel supports multiple tabs, so you can have several docs open at once.

The help panel also appears at the bottom of the screen when docs are available. You can collapse it with the arrow button or close individual tabs.

## The Journal

Click the **+** button in the help panel tab bar to open the Journal — a built-in scratchpad for notes. It supports Markdown formatting. Double-click the preview to edit, and press **Esc** or **Ctrl+Enter** to switch back to preview mode. Journal content is saved with your workflow.

## Saving and Loading Workflows

tono has a clever trick where it stores the workflow structure as metadata in an image file, so you can view the workflows easily, and when you find the one you like, you can just drag it into the window to load fully interactive version of it.

### Save

Click **Save** in the toolbar to save your workflow as a PNG image. The workflow graph is embedded in the image metadata, so the PNG serves as both a visual snapshot and a loadable workflow file. It only contains the tree of nodes, along with journal content.

### Pack

Click **Pack** to save a packed workflow. This bundles all loaded images into the workflow file itself, so the workflow is fully self-contained and can be shared with others without needing to send the source files separately. It also includes the journal content.

### Load

Click **Load** to open a saved workflow. You can load both regular workflow PNGs and packed workflows. Packed workflows will automatically restore their bundled files and run once so previews populate.

### Snapshot

Click **Snapshot** to copy a screenshot of the current canvas to your clipboard. This includes the workflow graph and the journal contents.

Keep in mind when sharing this file that some messaging services will strip the metadata from the image, which will break workflow loading.

## Keyboard Shortcuts

### Cloning

Select nodes and hold **Ctrl** while dragging to clone the nodes. This will preserve all of it's controls and upstream connections.

### Copy and Paste

Select nodes and press **Ctrl+C** / **Cmd+C** to copy them, then **Ctrl+V** / **Cmd+V** to paste. Manual controls between copied nodes are preserved.

### Undo and Redo

Use **Ctrl+Z** / **Cmd+Z** to undo and **Ctrl+Shift+Z** / **Cmd+Shift+Z** to redo changes to the graph.

### Shortcut Reference

| Shortcut | Action |
|---|---|
| Ctrl+Enter | Run workflow |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Ctrl+C | Copy selected nodes |
| Ctrl+V | Paste nodes |
| Right-click canvas | Add node menu |
| Escape | Close help panel |
