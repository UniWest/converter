# Step 6: Automated Tests Documentation

This directory contains comprehensive automated tests for **Step 6** of the project, covering form validation edge cases and integration testing for MP4 to GIF conversion functionality.

## Overview

The automated test suite includes:

- **Unit Tests**: Form validation edge cases (file size limits, format validation, invalid time ranges)
- **Integration Tests**: End-to-end client workflow testing (MP4 upload → GIF response)
- **Test Fixtures**: Sample media files for realistic testing scenarios

## Test Framework

- **pytest**: Primary testing framework
- **Django TestCase**: Django-specific test utilities
- **Sample fixtures**: Located in `tests/media/` directory

## Test Files Structure

```
tests/
├── AUTOMATED_TESTS_README.md          # This documentation
├── requirements_test.txt               # Testing dependencies
├── create_test_media.py               # Script to create sample media files
├── run_automated_tests.py             # Main test runner script
├── test_form_validation.py            # Unit tests for form validation
├── test_integration_mp4_to_gif.py     # Integration tests
└── media/                             # Test fixture files
    ├── small_sample.mp4               # 40 bytes minimal MP4
    ├── medium_sample.mp4              # 1KB MP4 for testing
    ├── wrong_format.txt               # Invalid format file
    ├── big_file_marker.txt            # Represents large files
    └── invalid_times.json             # Test cases for time validation
```

## Unit Tests (`test_form_validation.py`)

### VideoUploadForm Tests
Tests the main video upload form validation with edge cases:

- **File Size Validation**: Tests 500MB limit enforcement
- **Format Validation**: Rejects unsupported file types (`.txt`, etc.)
- **Width Validation**: 
  - Minimum: 144px
  - Maximum: 3840px (4K)
  - Must be even numbers (FFmpeg requirement)
- **FPS Validation**:
  - Range: 15-60 FPS
  - Boundary testing
- **Time Range Validation**:
  - Negative start times (invalid)
  - End time before start time (invalid)
  - Duration > 10 minutes (invalid)
  - Zero duration (invalid)
- **Conversion Settings Generation**: Verifies form produces correct parameter dict

### AudioToTextForm Tests
- **File Size**: 200MB limit for audio files
- **Format Validation**: Rejects non-audio formats

### ImagesToGifForm Tests
- **Image Count**: Minimum 2, maximum 100 images
- **Frame Duration**: 0.1-5.0 seconds range
- **Total File Size**: 100MB combined limit

### VideoProcessingForm Tests
- **Fast Processing**: 200MB limit for simplified form
- **Quality Mapping**: Verifies preset quality settings

## Integration Tests (`test_integration_mp4_to_gif.py`)

### Core Workflow Tests
- **Home Page Loading**: Verifies view functionality
- **MP4 Upload**: Tests complete upload → conversion → GIF response workflow
- **Database Integration**: Ensures ConversionTask records are created
- **Error Handling**: Tests conversion failures and form validation errors

### Edge Case Integration
- **Invalid File Formats**: Full workflow with validation errors
- **Concurrent Uploads**: Multiple simultaneous requests
- **Large File Handling**: Integration with form size limits

### Mocking Strategy
Uses `unittest.mock` to isolate components:
- **VideoConversionService**: Mocked for consistent test results
- **File System Operations**: Mocked to avoid actual file I/O
- **External Dependencies**: Isolated for reliable testing

## Running Tests

### Prerequisites
```bash
pip install -r tests/requirements_test.txt
```

### Create Test Fixtures
```bash
python tests/create_test_media.py
```

### Run All Tests
```bash
python tests/run_automated_tests.py
```

### Run Specific Test Types
```bash
# Unit tests only
python tests/run_automated_tests.py --unit-only

# Integration tests only  
python tests/run_automated_tests.py --integration-only

# Verbose output
python tests/run_automated_tests.py --verbose

# Show available tests
python tests/run_automated_tests.py --collect
```

