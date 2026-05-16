import unittest

from services.text_chunker import chunk_text


class TextChunkerTestCase(unittest.TestCase):
    def test_chunk_text_builds_overlap_windows(self) -> None:
        text = "abcdefghij"

        chunks = chunk_text(text, chunk_size=5, overlap=2)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[0].content, "abcde")
        self.assertEqual(chunks[0].preview, "abcde")
        self.assertEqual(chunks[0].char_start, 0)
        self.assertEqual(chunks[0].char_end, 5)
        self.assertEqual(chunks[1].chunk_index, 1)
        self.assertEqual(chunks[1].content, "defgh")
        self.assertEqual(chunks[1].preview, "defgh")
        self.assertEqual(chunks[1].char_start, 3)
        self.assertEqual(chunks[1].char_end, 8)
        self.assertEqual(chunks[2].chunk_index, 2)
        self.assertEqual(chunks[2].content, "ghij")
        self.assertEqual(chunks[2].preview, "ghij")
        self.assertEqual(chunks[2].char_start, 6)
        self.assertEqual(chunks[2].char_end, 10)

    def test_chunk_text_filters_blank_input(self) -> None:
        self.assertEqual(chunk_text("   \n\t  ", chunk_size=5, overlap=1), [])

    def test_chunk_text_rejects_non_positive_chunk_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "chunk_size 必须大于 0"):
            chunk_text("abc", chunk_size=0, overlap=0)

    def test_chunk_text_rejects_negative_overlap(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "overlap 必须大于等于 0 且小于 chunk_size"
        ):
            chunk_text("abc", chunk_size=2, overlap=-1)

    def test_chunk_text_rejects_overlap_not_smaller_than_chunk_size(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "overlap 必须大于等于 0 且小于 chunk_size"
        ):
            chunk_text("abc", chunk_size=2, overlap=2)

    def test_chunk_text_advances_when_overlap_is_chunk_size_minus_one(self) -> None:
        chunks = chunk_text("abcd", chunk_size=2, overlap=1)

        self.assertEqual([chunk.content for chunk in chunks], ["ab", "bc", "cd"])
        self.assertEqual([chunk.chunk_index for chunk in chunks], [0, 1, 2])
        self.assertEqual([chunk.char_start for chunk in chunks], [0, 1, 2])
        self.assertEqual([chunk.char_end for chunk in chunks], [2, 3, 4])

    def test_chunk_text_trims_edge_whitespace_for_offsets_and_preview(self) -> None:
        chunks = chunk_text("  abc  def  ", chunk_size=12, overlap=2)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, "abc  def")
        self.assertEqual(chunks[0].preview, "abc  def")
        self.assertEqual(chunks[0].char_start, 2)
        self.assertEqual(chunks[0].char_end, 10)


if __name__ == "__main__":
    unittest.main()
