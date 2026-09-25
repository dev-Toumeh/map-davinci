import unittest
from pathlib import Path


class AudioTimelineUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).parents[1] / "static" / "animation.html").read_text()

    def test_clip_drag_is_track_wide_and_not_blocked_by_edit_mode(self):
        self.assertIn('function updateAudioDrag(clientX)', self.html)
        self.assertIn('document.addEventListener("pointermove",e=>{if(!audioDrag)return;', self.html)
        self.assertIn('clip.start_frame=clamp(base.start_frame+delta,0,total()-1)', self.html)
        self.assertNotIn('if(editMode!=="commentary")return;e.stopPropagation();selectedAudioId=clip.id', self.html)

    def test_audio_files_can_be_dropped_at_a_timeline_position(self):
        self.assertIn('addEventListener("drop",async e=>', self.html)
        self.assertIn('addAudioFiles(e.dataTransfer?.files,audioFrameAt(e.clientX))', self.html)
        self.assertIn('classList.add("drop-active")', self.html)


if __name__ == "__main__":
    unittest.main()
