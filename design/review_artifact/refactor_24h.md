# Refactoring: time_window_hours 12 → 24

## Background

Japanese RSS feeds (assets.wor.jp) round `updated` timestamps to `00:00:00 JST`, causing articles to appear older than they actually are. With a 12-hour window, these articles are filtered out. Changing to a 24-hour window ensures Japanese feed articles are included.

## Changes Required

All changes are simple value replacements of `12` → `24` for `time_window_hours` and related display strings. No logic changes are needed.

---

### 1. `config.yaml` (line 10)

Change default `time_window_hours` from `12` to `24`.

```yaml
# Before
schedule:
  interval_hours: 12
  time_window_hours: 12

# After
schedule:
  interval_hours: 24
  time_window_hours: 24
```

Both `interval_hours` and `time_window_hours` should be changed to 24 to keep them consistent (the interval defines how often the pipeline runs, the window defines how far back to look).

---

### 2. `src/config.py` (lines 104-105)

Change the default fallback values from `12` to `24`.

```python
# Before (line 104-105)
            interval_hours=int(schedule.get("interval_hours", 12)),
            time_window_hours=int(schedule.get("time_window_hours", 12)),

# After
            interval_hours=int(schedule.get("interval_hours", 24)),
            time_window_hours=int(schedule.get("time_window_hours", 24)),
```

---

### 3. `templates/email.html` (line 75)

Update the "no articles" message to say 24 hours.

```html
<!-- Before -->
    <p>No articles found in the last 12 hours.</p>

<!-- After -->
    <p>No articles found in the last 24 hours.</p>
```

---

### 4. `README.md` (lines 71, 107)

Update documentation references.

```markdown
# Before (line 71)
| `schedule.time_window_hours` | 12 | 取得する記事の時間範囲 (時間) |

# After
| `schedule.time_window_hours` | 24 | 取得する記事の時間範囲 (時間) |
```

```markdown
# Before (line 107)
# 初回実行: 過去12時間の全記事を取得してHTMLだけ確認

# After
# 初回実行: 過去24時間の全記事を取得してHTMLだけ確認
```

Also update the cron example (line 115-123) from twice daily to once daily:

```markdown
# Before
毎日 6:00 と 18:00 に実行する例:
0 6,18 * * * cd /path/to/news_filtering && ...

# After
毎日 6:00 に実行する例:
0 6 * * * cd /path/to/news_filtering && ...
```

---

### 5. `tests/test_config.py` (lines 16-17, 49)

Update the YAML fixture and assertion.

```python
# Before (line 16-17 in _base_yaml)
          interval_hours: 12
          time_window_hours: 12

# After
          interval_hours: 24
          time_window_hours: 24
```

```python
# Before (line 49)
    assert cfg.schedule.time_window_hours == 12

# After
    assert cfg.schedule.time_window_hours == 24
```

---

### 6. `tests/test_integration.py` (lines 24, 69)

Update ScheduleConfig values and filter call.

```python
# Before (line 24)
        schedule=ScheduleConfig(interval_hours=12, time_window_hours=12),

# After
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
```

```python
# Before (line 69)
        time_window_hours=12,

# After
        time_window_hours=24,
```

---

### 7. `tests/test_deduplicator.py` (lines 31, 164)

Update ScheduleConfig values.

```python
# Before (line 31)
        schedule=ScheduleConfig(interval_hours=12, time_window_hours=12),

# After
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
```

```python
# Before (line 164)
        schedule=ScheduleConfig(interval_hours=12, time_window_hours=12),

# After
        schedule=ScheduleConfig(interval_hours=24, time_window_hours=24),
```

---

### 8. `tests/test_time_filter.py` (line 69)

Update compute_cutoff test.

```python
# Before (line 69)
    cutoff = compute_cutoff(time_window_hours=12, last_run=last_run, force=False)

# After
    cutoff = compute_cutoff(time_window_hours=24, last_run=last_run, force=False)
```

---

## Files Changed (summary)

| File | Lines | Change |
|---|---|---|
| `config.yaml` | 9-10 | `12` → `24` |
| `src/config.py` | 104-105 | default `12` → `24` |
| `templates/email.html` | 75 | "12 hours" → "24 hours" |
| `README.md` | 71, 107, 115-123 | docs update |
| `tests/test_config.py` | 16-17, 49 | `12` → `24` |
| `tests/test_integration.py` | 24, 69 | `12` → `24` |
| `tests/test_deduplicator.py` | 31, 164 | `12` → `24` |
| `tests/test_time_filter.py` | 69 | `12` → `24` |

## Verification

After changes, run:
```bash
source venv/bin/activate && pytest tests/ -v
```

All 54 tests should pass with no modifications to test logic (only constant values change).
