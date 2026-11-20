import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import GoreeCloud.Notify

ApplicationWindow {
    id: root
    visible: true
    width: 1100
    height: 760
    minimumWidth: 420
    minimumHeight: 520
    title: "GoreeCloud Notify"
    color: GoreeTokens.canvas

    property bool compact: width < 820

    Timer {
        interval: 20000
        repeat: true
        running: true
        onTriggered: notify.refresh()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        RowLayout {
            Layout.fillWidth: true
            spacing: 14
            Rectangle {
                width: 52; height: 52; radius: 18
                color: GoreeTokens.brand
                Label { anchors.centerIn: parent; text: "N"; color: GoreeTokens.onBrand; font.pixelSize: 26; font.bold: true }
            }
            Column {
                spacing: 2
                Label { text: "GoreeCloud Notify"; font.pixelSize: 25; font.bold: true; color: GoreeTokens.text }
                Label { text: "Private, self-hosted notifications"; color: GoreeTokens.softText }
            }
            Item { Layout.fillWidth: true }
            Button { text: "Refresh"; enabled: notify.apiToken.length >= 32; onClicked: notify.refresh() }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: settings.implicitHeight + 32
            color: GoreeTokens.surface
            radius: 18
            border.color: GoreeTokens.outline
            ColumnLayout {
                id: settings
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 12
                Label { text: "Connection"; font.bold: true; font.pixelSize: 18; color: GoreeTokens.text }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    ColumnLayout {
                        Layout.fillWidth: true
                        Label { text: "Server URL"; color: GoreeTokens.softText }
                        TextField {
                            Layout.fillWidth: true
                            text: notify.serverUrl
                            Accessible.name: "Server URL"
                            onEditingFinished: notify.serverUrl = text
                            placeholderText: "https://notify.example.com"
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Label { text: "API token (memory only)"; color: GoreeTokens.softText }
                        TextField {
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            Accessible.name: "API token"
                            placeholderText: "Private API token"
                            onTextChanged: notify.apiToken = text
                        }
                    }
                    ColumnLayout {
                        Layout.preferredWidth: 170
                        Label { text: "Topic"; color: GoreeTokens.softText }
                        TextField {
                            Layout.fillWidth: true
                            text: notify.topic
                            Accessible.name: "Topic"
                            onEditingFinished: notify.topic = text
                        }
                    }
                }
                Label {
                    text: notify.status
                    color: GoreeTokens.softText
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                    Accessible.role: Accessible.StaticText
                }
            }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: root.compact ? Qt.Vertical : Qt.Horizontal

            Rectangle {
                SplitView.preferredWidth: 420
                SplitView.preferredHeight: 320
                SplitView.minimumWidth: 280
                color: GoreeTokens.surface
                radius: 18
                border.color: GoreeTokens.outline
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12
                    Label { text: "New notification"; font.pixelSize: 21; font.bold: true; color: GoreeTokens.text }
                    Label { text: "Title (optional)"; color: GoreeTokens.softText }
                    TextField { id: noticeTitle; Layout.fillWidth: true; maximumLength: 160; placeholderText: "Service update"; Accessible.name: "Notification title" }
                    Label { text: "Message"; color: GoreeTokens.softText }
                    TextArea {
                        id: noticeBody
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        wrapMode: TextArea.Wrap
                        placeholderText: "What should your devices know?"
                        Accessible.name: "Notification message"
                    }
                    Label { text: "Priority"; color: GoreeTokens.softText }
                    ComboBox {
                        id: noticePriority
                        Layout.fillWidth: true
                        model: ["Minimum", "Low", "Default", "High", "Urgent"]
                        currentIndex: 2
                        Accessible.name: "Notification priority"
                    }
                    Button {
                        Layout.fillWidth: true
                        text: "Publish notification"
                        enabled: noticeBody.text.trim().length > 0 && notify.apiToken.length >= 32
                        onClicked: {
                            notify.publish(noticeTitle.text, noticeBody.text, noticePriority.currentIndex + 1)
                            noticeTitle.clear()
                            noticeBody.clear()
                        }
                    }
                }
            }
            Rectangle {
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                color: GoreeTokens.surface
                radius: 18
                border.color: GoreeTokens.outline
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Inbox"; font.pixelSize: 21; font.bold: true; color: GoreeTokens.text }
                        Item { Layout.fillWidth: true }
                        Label { text: notify.messages.length + " recent"; color: GoreeTokens.softText }
                    }
                    Label {
                        visible: notify.messages.length === 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        text: "Connect to a topic or publish a message to get started."
                        color: GoreeTokens.softText
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        wrapMode: Text.Wrap
                    }
                    ListView {
                        visible: notify.messages.length > 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 12
                        model: notify.messages
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            implicitHeight: details.implicitHeight + 24
                            radius: 12
                            color: GoreeTokens.tonal
                            ColumnLayout {
                                id: details
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: 12
                                Label { text: "Priority " + modelData.priority; color: GoreeTokens.softText }
                                Label { visible: !!modelData.title; text: modelData.title || ""; font.bold: true; color: GoreeTokens.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                Label { text: modelData.body; color: GoreeTokens.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }
        }
    }
}
