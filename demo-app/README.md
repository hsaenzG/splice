# demo-app (optional sample)

This folder is an **optional example** for workshops and first-run demos. Splice works on any project without it.

## Enable for demos

Add to `.splice/config.json`:

```json
{
  "errorSources": [".splice/last-error.log", "demo-app/UserList.tsx.error.log"],
  "extraFiles": ["demo-app/UserList.tsx"]
}
```

Or run:

```bash
python3 scripts/demo-dual-ide.py   # writes demo config automatically
```

## The bug

`UserList.tsx` calls `data.map()` but API returns `{ items: User[] }`.
