from lxml import etree


class RelaxNGValidator:
    module = None

    def __init__(self, module):
        self.module = module

    def validate(self, method, snippet, rnc):
        """
        Validate HTMLfilter methods with Relax NG Compact
        :param method the method to test
        :param snippet an XML! snippet that the method has to be applied to
        :param rnc a Relax NG Compact string to validate the result
        """
        if self.module:
            node = etree.fromstring(snippet)
            getattr(self.module, method)(node)
            relax_ng = etree.RelaxNG.from_rnc_string(rnc)
            return relax_ng.validate(node), etree.tostring(node, pretty_print=True)
        else:
            raise ValueError("Please set module")
