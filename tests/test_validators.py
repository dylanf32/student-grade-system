"""
Unit tests for the InputValidator.
"""

import unittest

from app.validators.input_validator import InputValidator


class TestValidateName(unittest.TestCase):

    def test_valid_name(self):
        valid, msg = InputValidator.validate_name("Ali Khan")
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_empty_name(self):
        valid, msg = InputValidator.validate_name("")
        self.assertFalse(valid)

    def test_whitespace_name(self):
        valid, msg = InputValidator.validate_name("   ")
        self.assertFalse(valid)

    def test_single_char_name(self):
        valid, msg = InputValidator.validate_name("A")
        self.assertFalse(valid)

    def test_name_with_numbers(self):
        valid, msg = InputValidator.validate_name("Ali123")
        self.assertFalse(valid)


class TestValidateGrade(unittest.TestCase):

    def test_valid_grade(self):
        valid, _ = InputValidator.validate_grade(85)
        self.assertTrue(valid)

    def test_boundary_zero(self):
        valid, _ = InputValidator.validate_grade(0)
        self.assertTrue(valid)

    def test_boundary_hundred(self):
        valid, _ = InputValidator.validate_grade(100)
        self.assertTrue(valid)

    def test_negative_grade(self):
        valid, _ = InputValidator.validate_grade(-1)
        self.assertFalse(valid)

    def test_over_hundred(self):
        valid, _ = InputValidator.validate_grade(101)
        self.assertFalse(valid)


class TestValidateIndex(unittest.TestCase):

    def test_valid_index(self):
        valid, _ = InputValidator.validate_index(0, 5)
        self.assertTrue(valid)

    def test_last_valid_index(self):
        valid, _ = InputValidator.validate_index(4, 5)
        self.assertTrue(valid)

    def test_negative_index(self):
        valid, _ = InputValidator.validate_index(-1, 5)
        self.assertFalse(valid)

    def test_out_of_range_index(self):
        valid, _ = InputValidator.validate_index(5, 5)
        self.assertFalse(valid)

    def test_empty_list(self):
        valid, _ = InputValidator.validate_index(0, 0)
        self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main()
