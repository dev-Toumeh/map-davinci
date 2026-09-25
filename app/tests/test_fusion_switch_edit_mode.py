import tempfile
import unittest
from pathlib import Path

from tools.add_fusion_switch_edit_mode import build


class FusionSwitchEditModeTests(unittest.TestCase):
    def test_builds_native_edit_and_final_switches(self):
        source_text = '''{
\tTools = ordered() {
\t\tCountry_USA_Canvas = Background { Inputs = {}, },
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
\t\tCountry_USA_Gate = Merge { Inputs = { Foreground = Input { SourceOp = "Country_USA_Regions", Source = "Output", }, }, },
\t},
}
'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.comp"
            target = Path(directory) / "target.comp"
            source.write_text(source_text, encoding="utf-8")
            report = build(
                source, target, "Country_USA_Regions", "Country_USA_Gate", "Alaska Purchase"
            )
            result = target.read_text(encoding="utf-8")

        self.assertEqual(report["default_edit_territory"], "Alaska Purchase")
        self.assertEqual(result.count("EDIT_TERRITORY_SWITCH = Switch"), 1)
        self.assertEqual(result.count("EDIT_FINAL_SWITCH = Switch"), 1)
        self.assertIn('Name1 = Input { Value = "Alaska Purchase", }', result)
        self.assertIn('Name2 = Input { Value = "Entire country", }', result)
        self.assertIn('SourceOp = "EDIT_FINAL_SWITCH"', result)


if __name__ == "__main__":
    unittest.main()
