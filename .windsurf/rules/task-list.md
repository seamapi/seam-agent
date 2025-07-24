---
trigger: always_on
description: This is a rule for how to plan and execute work!
globs:
---

# Task List - Single Focus Workflow

## 🎯 Focus Rule
**ONLY WORK ON ONE TASK AT A TIME**
DO NOT UPDATE THIS FILE UPDATAE task.md for keeping track

## Workflow

1. **Select Task:** Choose ONE task from `task.md` with status TODO
2. **Mark In Progress:** Update the task status to IN_PROGRESS in `task.md`
3. **Update This File:** Record the active task above
4. **Work Iteratively:** Make small, focused changes
5. **Test Frequently:** Verify each change works as expected
6. **Complete Task:** Mark as COMPLETED when all acceptance criteria are met
7. **Clean Up:** Update both files before starting the next task

## Quick Commands

```bash
# To check current task status
grep -A 5 "IN_PROGRESS" task.md

# To see all TODO tasks
grep -B 2 -A 10 "Status.*TODO" task.md
```

## Reminders

- ✅ Follow the plan in `task.md`
- ✅ Check `docs/customer-support-agent-prd.md` for requirements
- ✅ Keep changes small and focused
- ✅ Don't modify unrelated code
- ✅ Test assumptions frequently
- ✅ Ask for help when uncertain
