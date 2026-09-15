# Releasing texaudit

Releases are published from GitHub to PyPI using Trusted Publishing. The
workflow uses short-lived credentials, so no PyPI API token should be stored in
the repository or in GitHub Actions secrets.

## One-time PyPI and GitHub configuration

The `texaudit` project already exists on PyPI. In its **Publishing** settings,
add a GitHub Trusted Publisher with these exact values:

- Owner: `thermok-SG`
- Repository: `texaudit`
- Workflow name: `release.yml`
- Environment name: `pypi`

In the GitHub repository settings, create an environment named `pypi`.
Requiring approval for that environment is recommended: it leaves a manual
confirmation between building a release and publishing it permanently.

After Trusted Publishing is configured and tested, revoke any account-wide
PyPI token used for the first manual release. A project-scoped token may be
created as an emergency fallback, but it is not needed by the workflow.

## Prepare a release

1. Update the version in both `pyproject.toml` and
   `src/texaudit/__init__.py`. PyPI versions cannot be overwritten or reused.
2. Update user-facing documentation when installation, commands, output, or
   supported profiles change.
3. Run the local checks:

   ```bash
   python -m pip install -e ".[dev]"
   pytest -q
   python -m build
   python -m twine check dist/*
   ```

4. Merge the release changes into `main` and ensure CI is clean.
5. On GitHub, create a new release from `main` with a tag exactly matching the
   package version, such as `v0.2.1`.
6. Publish the GitHub release. The `release.yml` workflow tests the project,
   verifies that the tag and package version match, builds one source archive
   and one wheel, checks their metadata, and publishes those exact artifacts to
   PyPI.
7. Confirm the release from a fresh environment:

   ```bash
   python -m pip install --upgrade texaudit
   texaudit --list-journals
   ```

If the workflow fails before the publish job, fix the problem and make a new
GitHub release attempt using the same tag only if nothing reached PyPI. If any
artifact was uploaded, increment the package version instead.
