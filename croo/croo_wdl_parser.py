import logging

from caper.wdl_parser import WDLParser

logger = logging.getLogger(__name__)


class CrooWDLParser(WDLParser):
    """WDL parser for Croo.
    """

    RE_WDL_COMMENT_CROO_OUT_DEF = r'^\s*\#\s*CROO\s+out_def\s(.+)'
    WDL_WORKFLOW_META_OUT_DEF = 'croo_out_def'

    def __init__(self, wdl):
        super().__init__(wdl)

    @property
    def croo_out_def(self):
        """Find a Docker image in WDL for Caper.

        Backward compatibililty:
            Keep using old regex method
            if WDL_WORKFLOW_META_OUT_DEF doesn't exist in workflow's meta
        """
        if self.workflow_meta:
            if CrooWDLParser.WDL_WORKFLOW_META_OUT_DEF in self.workflow_meta:
                return self.workflow_meta[CrooWDLParser.WDL_WORKFLOW_META_OUT_DEF]

        ret = self._find_val_of_matched_lines(CrooWDLParser.RE_WDL_COMMENT_CROO_OUT_DEF)
        if ret:
            return ret[0].strip('"\'')
