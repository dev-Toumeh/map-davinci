import tempfile
import unittest
from pathlib import Path

from tools.build_optional_islands_prototype import build


def polygon(name: str, size: float) -> str:
    return f'''\t\t{name} = sPolygon {{
\t\t\tInputs = {{ Polyline = Input {{ Value = Polyline {{ Points = {{
\t\t\t\t{{ X = 0, Y = 0 }}, {{ X = {size}, Y = 0 }},
\t\t\t\t{{ X = {size}, Y = {size} }}, {{ X = 0, Y = {size} }},
\t\t\t}} }}, }} }},
\t\t}},'''


class OptionalIslandsPrototypeTests(unittest.TestCase):
    def test_only_significant_rings_remain_connected(self):
        content = "\n".join([
            polygon("GBR_Entire_Ring_01_Fill", 1),
            "\t\tGBR_Entire_Ring_01_Border = sPolygon { SourceOp = \"GBR_Entire_Ring_01_Fill\", },",
            polygon("GBR_Entire_Ring_02_Fill", .25),
            "\t\tGBR_Entire_Ring_02_Border = sPolygon { SourceOp = \"GBR_Entire_Ring_02_Fill\", },",
            polygon("GBR_Entire_Ring_03_Fill", .1),
            "\t\tGBR_Entire_Ring_03_Border = sPolygon { SourceOp = \"GBR_Entire_Ring_03_Fill\", },",
            "\t\tGBR_Entire_Shapes = sMerge { Inputs = {}, },",
        ])
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "in.comp", Path(tmp) / "out.comp"
            source.write_text(content)
            report = build(source, target, threshold=.05)
            result = target.read_text()
        self.assertEqual(report["essential_rings"], [1, 2])
        self.assertEqual(report["optional_rings"], [3])
        active = result.split("GBR_Entire_Shapes = sMerge", 1)[1].split(
            "GBR_Entire_Optional_Shapes", 1)[0]
        self.assertIn("Ring_02_Fill", active)
        self.assertNotIn("Ring_03_Fill", active)
        optional = result.split("GBR_Entire_Optional_Shapes", 1)[1]
        self.assertIn("Ring_03_Fill", optional)


if __name__ == "__main__":
    unittest.main()
