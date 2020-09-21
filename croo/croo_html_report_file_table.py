#!/usr/bin/env python3
"""CrooHtmlReportFileTable

    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

import os
import textwrap

from autouri import AutoURI


class CrooHtmlReportFileTable(object):
    HEAD = textwrap.dedent(
        """
        <link href="https://cdnjs.cloudflare.com/ajax/libs/jquery-treetable/3.2.0/css/jquery.treetable.min.css" rel="stylesheet" type="text/css" />
        <link href="https://cdnjs.cloudflare.com/ajax/libs/jquery-treetable/3.2.0/css/jquery.treetable.theme.default.min.css" rel="stylesheet" />
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-treetable/3.2.0/jquery.treetable.min.js"></script>
        <script type="text/javascript">
          $(function(){
            $("#filetable").treetable({
              expandable: true,
              onNodeCollapse: function() {},
              onNodeExpand: function() {}
            });
          });
        </script>
    """
    )
    BODY = textwrap.dedent(
        """
        <div id='file-table'><b>File table</b>
        <table id='filetable'>
          <caption>
            <a href='#' onclick="jQuery('#filetable').treetable('expandAll');return false;">
              Expand all</a> &nbsp&nbsp
            <a href='#' onclick="jQuery('#filetable').treetable('collapseAll');return false;">
              Collapse all</a>
          </caption>
        <thead><tr><th>Files</th><th>Path</th></tr></thead>
          {table_contents}
        <tbody>
        </tbody>
        </table>
        </div>
    """
    )
    FILETABLE_TSV = 'croo.filetable.{workflow_id}.tsv'

    def __init__(self, out_dir, workflow_id):
        self._items = []
        self._out_dir = out_dir
        self._workflow_id = workflow_id

    def add(self, full_path, url, table_item):
        self._items.append((full_path, url, table_item))

    def get_html_head_str(self):
        return CrooHtmlReportFileTable.HEAD

    def get_html_body_str(self):
        html = CrooHtmlReportFileTable.BODY.format(
            table_contents=self.__make_table_contents()
        )
        return html

    def __make_table_contents(self):
        """
        Each item has (full_path, url, table_item)
        table_item defines a hierarchy in a tree
        e.g. a/b/c with full_path=/scratch/hello.world
            and url=http://scratch.com/hello.world
        Tree    Path
        a
        +-b
          +-c   /scratch/hello.world (url as href)
        """
        # parse table_item string
        all_items = []
        data_tt_id_cache = set()
        for full_path, url, table_item in self._items:
            dir_items = table_item.split('/')
            # print(dir_items)
            for i, label in enumerate(dir_items):
                data_tt_id = '/'.join(dir_items[: i + 1]).replace(' ', '-')

                if data_tt_id in data_tt_id_cache and i < len(dir_items) - 1:
                    continue
                else:
                    data_tt_id_cache.add(data_tt_id)

                if i == 0:
                    data_tt_parent_id = None
                else:
                    data_tt_parent_id = '/'.join(dir_items[:i]).replace(' ', '-')

                if i == len(dir_items) - 1:
                    if url is None:
                        path = full_path
                    else:
                        path = '<a href="{url}" target="_blank">{full_path}</a>'.format(
                            url=url, full_path=full_path
                        )
                else:
                    path = ''

                all_items.append((data_tt_id, data_tt_parent_id, label, path))

        # sort by data_tt_id but dir always comes first
        def dir_first(s):
            arr = s[0].split('/')
            if s[3] != '':  # if dir
                arr[-1] = '_' + arr[-1]
            return '/'.join(arr)

        sorted_all_items = sorted(all_items, key=lambda x: dir_first(x))

        table_contents = ''
        for data_tt_id, data_tt_parent_id, label, path in sorted_all_items:
            table_contents += "<tr data-tt-id='{}'".format(data_tt_id)

            if data_tt_parent_id is None:
                table_contents += ">"
            else:
                table_contents += "data-tt-parent-id='{}'>".format(data_tt_parent_id)

            table_contents += "<td>{label}</td><td>{path}</td></tr>\n".format(
                label=label, path=path
            )

        # save to TSV file
        contents = ''
        for full_path, url, table_item in self._items:
            contents += '{}\t{}\t{}\n'.format(table_item, full_path, url)
        uri_filetable = os.path.join(
            self._out_dir,
            CrooHtmlReportFileTable.FILETABLE_TSV.format(workflow_id=self._workflow_id),
        )
        AutoURI(uri_filetable).write(contents)
        return table_contents
