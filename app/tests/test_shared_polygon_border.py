import unittest

from tools.share_polygon_border import _put_border_behind_fill


class SharedPolygonBorderTests(unittest.TestCase):
    def test_border_layer_is_placed_behind_fill(self):
        source = '''
                ["Layer1.Foreground"] = Input { SourceOp = "Region_Fill", Source = "Output", },
                LayerName1 = Input { Value = "Example fill", },
                ["Layer2.Foreground"] = Input { SourceOp = "Region_Border", Source = "Output", },
                LayerName2 = Input { Value = "Example border", },'''
        result = _put_border_behind_fill(source, "Region")
        self.assertIn('Layer1.Foreground"] = Input { SourceOp = "Region_Border"', result)
        self.assertIn('Layer2.Foreground"] = Input { SourceOp = "Region_Fill"', result)
        self.assertIn('Value = "Example generated border"', result)


if __name__ == "__main__":
    unittest.main()
