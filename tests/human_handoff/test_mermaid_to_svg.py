import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills/quick-html/scripts/mermaid_to_svg.py"


def load_module():
    specification = importlib.util.spec_from_file_location("mermaid_to_svg", MODULE_PATH)
    module = importlib.util.module_from_spec(specification)
    sys.modules["mermaid_to_svg"] = module
    specification.loader.exec_module(module)
    return module


SAFE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 10 10"><rect width="10" height="10"/><text x="1" y="8">判定</text></svg>'


class MermaidToSvgTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_svg(self, text):
        path = self.root / "flow.svg"
        path.write_text(text, encoding="utf-8")
        return path

    def test_postprocess_strips_unused_xlink_namespace_and_validates(self):
        path = self.write_svg(SAFE_SVG)
        self.module.postprocess(path)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("xmlns:xlink", text)
        self.assertIn("<rect", text)

    def test_postprocess_keeps_svg_without_xlink_namespace_valid(self):
        path = self.write_svg(SAFE_SVG.replace(' xmlns:xlink="http://www.w3.org/1999/xlink"', ""))
        self.module.postprocess(path)
        self.assertIn("<rect", path.read_text(encoding="utf-8"))

    def test_postprocess_rejects_foreign_object(self):
        path = self.write_svg(SAFE_SVG.replace("<rect", "<foreignObject></foreignObject><rect"))
        with self.assertRaises(self.module.ContractError):
            self.module.postprocess(path)

    def test_postprocess_rejects_used_xlink_reference(self):
        path = self.write_svg(SAFE_SVG.replace("<rect", '<use xlink:href="#x"/><rect'))
        with self.assertRaises(self.module.ContractError):
            self.module.postprocess(path)

    def test_mermaid_cli_version_is_pinned(self):
        self.assertRegex(self.module.MERMAID_CLI, r"^@mermaid-js/mermaid-cli@\d+\.\d+\.\d+$")

    def test_default_config_disables_html_labels_and_uses_strict_security(self):
        config = self.module.DEFAULT_CONFIG
        self.assertEqual(config["securityLevel"], "strict")
        self.assertFalse(config["htmlLabels"])
        self.assertFalse(config["flowchart"]["htmlLabels"])


if __name__ == "__main__":
    unittest.main()
