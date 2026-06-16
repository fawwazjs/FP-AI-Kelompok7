import unittest
from unittest import mock

from backend import translator_service
from backend.ml import data_prep, inference


class MLDataPrepTests(unittest.TestCase):
    def test_parallel_corpus_has_both_directions_and_levels(self):
        rows = data_prep.build_parallel_corpus()
        self.assertGreater(len(rows), 1000)
        pairs = {(r["src_lang"], r["tgt_lang"]) for r in rows}
        # Both directions for each regional language must exist.
        self.assertIn(("id", "jv"), pairs)
        self.assertIn(("jv", "id"), pairs)
        self.assertIn(("id", "mad"), pairs)
        self.assertIn(("mad", "id"), pairs)
        levels = {r["level"] for r in rows}
        self.assertEqual(levels, {"high", "low"})

    def test_classifier_corpus_covers_three_languages(self):
        rows = data_prep.build_classifier_corpus()
        langs = {r["language"] for r in rows}
        self.assertEqual(langs, {"Indonesia", "Jawa", "Madura"})


class MLFallbackTests(unittest.TestCase):
    """When no model artifacts exist, the API must use the rule-based engine."""

    def test_translation_falls_back_without_model(self):
        # No artifacts in test env -> nmt_available() is False.
        self.assertFalse(inference.nmt_available())
        result = translator_service.translate_and_classify(
            "Saya ingin makan nasi goreng.", "id", "jv", "high"
        )
        self.assertIn("Kula", result["translatedText"])
        # Contract preserved.
        for key in ("translatedText", "politenessLevel", "ngokoPercentage",
                    "kramaPercentage", "context", "alternativeText"):
            self.assertIn(key, result)

    def test_detection_falls_back_without_model(self):
        self.assertFalse(inference.classifier_available())
        result = translator_service.detect_language_and_register("Kula badhe dhahar sekul.")
        self.assertEqual(result["language"], "Jawa")
        for key in ("language", "register", "explanation"):
            self.assertIn(key, result)


class MLActivePathTests(unittest.TestCase):
    """Simulate trained models being available via mocks."""

    def test_translation_uses_model_when_available(self):
        fake = {
            "translatedText": "MODEL-OUTPUT",
            "politenessLevel": "Krama Alus",
            "ngokoPercentage": 20.0,
            "kramaPercentage": 80.0,
            "context": "from model",
            "alternativeText": None,
        }
        with mock.patch.object(translator_service, "_ml_translate_and_classify", return_value=fake):
            result = translator_service.translate_and_classify("apa saja", "id", "jv", "high")
        self.assertEqual(result["translatedText"], "MODEL-OUTPUT")

    def test_detection_uses_classifier_when_available(self):
        with mock.patch.object(inference, "classify_language", return_value={
            "language": "Madura", "register": "Enja-Iya",
            "language_confidence": 91.2, "register_confidence": 80.0,
        }):
            result = translator_service.detect_language_and_register("sengko' ngakan")
        self.assertEqual(result["language"], "Madura")
        self.assertEqual(result["register"], "Enja-Iya")
        self.assertIn("91.2%", result["explanation"])

    def test_politeness_split_sums_to_100(self):
        with mock.patch.object(inference, "nmt_available", return_value=True), \
             mock.patch.object(inference, "translate", side_effect=lambda t, s, tg, lv: "Kula dhahar" if lv == "high" else "Aku mangan"), \
             mock.patch.object(inference, "classify_politeness", return_value=None):
            result = translator_service._ml_translate_and_classify("saya makan", "id", "jv", "high")
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["ngokoPercentage"] + result["kramaPercentage"], 100.0, places=1)


if __name__ == "__main__":
    unittest.main()
