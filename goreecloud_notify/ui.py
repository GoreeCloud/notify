"""GoreeCloud Notify native GTK4/libadwaita UI (Linux development preview)."""
from __future__ import annotations

import datetime as dt
import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from .core import NtfyClient, Notification, NotifyError, normalize_server, validate_topic
from .storage import load_settings, load_token, save_settings, save_token
from .worker import SubscriptionManager

APP_ID = "com.goreecloud.Notify"
CSS = """
window { background: @window_bg_color; }
.notify-sidebar { background: alpha(@accent_bg_color, 0.045); padding: 16px 10px; }
.notify-brand { font-weight: 800; font-size: 17px; }
.notify-overline { opacity: .65; font-size: 11px; font-weight: 700; }
.notify-title { font-size: 24px; font-weight: 800; }
.notify-status { font-size: 12px; opacity: .7; }
.notify-row { border-radius: 14px; padding: 12px; margin: 5px 2px; }
.notify-row:selected { background: alpha(@accent_bg_color, .16); }
.notify-card { background: @card_bg_color; border-radius: 16px; padding: 18px;
               margin: 6px 12px; }
.notify-card-title { font-weight: 750; font-size: 15px; }
.notify-card-body { opacity: .9; }
.notify-muted { opacity: .62; font-size: 12px; }
.notify-urgent { color: #d4504e; font-weight: bold; }
.notify-compose { padding: 12px; }
"""


def label(text: str, css: str = "", wrap: bool = False) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=0, wrap=wrap)
    if css:
        widget.add_css_class(css)
    return widget


class NotifyWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="GoreeCloud Notify", default_width=1050, default_height=710)
        self.settings = {"server": "", "topics": []}
        self.connection_generation = 0
        self.messages: dict[str, list[Notification]] = {}
        self.statuses: dict[str, str] = {}
        self.rows: dict[Gtk.ListBoxRow, str] = {}
        self.selected_topic: str | None = None
        self.manager = SubscriptionManager(
            lambda n: GLib.idle_add(self._received, n),
            lambda topic, state: GLib.idle_add(self._status, topic, state),
        )
        self.connect("close-request", self._close)
        overlay = Adw.ToastOverlay()
        self.overlay = overlay
        toolbar = Adw.ToolbarView()
        overlay.set_child(toolbar)
        header = Adw.HeaderBar()
        name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name.append(Gtk.Image.new_from_icon_name("mail-unread-symbolic"))
        name.append(label("GoreeCloud Notify", "notify-brand"))
        header.set_title_widget(name)
        setup = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Connection settings")
        setup.connect("clicked", self._configure)
        add = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Subscribe to a topic")
        add.connect("clicked", self._add_topic)
        remove = Gtk.Button(icon_name="list-remove-symbolic", tooltip_text="Unsubscribe from selected topic")
        remove.connect("clicked", self._remove_topic)
        compose = Gtk.Button(label="New message")
        compose.add_css_class("suggested-action")
        compose.connect("clicked", self._compose)
        header.pack_end(compose)
        header.pack_end(add)
        header.pack_end(remove)
        header.pack_end(setup)
        toolbar.add_top_bar(header)

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        toolbar.set_content(split)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.add_css_class("notify-sidebar")
        sidebar.set_size_request(250, -1)
        split.append(sidebar)
        sidebar.append(label("YOUR TOPICS", "notify-overline"))
        self.topic_list = Gtk.ListBox()
        self.topic_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.topic_list.add_css_class("navigation-sidebar")
        self.topic_list.connect("row-selected", self._select_row)
        sidebar_scroller = Gtk.ScrolledWindow(vexpand=True)
        sidebar_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroller.set_child(self.topic_list)
        sidebar.append(sidebar_scroller)
        self.server_label = label("No server configured", "notify-status", True)
        sidebar.append(self.server_label)
        split.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main.set_hexpand(True)
        split.append(main)
        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        heading.set_margin_start(25)
        heading.set_margin_end(25)
        heading.set_margin_top(20)
        heading.set_margin_bottom(12)
        self.heading = label("Notifications", "notify-title")
        self.subtitle = label("Private by design · Powered by ntfy", "notify-muted")
        heading.append(self.heading)
        heading.append(self.subtitle)
        main.append(heading)
        self.stack = Gtk.Stack(vexpand=True, hexpand=True)
        self.empty = Adw.StatusPage(
            icon_name="mail-unread-symbolic", title="Your updates, in one place",
            description="Configure your ntfy server and subscribe to a topic to get started.",
        )
        empty_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.CENTER)
        cta = Gtk.Button(label="Get started")
        cta.add_css_class("suggested-action")
        cta.connect("clicked", self._configure)
        empty_actions.append(cta)
        self.empty.set_child(empty_actions)
        self.stack.add_named(self.empty, "empty")
        scroller = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.message_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.message_list.set_margin_bottom(24)
        scroller.set_child(self.message_list)
        self.stack.add_named(scroller, "messages")
        main.append(self.stack)
        self._refresh()
        try:
            self.settings = load_settings()
        except NotifyError as exc:
            self._toast(str(exc))
        self._refresh()
        if self.settings["server"] and self.settings["topics"]:
            self._restart()

    def _toast(self, message: str):
        self.overlay.add_toast(Adw.Toast.new(message))

    def _refresh(self):
        row = self.topic_list.get_first_child()
        while row is not None:
            next_row = row.get_next_sibling()
            self.topic_list.remove(row)
            row = next_row
        self.rows.clear()
        for topic in self.settings["topics"]:
            item = Gtk.ListBoxRow()
            item.add_css_class("notify-row")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.append(label("# " + topic, "notify-card-title"))
            box.append(label(self.statuses.get(topic, "Not connected"), "notify-muted"))
            item.set_child(box)
            self.rows[item] = topic
            self.topic_list.append(item)
            if self.selected_topic == topic:
                self.topic_list.select_row(item)
        if self.settings["topics"] and self.selected_topic not in self.settings["topics"]:
            self.selected_topic = self.settings["topics"][0]
            self.topic_list.select_row(next(iter(self.rows)))
        self.server_label.set_text(self.settings["server"] or "No server configured")
        self._render_messages()

    def _select_row(self, _list, row):
        if row is not None and row in self.rows:
            self.selected_topic = self.rows[row]
            self._render_messages()

    def _render_messages(self):
        row = self.message_list.get_first_child()
        while row is not None:
            next_row = row.get_next_sibling()
            self.message_list.remove(row)
            row = next_row
        topic = self.selected_topic
        if not topic:
            self.stack.set_visible_child_name("empty")
            self.heading.set_text("Notifications")
            self.subtitle.set_text("Set up a private ntfy connection to begin")
            return
        self.heading.set_text("# " + topic)
        notes = self.messages.get(topic, [])
        self.subtitle.set_text(self.statuses.get(topic, "Waiting for connection") + " · " + str(len(notes)) + " in this session")
        self.stack.set_visible_child_name("messages")
        if not notes:
            state = Adw.StatusPage(
                icon_name="mail-read-symbolic", title="Nothing here yet",
                description="New notifications will appear automatically. Use New message to send a test.",
            )
            self.message_list.append(state)
        for note in reversed(notes):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("notify-card")
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            top.append(label(note.title or "Notification", "notify-card-title"))
            top.append(Gtk.Box(hexpand=True))
            timestamp = dt.datetime.fromtimestamp(note.time, dt.timezone.utc).astimezone().strftime("%b %d, %H:%M") if note.time else "Now"
            top.append(label(timestamp, "notify-muted"))
            card.append(top)
            body = label(note.message, "notify-card-body", True)
            body.set_selectable(True)
            card.append(body)
            if note.priority >= 4 or note.tags:
                details = ("High priority · " if note.priority >= 4 else "") + "  ".join(note.tags)
                card.append(label(details, "notify-urgent" if note.priority >= 4 else "notify-muted"))
            self.message_list.append(card)

    def _status(self, topic: str, state: str, epoch: int):
        if epoch != self.connection_generation:
            return False
        if topic in self.settings["topics"]:
            if self.statuses.get(topic) != state:
                self.statuses[topic] = state
                self._refresh()
        return False

    def _received(self, note: Notification, epoch: int):
        if epoch != self.connection_generation:
            return False
        if note.topic not in self.settings["topics"]:
            return False
        items = self.messages.setdefault(note.topic, [])
        if note.id not in {item.id for item in items}:
            items.append(note)
            del items[:-200]  # Bounded in-memory history; never written to disk.
            if self.selected_topic == note.topic:
                self._render_messages()
            if note.priority == 5:
                self._toast("Urgent: " + (note.title or note.topic))
        return False

    def _restart(self):
        self.connection_generation += 1
        self.manager.stop()
        epoch = self.connection_generation
        self.manager.on_message = lambda n: GLib.idle_add(self._received, n, epoch)
        self.manager.on_status = lambda topic, state: GLib.idle_add(self._status, topic, state, epoch)
        if not self.settings["server"] or not self.settings["topics"]:
            return
        try:
            token = load_token(self.settings["server"])
            self.manager.start(self.settings["server"], self.settings["topics"], token)
        except NotifyError as exc:
            self._toast(str(exc))

    def _configure(self, *_):
        dialog = Adw.MessageDialog.new(self, "Connection settings", "Use an HTTPS ntfy endpoint. HTTP is allowed only for loopback development.")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        server = Gtk.Entry(text=self.settings["server"], placeholder_text="https://ntfy.example.org")
        server.set_tooltip_text("Server URL can include an ntfy reverse-proxy path")
        token = Gtk.PasswordEntry(placeholder_text="Access token (leave unchanged if empty)")
        box.append(label("SERVER URL", "notify-overline"))
        box.append(server)
        box.append(label("BEARER ACCESS TOKEN", "notify-overline"))
        box.append(token)
        box.append(label("Credentials are saved only in your operating system keyring.", "notify-muted", True))
        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save connection")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        def changed(_dlg, response):
            if response != "save":
                return
            try:
                new_server = normalize_server(server.get_text())
                new_token = token.get_text()
                if new_token:
                    save_token(new_server, new_token)
                old = self.settings["server"]
                self.settings["server"] = new_server
                save_settings(self.settings)
                if old != new_server:
                    self.messages.clear()
                    self.statuses.clear()
                self._restart()
                self._refresh()
            except NotifyError as exc:
                self._toast(str(exc))
        dialog.connect("response", changed)
        dialog.present()

    def _add_topic(self, *_):
        if not self.settings["server"]:
            self._configure()
            return
        dialog = Adw.MessageDialog.new(self, "Subscribe to a topic", "Choose a hard-to-guess topic name unless the server enforces access controls.")
        entry = Gtk.Entry(placeholder_text="system-alerts")
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Subscribe")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        def added(_dlg, response):
            if response != "add":
                return
            try:
                topic = validate_topic(entry.get_text())
                if topic not in self.settings["topics"]:
                    self.settings["topics"].append(topic)
                    save_settings(self.settings)
                self.selected_topic = topic
                self._refresh()
                self._restart()
            except NotifyError as exc:
                self._toast(str(exc))
        dialog.connect("response", added)
        dialog.present()

    def _remove_topic(self, *_):
        topic = self.selected_topic
        if not topic:
            self._toast("Select a topic to unsubscribe")
            return
        dialog = Adw.MessageDialog.new(
            self, "Unsubscribe from #" + topic,
            "Stop receiving this topic and clear its in-memory history on this device. "
            "This does not delete server-side messages.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Unsubscribe")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)

        def removed(_dlg, response):
            if response != "remove":
                return
            try:
                updated = {**self.settings, "topics": [t for t in self.settings["topics"] if t != topic]}
                save_settings(updated)
                self.settings = updated
                self.messages.pop(topic, None)
                self.statuses.pop(topic, None)
                self.selected_topic = updated["topics"][0] if updated["topics"] else None
                self._restart()
                self._refresh()
            except NotifyError as exc:
                self._toast(str(exc))

        dialog.connect("response", removed)
        dialog.present()

    def _compose(self, *_):
        if not self.selected_topic or not self.settings["server"]:
            self._toast("Choose a server and topic before publishing")
            return
        dialog = Adw.MessageDialog.new(self, "New notification", "Publish to # " + self.selected_topic)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        title = Gtk.Entry(placeholder_text="Optional title")
        body = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=8, bottom_margin=8)
        body.set_size_request(420, 120)
        priority = Gtk.DropDown.new_from_strings(["Min", "Low", "Default", "High", "Urgent"])
        priority.set_selected(2)
        tags = Gtk.Entry(placeholder_text="Optional tags: backup,success")
        content.append(title)
        content.append(body)
        content.append(priority)
        content.append(tags)
        dialog.set_extra_child(content)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("send", "Send")
        dialog.set_response_appearance("send", Adw.ResponseAppearance.SUGGESTED)
        def send(_dlg, response):
            if response != "send":
                return
            buffer = body.get_buffer()
            message = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
            topic, server = self.selected_topic, self.settings["server"]
            draft_title = title.get_text()
            draft_priority = priority.get_selected() + 1
            draft_tags = tags.get_text()
            try:
                token = load_token(server)
                client = NtfyClient(server, token)
                # Publishing must not block the GTK UI.
                def work():
                    try:
                        client.publish(topic, message, title=draft_title, priority=draft_priority, tags=draft_tags)
                        GLib.idle_add(self._toast, "Notification sent")
                    except NotifyError as exc:
                        GLib.idle_add(self._toast, str(exc))
                threading.Thread(target=work, daemon=True).start()
            except NotifyError as exc:
                self._toast(str(exc))
        dialog.connect("response", send)
        dialog.present()

    def _close(self, *_):
        self.manager.stop()
        return False


class NotifyApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = NotifyWindow(self)
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS.encode())
            Gtk.StyleContext.add_provider_for_display(
                self.window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        self.window.present()


def main(argv=None):
    app = NotifyApplication()
    return app.run(argv)
