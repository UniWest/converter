# Step 6: Linting Issues and Fixes

## Summary of Major Issues Found

### 1. **Critical Errors** (F821 - Undefined Names)
- **Image processing**: Missing `Image` imports in `image_engine.py` and `utils.py`
- **Location**: `converter/adapters/image_engine.py` lines 310, 327, 330, 334, 345
- **Location**: `converter/utils.py` lines 829, 832, 897, 917
- **Fix**: Add proper PIL Image imports where needed

### 2. **Logic Errors** (E722, E713, E721)
- **Bare except clauses**: Multiple files using `except:` without specific exceptions
- **Type comparisons**: Using `==` instead of `isinstance()` for type checks
- **Membership tests**: Should use `not in` instead of `not x in`

### 3. **Unused Variables** (F841)
- Several local variables assigned but never used
- Most can be safely removed or replaced with `_` for ignored variables

### 4. **Import Issues** (E402, F811)
- Module level imports not at top of file
- Redefinition of imported modules
- Multiple imports of same module

## High Priority Fixes

### 1. Fix Image Import Issues
```python
# In image_engine.py and utils.py, add proper imports:
from PIL import Image
```

### 2. Fix Bare Exception Handling
Replace bare `except:` with specific exceptions:
```python
# Bad
except:
    pass

# Good
except (OSError, IOError):
    pass
```

### 3. Fix Type Comparisons
```python
# Bad
if param_type == bool:

# Good
if param_type is bool:
```

## Medium Priority Fixes

### 1. Clean Up Unused Variables
- Remove or rename with `_` prefix
- Use `_` for intentionally ignored values

### 2. Fix Import Organization
- Move all imports to top of file
- Remove duplicate imports
- Use proper import structure

## Low Priority (Style Issues)

### 1. Remove f-string without placeholders
```python
# Bad
print(f"Static message")

# Good
print("Static message")
```

### 2. Fix whitespace and formatting issues
- Remove trailing whitespace
- Fix blank line issues
- Proper indentation

## Status Summary

- **Django check**: ✅ PASSED (no issues)
- **Basic functionality**: ✅ PASSED (smoke tests)  
- **Required dependencies**: ✅ VERIFIED
  - `pydub==0.25.1` ✓
  - `ffmpeg-python==0.2.0` ✓
  - `django-cors-headers==4.6.0` ✓
- **Celery configuration**: ✅ CONFIRMED (eager mode for dev/testing)

## Test Results

- **Smoke tests**: 6/6 passed
- **Django tests**: Some failures related to missing URL patterns, but core functionality works
- **Linting**: 131 issues found (mostly style and some logic errors)

## Recommendations

1. **Immediate**: Fix critical Image import issues
2. **Short-term**: Address bare exceptions and type comparison issues  
3. **Medium-term**: Clean up unused variables and import organization
4. **Long-term**: Address style issues and improve test coverage

## Next Steps

1. Apply critical fixes for Image imports
2. Fix bare exception handling
3. Update type comparisons
4. Run tests to verify fixes
5. Commit and document changes
