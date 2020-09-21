import logging
import os

from autouri import AutoURI
from graphviz import Source
from graphviz.backend import ExecutableNotFound

logger = logging.getLogger(__name__)


class CrooHtmlReportTaskGraph(object):
    TASK_GRAPH_DOT = 'croo.task_graph.{workflow_id}.dot'
    TASK_GRAPH_SVG = 'croo.task_graph.{workflow_id}.svg'

    def __init__(self, out_dir, workflow_id, dag, template_d):
        """
        Args:
            out_dir:
                directory for SVG (remote or local)
            dag:
                Task graph (DAG)
            template_d:
                A template dict that will be converted to a template dot file for graphviz
                This dot file will be converted into SVG and finally be embedded in HTML
                Refer to the function caper.dict_tool.dict_to_dot_str() for details
                https://github.com/ENCODE-DCC/caper/blob/master/caper/dict_tool.py#L190
        """
        self._out_dir = out_dir
        self._workflow_id = workflow_id
        self._dag = dag
        self._template_d = template_d
        self._items = {}

    def add(self, output_name, task_name, shard_idx, url, node_format, subgraph):
        # node as task's output
        self._items[('output', output_name, task_name, shard_idx)] = (
            node_format,
            url,
            subgraph,
        )
        # node as task itself
        task_name_on_graph = task_name.split('.')[-1] if task_name else task_name
        self._items[('task', None, task_name, shard_idx)] = (
            '[label=\"{}\"]'.format(task_name_on_graph),
            task_name,
            subgraph,
        )

    def get_html_body_str(self):
        """Embed SVG into HTML
        """
        svg_contents = self.__make_svg()
        if svg_contents is None:
            return ''
        else:
            head = '<b>Task graph</b><div id=\'task-graph\'>\n'
            img = svg_contents
            tail = '</div><br>'
            return head + img + tail

    def __make_svg(self):
        """Converts a dict into a dot string and then to a SVG file
        Returns:
            An SVG string, but also saves to CrooHtmlReportTaskGraph.TASK_GRAPH_SVG
        """
        if not self._items:
            return None

        # define call back functions for node format, href, subgraph
        def fnc_node_format(n):
            if (n.type, n.output_name, n.task_name, n.shard_idx) in self._items:
                return self._items[(n.type, n.output_name, n.task_name, n.shard_idx)][0]
            else:
                return None

        def fnc_href(n):
            if (n.type, n.output_name, n.task_name, n.shard_idx) in self._items:
                return self._items[(n.type, n.output_name, n.task_name, n.shard_idx)][1]
            else:
                return None

        def fnc_subgraph(n):
            if (n.type, n.output_name, n.task_name, n.shard_idx) in self._items:
                return self._items[(n.type, n.output_name, n.task_name, n.shard_idx)][2]
            else:
                return None

        # convert to dot string
        dot_str = self._dag.to_dot(
            fnc_node_format=fnc_node_format,
            fnc_href=fnc_href,
            fnc_subgraph=fnc_subgraph,
            template=self._template_d,
        )
        # temporary dot, svg from graphviz.Source.render
        tmp_dot = '_tmp_.dot'

        try:
            svg = Source(dot_str, format='svg').render(filename=tmp_dot)
        except (ExecutableNotFound, FileNotFoundError):
            logger.info(
                'Importing graphviz failed. Task graph will not be available. '
                'Check if you have installed graphviz correctly so that '
                '"dot" executable exists on your PATH. '
                '"pip install graphviz" does not install such "dot". '
                'Use apt or system-level installer instead. '
                'e.g. sudo apt-get install graphviz.'
            )
            return None

        # save to DOT
        uri_dot = os.path.join(
            self._out_dir,
            CrooHtmlReportTaskGraph.TASK_GRAPH_DOT.format(
                workflow_id=self._workflow_id
            ),
        )
        AutoURI(uri_dot).write(dot_str)

        # save to SVG
        with open(svg, 'r') as fp:
            svg_contents = fp.read()
        uri_svg = os.path.join(
            self._out_dir,
            CrooHtmlReportTaskGraph.TASK_GRAPH_SVG.format(
                workflow_id=self._workflow_id
            ),
        )
        AutoURI(uri_svg).write(svg_contents)

        os.remove(tmp_dot)
        os.remove(svg)

        return svg_contents
