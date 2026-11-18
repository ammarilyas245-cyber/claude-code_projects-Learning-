# Example Workflow Template

**Objective:** [What should this workflow accomplish?]

**Use Case:** [When would you run this?]

---

## Required Inputs

- Input 1: [description, format, where it comes from]
- Input 2: [description, format, where it comes from]
- API Key: [which `.env` variable]

---

## Workflow Steps

### Step 1: [Do something]
- **Tool:** `tools/[tool_name].py`
- **Input:** [what data/args]
- **Output:** [what gets produced]
- **Success Check:** [how do we know it worked?]

### Step 2: [Do next thing]
- **Tool:** `tools/[another_tool].py`
- **Input:** [output from step 1, plus...]
- **Output:** [intermediate result]
- **Success Check:** [validation]

### Step 3: [Deliver result]
- **Tool:** `tools/[delivery_tool].py`
- **Input:** [everything assembled]
- **Output:** [link to cloud service result]
- **Success Check:** [verify it's live]

---

## Edge Cases & Error Handling

| Scenario | Error Sign | Recovery |
|----------|-----------|----------|
| API rate limit hit | HTTP 429 | [What to do] |
| Missing input file | FileNotFoundError | [What to do] |
| Malformed data | ValueError | [What to do] |

---

## Success Criteria

- [ ] Output is created in [destination]
- [ ] Data quality check passes
- [ ] User can access the result
- [ ] No errors in the log

---

## Notes

- [Any quirks discovered about APIs, timing, or data]
- [Constraints that came up]
- [What we'll optimize next time]
