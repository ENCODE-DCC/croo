#!/usr/bin/env python3
"""CrooHtmlReportFileTable

    Jin Lee (leepc12@gmail.com) at ENCODE-DCC
"""

from caper.caper_uri import CaperURI, URI_LOCAL, URI_URL


class CrooHtmlReportFileTable(object):
    HEAD = """
    <link href="https://cdnjs.cloudflare.com/ajax/libs/jquery-treetable/\
3.2.0/css/jquery.treetable.min.css" rel="stylesheet" type="text/css" />
    <link href="https://cdnjs.cloudflare.com/ajax/libs/jquery-treetable/\
3.2.0/css/jquery.treetable.theme.default.min.css" rel="stylesheet" />
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-treetable/\
3.2.0/jquery.treetable.min.js"></script>
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
    BODY = """
    <div id='file-table'><b>File table</b>
    <table id='filetable'>
      <caption>
        <a href='#' onclick="jQuery('#filetable').treetable('expandAll');\
return false;">
          Expand all</a> &nbsp&nbsp
        <a href='#' onclick="jQuery('#filetable').treetable('collapseAll');\
return false;">
          Collapse all</a>
      </caption>
    <thead><tr><th>Files</th><th>Path</th></tr></thead>
      {table_contents}
    <tbody>
    </tbody>
    </table>
    </div>
    """

    def __init__(self, html_root, use_rel_path_in_link=False):
        self._items = []
        self._html_root = html_root
        self._use_rel_path_in_link = use_rel_path_in_link

    def add(self, full_path, table_item):
        self._items.append((full_path, table_item))

    def get_html_head_str(self):
        return CrooHtmlReportFileTable.HEAD

    def get_html_body_str(self):
        html = CrooHtmlReportFileTable.BODY.format(
            table_contents=self.__make_table_contents())
        return html

    def __make_table_contents(self):
        """
        Each item has (full_path, table_item)
        table_item defines a hierarchy in a tree
        e.g. a/b/c with full_path=/scratch/hello.world
        Tree    Path
        a
        +-b
          +-c   /scratch/hello.world
        """
        all_items = []
        data_tt_id_cache = set()
        for full_path, table_item in self._items:
            dir_items = table_item.split('/')
            # print(dir_items)
            for i, label in enumerate(dir_items):
                data_tt_id = '/'.join(dir_items[:i+1]).replace(' ', '-')

                if data_tt_id in data_tt_id_cache and i < len(dir_items) - 1:
                    continue
                else:
                    data_tt_id_cache.add(data_tt_id)

                if i == 0:
                    data_tt_parent_id = None
                else:
                    data_tt_parent_id = '/'.join(dir_items[:i]).replace(' ', '-')

                if i == len(dir_items) - 1:
                    path = self.get_html_link(full_path)
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
                table_contents += "data-tt-parent-id='{}'>".format(
                    data_tt_parent_id)

            table_contents += "<td>{label}</td><td>{path}</td></tr>\n".format(
                label=label, path=path)

        return table_contents

    def get_html_link(self, full_path):
        if self._use_rel_path_in_link:
            rel_path = full_path.replace(self._html_root, '', 1)
            return '<a href="{rel_path}">{full_path}</a>'.format(
                rel_path=rel_path,
                full_path=full_path)
        else:
            cu = CaperURI(full_path)
            if cu.uri_type != URI_LOCAL:
                return '<a href="{url}">{full_path}</a>'.format(
                    url=cu.get_file(uri_type=URI_URL),
                    full_path=full_path)
            else:
                return full_path
