# GoreeCloud Notify CLI — developer preview

The terminal client is **additional** to the native GTK desktop app. It uses
existing Python ntfy protocol and health modules plus the same OS keyring as
the desktop client. It does **not** configure server-side ntfy users, tokens,
ACLs, public networking, or a new backend.

## Install (developer checkout)

```sh
python3 -m pip install --user -e .
goreecloud-notify-cli --help
# Or, without installation:
python3 -m goreecloud_notify.cli --help
```

The installed GTK application remains `goreecloud-notify`. This CLI is a
separate executable `goreecloud-notify-cli` with no GTK runtime import.

## Common commands

```sh
goreecloud-notify-cli config set-server https://YOUR-PRIVATE-NTFY-ENDPOINT
goreecloud-notify-cli config show
goreecloud-notify-cli topics add system-alerts
goreecloud-notify-cli topics list
goreecloud-notify-cli auth set             # prompts without echo and stores in OS keyring
goreecloud-notify-cli auth status          # reveals only whether token exists
goreecloud-notify-cli health --json
goreecloud-notify-cli subscribe system-alerts --since 10m --count 10
printf '%s\n' 'Synthetic notification' | goreecloud-notify-cli publish system-alerts --priority 3
goreecloud-notify-cli auth clear
```

Option `--server` may precede the command for a one-off endpoint override.
`--anonymous` skips the OS keyring for that command. HTTP is accepted only for
local loopback endpoints; remote connections require HTTPS. Never put an ntfy
bearer token in a shell command, process argument, URL, history file, CI log,
or public Git repository. There is deliberately no `--token` option.

The CLI reads sensitive messages from stdin when the positional message is
omitted. Positional message arguments may appear in the shell history or
process list; prefer stdin for sensitive content. `subscribe` emits JSON Lines
to stdout, which can contain private message bodies. Redirect output to files
only when the destination and its retention policy are explicitly authorized.

## Exit codes

- `0` — command succeeded or a health probe returned healthy.
- `1` — health endpoint explicitly returned unhealthy.
- `2` — connection/configuration/auth/validation error.
- `130` — subscription interrupted with Ctrl+C.

The CLI does not retry connections automatically; automation should implement
bounded retries with appropriate access controls. An HTTP 401/403 indicates
missing credentials or permission, not a reason to disable ntfy ACLs.

## Acceptance status

Developer preview until committed to `GoreeCloud/notify`, CI-tested and
packaged. A local unit-test pass does not demonstrate authenticated publishing,
end-to-end subscription, release quality, or verified VPS installation.
