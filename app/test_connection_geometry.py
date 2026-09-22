import math
import unittest

from connection_geometry import connection_shapes, connection_tools, dash_segments, path_at


def connection(**changes):
    return dict(id='test', name='Test', start={'x': .2, 'y': .3}, end={'x': .7, 'y': .3},
                bend={'x': .4, 'y': .1}, path_type='straight', line_style='solid',
                thickness=2, arrow_size=14, arrowhead=False, color='#ffffff',
                start_frame=10, arrival_frame=30, disappearance_frame=None,
                easing='linear') | changes


class ConnectionGeometryTests(unittest.TestCase):
    def test_solid_is_continuous_with_constant_output_thickness(self):
        out = {'width': 2160, 'height': 3840}
        for zoom in (1, 3, 20):
            shapes = connection_shapes(connection(), 30, zoom, 3840, 2160, out)
            self.assertEqual(len(shapes), 1)
            shape = shapes[0]
            self.assertAlmostEqual(min(p[0] for p in shape), -.3)
            self.assertAlmostEqual(max(p[0] for p in shape), .2)
            self.assertAlmostEqual((max(p[1] for p in shape)-min(p[1] for p in shape))*2160*zoom, 6)

    def test_curve_and_arrow_follow_browser_parameter(self):
        c = connection(path_type='curved', arrowhead=True, easing='smooth')
        out = {'width': 1080, 'height': 1920}
        # Quarter duration smoothstep = .15625; curve goes toward, not through, bend.
        t = .15625
        p = path_at(c, t)
        self.assertAlmostEqual(p[0], (1-t)**2*.2+2*(1-t)*t*.4+t*t*.7)
        for zoom in (1, 8):
            arrow = connection_shapes(c, 15, zoom, 3840, 2160, out)[-1]
            tip = ((arrow[0][0]+.5)*3840*zoom, (.5-arrow[0][1])*2160*zoom)
            center = (p[0]*3840*zoom, p[1]*2160*zoom)
            self.assertAlmostEqual(math.dist(tip, center), 14*.65)
            previous = path_at(c, t-.015)
            expected = math.atan2((p[1]-previous[1])*2160, (p[0]-previous[0])*3840)
            actual = math.atan2(tip[1]-center[1], tip[0]-center[0])
            self.assertAlmostEqual(actual, expected)

    def test_dashes_are_geometry_with_correct_spacing(self):
        segments = dash_segments([(0, 0), (7, 0), (30, 0)], 10, 8)
        self.assertEqual(segments, [[(0, 0), (7., 0.), (10., 0.)], [(18., 0.), (28., 0.)]])

    def test_export_has_native_shapes_and_exact_visibility(self):
        camera = [{'frame': 0, 'zoom': 2}]
        out = {'width': 1080, 'height': 1920}
        text, layer = connection_tools(connection(arrowhead=True), 3840, 2160, 35, 0, 2, camera, out)
        self.assertIn('MultiPoly', text)
        self.assertIn('time >= 10 and time < 36', text)
        self.assertNotIn('TextPlus', text)
        self.assertNotIn('StyledText', text)
        self.assertIn('Layer2.Foreground', layer)


if __name__ == '__main__':
    unittest.main()
