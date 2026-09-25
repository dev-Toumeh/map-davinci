import tempfile
import unittest
from pathlib import Path

from tools.add_fusion_performance_controller import build


class FusionPerformanceControllerTests(unittest.TestCase):
    def test_adds_one_controller_and_pairs_fill_with_border(self):
        source_text = '''{
\tTools = ordered() {
\t\tCountry_USA_Regions = MultiMerge {
\t\t\tInputs = {
\t\t\t\t["Layer1.Foreground"] = Input { SourceOp = "USA_Fill", Source = "Output", },
\t\t\t\tLayerName1 = Input { Value = "Entire country fill", },
\t\t\t\t["Layer2.Foreground"] = Input { SourceOp = "USA_Border", Source = "Output", },
\t\t\t\tLayerName2 = Input { Value = "Entire country border", },
\t\t\t\t["Layer3.Foreground"] = Input { SourceOp = "Alaska_Fill", Source = "Output", },
\t\t\t\tLayerName3 = Input { Value = "Alaska Purchase fill", },
\t\t\t\t["Layer4.Foreground"] = Input { SourceOp = "Alaska_Border", Source = "Output", },
\t\t\t\tLayerName4 = Input { Value = "Alaska Purchase border", },
\t\t\t},
\t\t},
\t},
}
'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.comp"
            target = Path(directory) / "target.comp"
            source.write_text(source_text, encoding="utf-8")
            report = build(source, target, "Country_USA_Regions", "Alaska Purchase")
            result = target.read_text(encoding="utf-8")

        self.assertEqual(report["territories"], ["Entire country", "Alaska Purchase"])
        self.assertEqual(report["controlled_layers"], 4)
        self.assertEqual(result.count("PERFORMANCE_CONTROLLER = CustomTool"), 1)
        self.assertIn("ActiveTerritory = Input { Value = 1, }", result)
        self.assertEqual(result.count("ActiveTerritory == 0"), 2)
        self.assertEqual(result.count("ActiveTerritory == 1"), 2)
        self.assertIn("LayerEnabled4 = Input { Expression =", result)


if __name__ == "__main__":
    unittest.main()
