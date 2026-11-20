#pragma once

#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QObject>
#include <QString>
#include <QUrl>
#include <QVariantList>

class NotifyClient final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString serverUrl READ serverUrl WRITE setServerUrl NOTIFY settingsChanged)
    Q_PROPERTY(QString apiToken READ apiToken WRITE setApiToken NOTIFY settingsChanged)
    Q_PROPERTY(QString topic READ topic WRITE setTopic NOTIFY settingsChanged)
    Q_PROPERTY(QVariantList messages READ messages NOTIFY messagesChanged)
    Q_PROPERTY(QString status READ status NOTIFY statusChanged)

public:
    explicit NotifyClient(QObject *parent = nullptr);

    QString serverUrl() const { return m_serverUrl; }
    QString apiToken() const { return m_apiToken; }
    QString topic() const { return m_topic; }
    QVariantList messages() const { return m_messages; }
    QString status() const { return m_status; }

    void setServerUrl(const QString &value);
    void setApiToken(const QString &value);
    void setTopic(const QString &value);

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void publish(const QString &title, const QString &body, int priority);

signals:
    void settingsChanged();
    void messagesChanged();
    void statusChanged();

private:
    bool ready();
    void setStatus(const QString &value);
    QNetworkRequest makeRequest(const QString &suffix) const;

    QString m_serverUrl = QStringLiteral("https://notify.example.com");
    QString m_apiToken;
    QString m_topic = QStringLiteral("general");
    QString m_status = QStringLiteral("Enter your server URL and token");
    QVariantList m_messages;
    QNetworkAccessManager m_network;
    bool m_loading = false;
};
