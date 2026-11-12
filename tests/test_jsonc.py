import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import jsonc


class JsoncTests(unittest.TestCase):
    def test_comments_urls_and_trailing_commas(self):
        text = '''// settings
{"url":"https://example.org/*literal*/", /* comment */ "array":[1,2,],}'''
        self.assertEqual(jsonc.loads(text), {'url': 'https://example.org/*literal*/', 'array': [1, 2]})

    def test_invalid_or_duplicate_content_is_rejected(self):
        for text in ('', '{,}', '[,]', '{"x":NaN}', '{"x":1,"x":2}', '{"x":01}', '{/* unfinished}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                jsonc.loads(text)

    def test_root_type_is_checked(self):
        self.assertEqual(jsonc.require_type('[]', list), [])
        with self.assertRaises(ValueError):
            jsonc.require_type('[]', dict)


if __name__ == '__main__':
    unittest.main()
