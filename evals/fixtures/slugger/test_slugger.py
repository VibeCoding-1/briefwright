import unittest

from slugger import slugify


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_collapses_repeated_separators(self):
        self.assertEqual(slugify("a  -  b"), "a-b")

    def test_strips_leading_trailing_dashes(self):
        self.assertEqual(slugify("--Hello--"), "hello")

    def test_unicode_transliteration(self):
        self.assertEqual(slugify("Café con Leche"), "cafe-con-leche")


if __name__ == "__main__":
    unittest.main()
