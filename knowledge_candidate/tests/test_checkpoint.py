import unittest
from pathlib import Path
from unittest.mock import patch
from experiment import atomic_replace


class CheckpointTests(unittest.TestCase):
    def test_transient_windows_lock_is_retried(self):
        with patch.object(Path, 'replace', side_effect=[PermissionError(), None]) as replace:
            with patch('experiment.time.sleep') as sleep:
                atomic_replace(Path('temporary'), Path('published'))
                self.assertEqual(replace.call_count, 2)
                sleep.assert_called_once_with(.05)

    def test_persistent_lock_is_reported(self):
        with patch.object(Path, 'replace', side_effect=PermissionError()) as replace:
            with patch('experiment.time.sleep'):
                with self.assertRaises(PermissionError):
                    atomic_replace(Path('temporary'), Path('published'))
                self.assertEqual(replace.call_count, 60)
