# Packaging

The files under `packages/` are maintainers' starters, not prebuilt binaries.

## Release checklist

1. Update versions in adapter manifests and `CHANGELOG.md`.
2. Run `python3 -m unittest discover -s tests -v`.
3. Run `python3 portable/mochi_companion.py --smoke-test`.
4. Run `bash -n install.sh uninstall.sh scripts/detect-environment.sh`.
5. Test native adapters in disposable KDE Plasma and GNOME sessions.
6. Build distribution packages in clean containers or VMs.
7. Create a source archive excluding `.git`, caches, and local test output.

## GitHub

Initialize and push when ready:

```text
git init
git add .
git commit -m "Initial stable release"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

Do not publish compatibility claims as fully tested until each row in `COMPATIBILITY.md` has a recorded runtime result.
