#!/usr/bin/env python
# ~ -*- coding:utf-8 -*-
import os

from lxml import etree
from mock import MagicMock

from mwlib.pdf import utils
from mwlib.pdf.collection import Article
from mwlib.pdf.htmlfilters import images
from mwlib.pdf.htmlfilters.test.utils import RelaxNGValidator

rng = RelaxNGValidator(images)
file_directory = os.path.dirname(os.path.realpath(__file__))


def test_fix_image_src():
    local_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), "extra")

    def mock_return(img_name):
        return os.path.join(local_directory, img_name)

    env = MagicMock()
    env.images.getDiskPath = mock_return
    article = Article(env=env)

    # good case - local gif file exists
    img_name = "giphy.gif"
    tree = etree.fromstring('<div><img src="https://pediapress.com/{}" /></div>'.format(img_name))
    article.dom = tree
    images.fix_image_src(article)
    assert os.path.join(local_directory, img_name) == article.dom[0].get("src")

    # bad case - local gif file doesn't exist
    img_name = "non-existent.gif"
    tree = etree.fromstring('<div><img src="https://pediapress.co/{}" /></div>'.format(img_name))
    article.dom = tree
    images.fix_image_src(article)
    assert "" == article.dom[0].get("src")

    # good case jpg
    img_name = "Bayon_Angkor_Relief1.jpg"
    img_src = "//upload.wikimedia.org/wikipedia/commons/thumb/5/5b/{img_name}/143px-{img_name}"
    img_src = img_src.format(img_name=img_name)
    tree = etree.fromstring('<div><img src="{}" /></div>'.format(img_src))
    article.dom = tree
    images.fix_image_src(article)
    assert os.path.join(local_directory, img_name) == article.dom[0].get("src")


def test_set_size_attributes():
    tree = etree.fromstring(
        '<div><img src="https://pediapress.com/{}" style="width: 100px; height: 50px;"/></div>'
    )
    images.set_size_attributes(tree)

    assert "100" == tree[0].get("width")
    assert "50" == tree[0].get("height")


def test_fix_galleries():
    with open(os.path.join(file_directory, "extra", "test_fix_galleries.html")) as fn:
        snippet = fn.read()
    rnc = """
start = element div {
    element ul {
        attribute style { empty }?,
        attribute class { text }?,
        element li {
            attribute style { empty }?,
            attribute class { "gallerybox col-4" },
            element div {
                attribute style { empty }?,
                element div {
                    attribute style { empty }?,
                    attribute class { "thumb" },
                    element div {
                        attribute style { text }?,
                        element a {
                            attribute href { text },
                            attribute class { "image" },
                            element img {
                                attribute alt { text },
                                attribute class { "thumbimage" },
                                attribute src { text },
                                attribute srcset { text },
                                attribute data-file-width { xsd:int },
                                attribute data-file-height {xsd:int }
                            }
                        }
                    }
                },
                element div {
                    attribute class { "gallerytext" },
                    element p { any_content }
                }
            }*
        }*
    }
}
any_content = any_element* & text
any_element = element * { any_attribute*, any_content}
any_attribute = attribute * { text }
    """
    result, transformed_snippet = rng.validate("fix_galleries", snippet, rnc)
    print(transformed_snippet)
    assert result


def test_remove_images():
    with open(os.path.join(file_directory, "extra", "test_remove_images.html")) as fn:
        root = etree.HTML(fn.read())
        for n in range(6):
            assert len(root.xpath('//*[@id="to_be_removed_{}"]'.format(n))) == 1
        for n in range(4, 6):
            assert len(root.xpath('//*[@id="not_to_be_removed_{}"]'.format(n))) == 1
        images.remove_images_with_class_remove(root)
        for n in range(6):
            assert len(root.xpath('//*[@id="to_be_removed_{}"]'.format(n))) == 0
        for n in range(4, 6):
            assert len(root.xpath('//*[@id="not_to_be_removed_{}"]'.format(n))) == 1


def test_remove_img_style_size():
    with open(os.path.join(file_directory, "extra", "test_remove_img_style_size.html")) as fn:
        root = etree.HTML(fn.read())
        has_thumbinner_width = []
        for n in range(3):
            xpath = '//*[@id="container_{}"]'.format(n)
            node = root.xpath(xpath)[0]
            assert "col-" not in node.attrib["class"]
            thumbinner = node.xpath('.//*[@class="thumbinner"]')[0]
            has_thumbinner_width.append(False)
            if utils.get_node_style(thumbinner).get("width") is not None:
                has_thumbinner_width[n] = True
        images.remove_img_style_size(root)
        for n in range(3):
            node = root.xpath('//*[@id="container_{}"]'.format(n))[0]
            if has_thumbinner_width[n]:
                thumbinner = node.xpath('.//*[@class="thumbinner"]')[0]
                assert utils.get_node_style(thumbinner).get("width") is None
            img = node.xpath(".//img")[0]
            assert utils.get_node_style(img).get("width") is None
            assert node.attrib.get("width") is None
            assert img.attrib.get("width") is None
            assert "col-" in node.attrib["class"]


def test_fix_image_widths_tmulti():
    with open(os.path.join(file_directory, "extra", "test_remove_img_style_size.html")) as fn:
        root = etree.HTML(fn.read())
        img_container = root.xpath('//*[@id="container_3"]')[0]
        thumbinner = img_container.xpath('.//*[contains(@class, "thumbinner")]')[0]
        assert utils.get_node_style(thumbinner).get("max-width") is not None
        images.fix_img_style_size_tmulti(root)
        assert utils.get_node_style(thumbinner).get("max-width") is None


def test_fix_links_on_images():
    with open(os.path.join(file_directory, "extra", "test_fix_links_on_images.html")) as fn:
        root = etree.HTML(fn.read())
        node = root.xpath("//a")[0]
        href = node.attrib.get("href")
        images.fix_links_on_images(root)
        node = root.xpath("//a")[0]
        assert "href" not in node.attrib
        assert "wiki_href" in node.attrib
        assert node.attrib["wiki_href"] == href


def test_resize_tabled_images():
    with open(os.path.join(file_directory, "extra", "test_image_table.html")) as fn:
        root = etree.HTML(fn.read())
        images.fix_image_tables(root)
        # assert False


def test_tag_infobox_images():
    with open(os.path.join(file_directory, "extra", "test_infobox.html")) as fn:
        root = etree.HTML(fn.read())
        images.add_class_to_infobox_wide_images(root)
        for node in root.xpath('//img[@boxid="2765"]'):
            assert "width" not in node.attrib
            assert "style" not in node.attrib
            assert "infobox-img-wide" in node.attrib.get("class")
        for node in root.xpath('//img[@boxid="2795"]'):
            assert "width" in node.attrib
            assert "style" in node.attrib
            assert "infobox-img-wide" not in node.attrib.get("class", "")
