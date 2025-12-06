import unittest
from mom_test import MomTest

class TestMomTest(unittest.TestCase):
    def test_rewrite_question(self):
        mom = MomTest()
        bad_question = "Would you pay for an app that tracks your sleep?"
        rewritten = mom.rewrite_question(bad_question)
        
        print(f"\nOriginal: {bad_question}")
        print(f"Rewritten: {rewritten}")
        
        self.assertIsInstance(rewritten, str)
        self.assertNotEqual(rewritten, bad_question)
        self.assertTrue(len(rewritten) > 10)

if __name__ == '__main__':
    unittest.main()
