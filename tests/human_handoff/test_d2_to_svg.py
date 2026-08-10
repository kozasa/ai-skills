import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "skills/quick-html/scripts/d2_to_svg.py"


def load_module():
    specification = importlib.util.spec_from_file_location("d2_to_svg", MODULE_PATH)
    module = importlib.util.module_from_spec(specification)
    sys.modules["d2_to_svg"] = module
    specification.loader.exec_module(module)
    return module


SAFE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 10 10"><style>@font-face{font-family:"d2";src:url("data:application/font-woff2;base64,AAAA")}</style><rect width="10" height="10"/><text x="1" y="8">判定</text></svg>'


class D2ToSvgTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_svg(self, text):
        path = self.root / "flow.svg"
        path.write_text(text, encoding="utf-8")
        return path

    def test_postprocess_accepts_d2_output_with_embedded_data_fonts(self):
        path = self.write_svg(SAFE_SVG)
        self.module.postprocess(path)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("xmlns:xlink", text)
        self.assertIn("data:application/font-woff2", text)

    def test_postprocess_rejects_foreign_object(self):
        path = self.write_svg(SAFE_SVG.replace("<rect", "<foreignObject></foreignObject><rect"))
        with self.assertRaises(self.module.ContractError):
            self.module.postprocess(path)

    def test_postprocess_rejects_external_url(self):
        path = self.write_svg(SAFE_SVG.replace("<rect", '<style>rect{fill:url(https://example.com/x)}</style><rect'))
        with self.assertRaises(self.module.ContractError):
            self.module.postprocess(path)

    def test_render_arguments_use_sketch_mode(self):
        self.assertIn("--sketch", self.module.D2_ARGS)
        self.assertIn("--theme", self.module.D2_ARGS)

    def test_missing_d2_binary_raises_contract_error(self):
        source = self.root / "flow.d2"
        source.write_text("a -> b", encoding="utf-8")
        original = self.module.D2_BINARY
        self.module.D2_BINARY = str(self.root / "missing-d2")
        try:
            with self.assertRaises(self.module.ContractError):
                self.module.convert(source, self.root / "out/flow.svg")
        finally:
            self.module.D2_BINARY = original


if __name__ == "__main__":
    unittest.main()
