import os
import re

import hou

from ayon_houdini.api import pipeline, plugin


class RigLoader(plugin.HoudiniLoader):
    """Load rig (APEX bgeo) files to Houdini."""

    label = "Load Rig"
    product_types = {"rig"}
    representations = {
        "bgeo",
        "bgeosc",
        "bgeogz",
        "bgeo.sc",
        "bgeo.gz",
        "bgeo.lzma",
        "bgeo.bz2",
    }
    order = -10
    icon = "male"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):
        obj = hou.node("/obj")
        if obj is None:
            raise RuntimeError("Could not find /obj node in Houdini session")

        namespace = namespace if namespace else context["folder"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        container = obj.createNode("geo", node_name=node_name)

        file_node = container.node("file1")
        if file_node:
            file_node.destroy()

        path = self.filepath_from_context(context)
        file_node = container.createNode("file", node_name=node_name)
        file_node.setParms(
            {"file": self.format_path(path, context["representation"])}
        )

        file_node.setDisplayFlag(True)

        nodes = [container, file_node]
        self[:] = nodes

        return pipeline.containerise(
            node_name,
            namespace,
            nodes,
            context,
            self.__class__.__name__,
            suffix="",
        )

    @staticmethod
    def format_path(path, representation):
        """Format file path for single bgeo or bgeo sequence."""
        is_sequence = bool(representation["context"].get("frame"))
        if is_sequence:
            folder, filename = os.path.split(path)
            filename = re.sub(
                r"(.*)\.(\d+)\.(bgeo.*)", "\\1.$F4.\\3", filename
            )
            path = os.path.join(folder, filename)

        return os.path.normpath(path).replace("\\", "/")

    def update(self, container, context):
        repre_entity = context["representation"]
        node = container["node"]
        try:
            file_node = next(
                n for n in node.children() if n.type().name() == "file"
            )
        except StopIteration:
            self.log.error("Could not find node of type `file`")
            return

        file_path = self.filepath_from_context(context)
        file_node.setParms({"file": self.format_path(file_path, repre_entity)})

        node.setParms({"representation": repre_entity["id"]})

    def remove(self, container):
        container["node"].destroy()

    def switch(self, container, context):
        self.update(container, context)
