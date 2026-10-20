"""Balanced country layout and native-only generator regression coverage."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fusion.flow_layout import GROUP_OFFSET, GROUP_SIZE, POSITION, arrange_country_stacks
from fusion.generator import _three_d_scene_x, generate
from tools.build_border_highlight_prototype import _tool_block


GEOMETRY = {"type": "Polygon", "coordinates": [[
    [0, 0], [2, 0], [2, 2], [0, 2], [0, 0],
]]}


def positions(content):
    return [(float(m[2]), float(m[3])) for m in POSITION.finditer(content)]


class CountryFlowLayoutTests(unittest.TestCase):
    def shot(self, count, child=False):
        codes = ['USA', 'CAN', 'EGY', 'IND', 'CHN'][:count]
        metadata = {
            'output': {'width': 1280, 'height': 720, 'wide_factor': 2},
            'wide': {'bbox_mercator': {'minx': -1000000, 'miny': -1000000,
                                      'maxx': 1000000, 'maxy': 1000000}},
            'countries': [{'iso3': iso, 'color': '#1689ff',
                           'geometry_file': f'geometry_{iso}.geojson'} for iso in codes],
        }
        groups = [{'iso3': iso, 'children': [
            {'id': f'country-{iso.lower()}', 'name': 'Entire country', 'category': 'country'}
        ]} for iso in codes]
        if child:
            groups[0]['children'].append({
                'id': 'local-region', 'name': 'Local region', 'category': 'administrative',
                'geometry_file': 'geometry_region.geojson'})
        animation = {'output': {'width': 1280, 'height': 720, 'fps': 24, 'duration_frames': 25},
                     'keyframes': [{'frame': 0, 'center': {'x': .5, 'y': .5}, 'view_width': .8},
                                   {'frame': 24, 'center': {'x': .55, 'y': .5}, 'view_width': .7}],
                     'connections': [], 'region_groups': groups}
        return codes, metadata, animation

    def write_geometry(self, package, codes):
        for iso in codes + ['region']:
            (package / f'geometry_{iso}.geojson').write_text(json.dumps({'geometry': GEOMETRY}))

    def test_zero_through_five_countries_in_both_modes(self):
        for mode in ('2d', '3d'):
            for count in range(6):
                with self.subTest(mode=mode, count=count), tempfile.TemporaryDirectory() as tmp:
                    package = Path(tmp)
                    codes, metadata, animation = self.shot(count)
                    self.write_geometry(package, codes)
                    with patch('fusion.generator.closeup_lod.plan_closeups', return_value=[]):
                        text = generate(package, metadata, animation, mode=mode).read_text()
                    center = _three_d_scene_x(0) if mode == '3d' else 2620
                    midpoint = (count + 1) // 2
                    ranges = [[], []]
                    for index, iso in enumerate(codes):
                        side = int(index >= midpoint)
                        country_points = []
                        # Check sources and downstream native tools, not only one anchor.
                        for name in (f'{iso}_Entire_Ring_01_Fill',
                                     f'{iso}_Flag_Loader',
                                     f'Country_Edit_{index + 1:02d}_Enabled'):
                            country_points.extend(positions(_tool_block(text, name)))
                        if mode == '3d':
                            # Existing exports may also include a native border
                            # group; when present it must move with its country.
                            if f'{iso}_Border_Highlight_Group = ' in text:
                                country_points.extend(positions(_tool_block(
                                    text, f'{iso}_Border_Highlight_Group')))
                            country_points.extend(positions(_tool_block(
                                text, f'Country_Edit_{index + 1:02d}_Plane')))
                        loader_x = positions(_tool_block(text, f'{iso}_Flag_Loader'))[0][0]
                        enabled_x = positions(_tool_block(
                            text, f'Country_Edit_{index + 1:02d}_Enabled'))[0][0]
                        if side == 0:
                            self.assertLess(loader_x, enabled_x)
                        else:
                            self.assertGreater(loader_x, enabled_x)
                        if mode == '3d':
                            plane_x = positions(_tool_block(
                                text, f'Country_Edit_{index + 1:02d}_Plane'))[0][0]
                            self.assertLess(enabled_x, plane_x) if side == 0 else \
                                self.assertGreater(enabled_x, plane_x)
                        for x, _y in country_points:
                            self.assertLessEqual(x, center - 400) if side == 0 else \
                                self.assertGreaterEqual(x, center + 1000)
                        ranges[side].append((min(y for _x, y in country_points),
                                             max(y for _x, y in country_points)))
                    for column in ranges:
                        for first, second in zip(column, column[1:]):
                            self.assertLess(first[1], second[0])
                    self.assertNotIn('CustomTool', text)
                    self.assertNotIn('UserControls', text)
                    self.assertNotIn('Country_Edit_Controller', text)
                    self.assertNotIn('Country_Mode_Switch.Deployment', text)
                    defined = set(re.findall(r'^\s*(\w+) = \w+ \{', text, re.M))
                    self.assertFalse(set(re.findall(r'SourceOp = "([^"]+)"', text)) - defined)

    @unittest.skipUnless(shutil.which('luajit'), 'LuaJIT not installed')
    def test_generated_2d_and_3d_compositions_parse_as_lua(self):
        for mode in ('2d', '3d'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                package = Path(tmp)
                codes, metadata, animation = self.shot(4, child=True)
                self.write_geometry(package, codes)
                with patch('fusion.generator.closeup_lod.plan_closeups', return_value=[]):
                    path = generate(package, metadata, animation, mode=mode)
                script = '''
local env=setmetatable({ordered=function()return function(t)return t end end},
    {__index=function(_,k)return function(t)t.kind=k;return t end end})
local f=assert(io.open(PATH));local s=f:read('*a');f:close()
local fn=assert(loadstring('return '..s));setfenv(fn,env)
local c=fn();assert(c.Tools.MediaOut1);assert(not c.Tools.Country_Edit_Controller)
'''.replace('PATH', json.dumps(str(path)))
                result = subprocess.run(['luajit', '-'], input=script, text=True,
                                        capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_subterritory_stays_with_country_and_layout_is_render_neutral(self):
        for mode in ('2d', '3d'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                package = Path(tmp)
                codes, metadata, animation = self.shot(4, child=True)
                self.write_geometry(package, codes)
                with patch('fusion.generator.closeup_lod.plan_closeups', return_value=[]):
                    actual = generate(package, metadata, animation, mode=mode).read_text()
                    with patch('fusion.generator.arrange_country_stacks',
                               side_effect=lambda content, *args, **kwargs: content):
                        original = generate(package, metadata, animation, mode=mode).read_text()
                def no_positions(text):
                    text = GROUP_OFFSET.sub(r'\g<1>0, 0\g<4>', POSITION.sub(
                        r'\g<1>0, 0\g<4>', text))
                    return GROUP_SIZE.sub(r'\g<1>\g<2>, \g<3>, 0, \g<5>\g<6>', text)
                self.assertEqual(no_positions(actual), no_positions(original))
                center = _three_d_scene_x(0) if mode == '3d' else 2620
                for name in ('USA_Local_region_Shapes', 'Country_Edit_02_Enabled'):
                    self.assertTrue(all(x <= center - 400 for x, _y in positions(
                        _tool_block(actual, name))))

    def test_expanded_groups_translate_internal_positions_and_inverse_offsets(self):
        text = '''\t\tAAA_Group = GroupOperator {
            ViewInfo = GroupInfo { Pos = { 10, 20 }, Size = { 100, 100 }, Offset = { -10, -20 } },
            Tools = { AAA_Fill = sPolygon {
                Inputs = { XOffset = Input { Value = 0.25 },
                    Polyline = Input { Value = Polyline { Points = { { X = 1, Y = 2 } } } } },
                ViewInfo = OperatorInfo { Pos = { 30, 40 } },
            } },
        },
\t\tBBB_Render = sRender { ViewInfo = OperatorInfo { Pos = { 10, 20 } } },
\t\tOther = Merge { ViewInfo = OperatorInfo { Pos = { 0, 0 } } },
'''
        result = arrange_country_stacks(text, ['AAA', 'BBB'], [], center_x=1000)
        group = _tool_block(result, 'AAA_Group')
        group_position = positions(group)[0]
        offset = GROUP_OFFSET.search(group)
        self.assertEqual(group_position, (-float(offset[2]), -float(offset[3])))
        points = positions(group)
        self.assertEqual((points[1][0] - points[0][0], points[1][1] - points[0][1]), (20, 20))
        self.assertIn('Points = { { X = 1, Y = 2 } }', result)
        self.assertEqual(_tool_block(text, 'Other'), _tool_block(result, 'Other'))

    def test_right_group_is_mirrored_including_frame_and_internal_nodes(self):
        group = '''\t\tBBB_Group = GroupOperator {
            ViewInfo = GroupInfo { Pos = { 10, 20 }, Size = { 100, 80, 30, -5 }, Offset = { -10, -20 } },
            Tools = { BBB_Source = Background {
                Inputs = { TopLeftRed = Input { Value = 0.25 } },
                ViewInfo = OperatorInfo { Pos = { 30, 40 } },
            } },
        },
'''
        text = ('\t\tAAA_Render = sRender { ViewInfo = OperatorInfo { Pos = { 30, 40 } } },\n'
                + group)
        result = arrange_country_stacks(text, ['AAA', 'BBB'], [], center_x=1000)
        actual = _tool_block(result, 'BBB_Group')
        pts = positions(actual)
        self.assertEqual((pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]), (-20, 20))
        offset = GROUP_OFFSET.search(actual)
        self.assertEqual(pts[0], (-float(offset[2]), -float(offset[3])))
        frame = GROUP_SIZE.search(actual)
        self.assertEqual(tuple(map(float, frame.groups()[1:5])), (100, 80, 70, -5))
        self.assertIn('TopLeftRed = Input { Value = 0.25 }', actual)


if __name__ == '__main__':
    unittest.main()
