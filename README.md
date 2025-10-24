# sodmaster

The Sodmaster Corporation

## Deployment notes

- Render uses the Python version pinned in `runtime.txt`. Update that file when
  the runtime needs to change.
- Configure the Render service (or your chosen host) with the `GIT_SHA`,
  `BUILD_TIME`, and `PY_RUNTIME` environment variables so the `/version` endpoint
  can expose accurate build metadata. The deploy workflow also publishes
  `app/version_env.json` as an artifact that can be mounted for offline
  environments.
- The marketing site under `app/site` is built with Astro for Render Static.
  - Set the `SITE_URL` environment variable to the final public hostname.
  - Use `cd app/site && npm install && npm run build` as the build command.
  - Publish the contents of `app/site/dist`.
