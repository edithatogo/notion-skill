# Track Template: Bug Fix

**Template ID**: bug-fix-track  
**Use Case**: Fixing bugs or issues  
**Typical Duration**: 1-3 days  

---

## Track: fix-<issue-number>-<YYYYMMDD>

**Phase**: <phase-number>  
**Priority**: <P0-P3>  
**Status**: planning  
**Created**: <created-date>  
**Owner**: <owner-name>  

---

## Issue Description

<Describe the bug being fixed>

**Reported By**: <reporter>  
**Reported Date**: <date>  
**Affected Versions**: <versions>  

---

## Root Cause

<Analysis of what caused the bug>

---

## Fix Plan

- [ ] Write failing test
- [ ] Implement fix in <file>
- [ ] Add regression tests
- [ ] Update documentation if needed
- [ ] Verify fix doesn't break existing functionality

---

## Testing

### Reproduction Steps
1. <step-1>
2. <step-2>
3. <step-3>

### Verification
- [ ] Original issue is resolved
- [ ] No regressions in <affected-area>
- [ ] Tests pass: <test-names>

---

## Files Changed

| File | Change Type | Lines |
|------|-------------|-------|
| <file.py> | Modified | +<n> -<m> |
| <test_file.py> | Added | +<n> |

---

## Review Checklist

- [ ] Code reviewed by <reviewer>
- [ ] Tests reviewed
- [ ] Documentation updated
- [ ] Changelog entry added

---

## Related Issues

- Fixes #<issue-number>
- Related to #<issue-number>
- Blocks #<issue-number>

---

*Template: bug-fix-track | Version: 1.0*