### Direct pytest Usage
```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_form_validation.py -v

# Specific test method
python -m pytest tests/test_form_validation.py::VideoUploadFormTests::test_file_too_big_validation -v
```

## Test Coverage

### Form Validation Edge Cases ✅
- [x] File size limits (500MB for video, 200MB for audio)
- [x] Invalid file formats (.txt instead of .mp4)
- [x] Width validation boundaries (144-3840px, even numbers)
- [x] FPS validation boundaries (15-60 fps)
- [x] Time range validation (negative times, invalid durations)
- [x] Duration limits (10 minute maximum)
- [x] Multi-file validation (images: 2-100 files)

### Integration Testing ✅
- [x] Client posts small sample MP4
- [x] Server returns 200 status code
- [x] Response has GIF content-type
- [x] Database records are created
- [x] Error handling for invalid inputs
- [x] Concurrent request handling

### Test Data Quality ✅
- [x] Minimal valid MP4 files (40 bytes, 1KB)
- [x] Invalid format samples
- [x] JSON test case definitions
- [x] Boundary value test cases

## Expected Test Results

When all tests pass, you should see:
```
=================== 25 tests passed ===================

Unit Tests: 15 passed
Integration Tests: 10 passed
```

### Sample Test Output
```
🚀 Running All Automated Tests
================================================================================
✅ All test fixture files are present

📋 Test Summary:
   - Unit tests: Form validation edge cases
   - Integration tests: Client MP4 upload → GIF response  
   - Framework: pytest + Django assertions
   - Fixtures: tests/media/ sample files

tests/test_form_validation.py::VideoUploadFormTests::test_valid_form_submission PASSED
tests/test_form_validation.py::VideoUploadFormTests::test_file_too_big_validation PASSED
...
tests/test_integration_mp4_to_gif.py::MP4ToGifIntegrationTest::test_small_mp4_upload_returns_200_with_gif PASSED
=================== 25 tests passed in 2.34s ===================
```

## Key Testing Principles

1. **Isolation**: Each test is independent and can run in any order
2. **Mocking**: External dependencies are mocked for reliable results
3. **Edge Cases**: Focus on boundary conditions and error scenarios
4. **Realistic Data**: Use actual MP4 files and realistic test scenarios
5. **Documentation**: Each test has clear docstrings explaining its purpose

## Troubleshooting

### Common Issues

1. **Missing Test Fixtures**:
   ```bash
   python tests/create_test_media.py
   ```

2. **Django Settings Issues**:
   ```bash
   export DJANGO_SETTINGS_MODULE=converter_site.settings
   ```

3. **Missing Dependencies**:
   ```bash
   pip install pytest pytest-django
   ```

4. **Database Issues**:
   ```bash
   python manage.py migrate --run-syncdb
   ```

### Test Failures

If tests fail, check:
- Test fixture files exist in `tests/media/`
- Django settings are properly configured
- All required form fields are included in test data
- Mock configurations match actual code structure

## Contributing

When adding new tests:
1. Follow the existing naming convention (`test_<feature>_<scenario>`)
2. Include docstrings explaining test purpose
3. Use appropriate mocking to isolate components
4. Add edge cases and boundary conditions
5. Update this README if adding new test categories

## Continuous Integration

These tests are designed to be run in CI/CD pipelines. The test runner script provides exit codes for build system integration:
- `0`: All tests passed
- `1`: Some tests failed or errors occurred

## Summary

This test suite provides comprehensive coverage of the requirements for Step 6:

✅ **Unit tests**: form validation edge cases (too big, wrong format, invalid times)  
✅ **Integration tests**: client posts small sample mp4, asserts 200 and gif content-type  
✅ **Uses pytest, django-asserts, and sample fixtures under tests/media/**

The tests are fully automated, provide detailed output, and can be integrated into CI/CD pipelines for continuous quality assurance.
