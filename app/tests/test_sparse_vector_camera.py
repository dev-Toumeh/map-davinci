import tempfile
import unittest
from pathlib import Path

from tools.build_sparse_vector_camera import _replace_vector_controller, _tool_span


class SparseVectorCameraTests(unittest.TestCase):
    def test_tool_span_handles_nested_braces(self):
        content = '\t\tA = BezierSpline { KeyFrames = { [0] = { 0 } } },\n\t\tB = XYPath {},'
        start, end = _tool_span(content, "A")
        self.assertEqual(content[start:end], '\t\tA = BezierSpline { KeyFrames = { [0] = { 0 } } },')

    def test_replaces_only_dense_vector_tools(self):
        content = '''Composition { Tools = {
\t\tVector_AnimationDisplacement = BezierSpline { KeyFrames = { [0] = { 0 } } },
\t\tVector_AnimationPath = PolyPath { Inputs = { Displacement = Input { SourceOp = "Vector_AnimationDisplacement" } } },
\t\tKeep = Transform {},
} }'''
        result = _replace_vector_controller(content, '\t\tSparse = XYPath {},')
        self.assertIn("Sparse = XYPath", result)
        self.assertIn("Keep = Transform", result)
        self.assertNotIn("Vector_AnimationDisplacement", result)


if __name__ == "__main__":
    unittest.main()
