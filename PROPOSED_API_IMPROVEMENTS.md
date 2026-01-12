# Macro Tracker API Improvements — Preventing Duplicate Entry Bugs

## The Bug

On 2026-01-11, an LLM logged the same meal multiple times:
1. First attempt: USDA lookup partially failed, but some items got logged
2. Retries: LLM retried with different approaches, each adding more entries
3. Result: 8 duplicate entries, inflated totals (4019 cal instead of ~1900 cal)

## Root Cause

The API has no protection against duplicate entries. Every `log_food()` call blindly appends, even if:
- Same food was just logged seconds ago
- LLM is retrying after a partial failure
- User accidentally asks to log the same thing twice

## Proposed Solutions

### 1. Duplicate Detection (Highest Impact, Easiest)

Add a `dedupe_window_minutes` parameter with sensible default:

```python
def log_food(
    self,
    name: str,
    quantity: float = 1,
    ...,
    dedupe_window_minutes: int = 5,  # NEW - set to 0 to disable
) -> dict:
    """
    If same food name (case-insensitive) was logged within dedupe_window_minutes,
    returns the existing entry with a flag instead of creating duplicate.
    """
```

**Behavior:**
```python
tracker.log_food("rice", quantity=2)
# Returns: {"logged": True, "entry": {...}}

tracker.log_food("rice", quantity=2)  # Called again within 5 min
# Returns: {"logged": False, "reason": "duplicate_detected", 
#           "existing_entry": {...}, "suggestion": "Use dedupe_window_minutes=0 to force"}

tracker.log_food("rice", quantity=2, dedupe_window_minutes=0)  # Force it
# Returns: {"logged": True, "entry": {...}}
```

**Implementation in `tracker.py`:**
```python
def log_food(self, name, quantity=1, ..., dedupe_window_minutes=5):
    # Check for recent duplicates
    if dedupe_window_minutes > 0:
        recent = self.get_food_log()  # Today's entries
        cutoff = datetime.now() - timedelta(minutes=dedupe_window_minutes)
        for entry in recent:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            if entry_time > cutoff and entry['name'].lower() == name.lower():
                return {
                    "logged": False,
                    "reason": "duplicate_detected",
                    "message": f"'{name}' was already logged {minutes_ago} minutes ago",
                    "existing_entry": entry,
                    "suggestion": "Set dedupe_window_minutes=0 to log anyway"
                }
    # ... rest of existing logic
```

---

### 2. Dry Run Mode (Preview Before Commit)

Add `dry_run` parameter to preview what would be logged:

```python
def log_food(self, name, ..., dry_run: bool = False) -> dict:
    """
    If dry_run=True, returns what WOULD be logged without saving.
    Useful for LLMs to verify nutrition lookup before committing.
    """
```

**Behavior:**
```python
result = tracker.log_food("chicken breast", quantity=150, unit="g", dry_run=True)
# Returns: {"dry_run": True, "would_log": {"name": "chicken breast", 
#           "calories": 248, "protein_g": 46.5, ...}}

# LLM can verify, then commit:
tracker.log_food("chicken breast", quantity=150, unit="g")
```

---

### 3. Batch/Meal Logging (Atomic Operations)

Add `log_meal()` for logging multiple items together:

```python
def log_meal(
    self,
    items: list[dict],
    meal_name: str = None,
    dedupe_window_minutes: int = 5,
) -> dict:
    """
    Log multiple food items atomically.
    
    Args:
        items: List of {"name": str, "quantity": float, "unit": str, ...}
        meal_name: Optional name for the meal (used in deduplication)
        
    Returns:
        {"success": True, "items": [...], "total": {"calories": X, ...}}
        OR
        {"success": False, "reason": "...", "failed_items": [...]}
    """
```

**Behavior:**
```python
tracker.log_meal([
    {"name": "rice", "quantity": 2, "unit": "cup", "calories": 440, "protein_g": 10},
    {"name": "sambhar", "quantity": 1, "unit": "cup", "calories": 150, "protein_g": 8},
    {"name": "cabbage sabzi", "quantity": 1, "unit": "cup", "calories": 100, "protein_g": 3},
], meal_name="dinner")

# Returns:
{
    "success": True,
    "meal_name": "dinner",
    "items": [...],
    "total": {"calories": 690, "protein_g": 21, "carbs_g": 122, "fat_g": 13}
}
```

---

### 4. Recent Entries Helper

Make it easy to check what was just logged:

```python
def recent_entries(self, minutes: int = 10) -> list[dict]:
    """Get food entries logged in the last N minutes."""
```

**Use case for LLMs:**
```python
# Before retrying, check what's already logged
recent = tracker.recent_entries(minutes=5)
if any(e['name'].lower() == 'rice' for e in recent):
    print("Rice already logged, skipping")
```

---

### 5. Delete Entry (Cleanup Capability)

Expose entry deletion in the API:

```python
def delete_entry(self, timestamp: str) -> dict:
    """
    Delete a food entry by its timestamp.
    
    Returns:
        {"deleted": True, "entry": {...}}
        OR
        {"deleted": False, "reason": "not_found"}
    """

def delete_entries(self, timestamps: list[str]) -> dict:
    """Delete multiple entries. Returns count deleted."""
```

**Document in TOOL.md** so LLMs know they can clean up mistakes.

---

### 6. Update TOOL.md with Safe Patterns

Add a new section:

```markdown
## Safe Logging Patterns for LLM Agents

### Preventing Duplicates

The tracker has built-in duplicate detection. By default, logging the same 
food within 5 minutes returns the existing entry instead of creating a duplicate.

### Recommended Flow for Meal Logging

1. **Prefer `log_meal()` for multiple items** — atomic, with built-in deduplication
2. **Use `dry_run=True` to preview** — verify nutrition before committing
3. **Check `recent_entries()` before retrying** — avoid duplicates on retry

### If Duplicates Occur

Use `delete_entry(timestamp)` to clean up:
```python
tracker.delete_entry("2026-01-11T21:43:03.676963")
```

### Retry Pattern

```python
# DON'T: Blindly retry
for item in items:
    tracker.log_food(item)  # May create duplicates!

# DO: Check before retry
recent = tracker.recent_entries(minutes=5)
logged_names = {e['name'].lower() for e in recent}
for item in items:
    if item['name'].lower() not in logged_names:
        tracker.log_food(item)
```
```

---

## Implementation Priority

| Change | Impact | Effort | Priority |
|--------|--------|--------|----------|
| Duplicate detection (dedupe_window) | High | Low | **1** |
| Delete entry | High | Low | **2** |
| Recent entries helper | Medium | Low | **3** |
| Dry run mode | Medium | Low | **4** |
| Batch log_meal() | Medium | Medium | **5** |
| Update TOOL.md | High | Low | **1** |

---

## Summary

The core insight: **LLM-friendly APIs should be idempotent by default**. 

A human using a form clicks "submit" once. An LLM might call the same function 
multiple times during retries, error handling, or re-processing. The API should 
handle this gracefully rather than creating duplicates.

Default behavior should be:
- **Safe** — duplicates detected and prevented
- **Observable** — easy to check current state  
- **Reversible** — mistakes can be cleaned up
- **Explicit** — if you want to bypass safety, you opt-in (`dedupe_window_minutes=0`)
