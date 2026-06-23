import unittest
from backend.translator_service import translate_and_classify, detect_language_and_register

class GeminiIntegrationTests(unittest.TestCase):
    def test_gemini_translation_success(self):
        # Test translation Indonesian -> Javanese High
        res = translate_and_classify("saya ingin makan nasi goreng di warung dekat keraton", "id", "jv", "high")
        self.assertIn("translatedText", res)
        self.assertIn("politenessLevel", res)
        self.assertIn("ngokoPercentage", res)
        self.assertIn("kramaPercentage", res)
        self.assertIn("context", res)
        self.assertIn("alternativeText", res)
        
        # Verify it translates Javanese terms correctly
        translated = res["translatedText"].lower()
        self.assertTrue(any(word in translated for word in ["kula", "badhe", "dhahar", "sega", "sekul"]))

    def test_gemini_detection_success(self):
        # Test detecting Javanese Krama Alus
        res = detect_language_and_register("kula badhe dhahar sekul goreng wonten ing warung dekat kraton")
        self.assertEqual(res["language"], "Jawa")
        self.assertEqual(res["register"], "krama alus")
        self.assertTrue(len(res["explanation"]) > 0)

if __name__ == "__main__":
    unittest.main()
