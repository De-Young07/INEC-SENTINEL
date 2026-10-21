"""Guard against the light-background/dark-theme contrast regression."""
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ThemeTests(unittest.TestCase):
    def test_theme_and_custom_surfaces_are_consistent(self):
        theme = tomllib.loads((ROOT / '.streamlit/config.toml').read_text())['theme']
        source = (ROOT / 'src/app.py').read_text(encoding='utf-8')
        self.assertEqual(theme['base'], 'dark')
        self.assertIn('background:' + theme['backgroundColor'], source)
        self.assertIn('color:' + theme['textColor'], source)
        self.assertNotIn('background:white', source)
