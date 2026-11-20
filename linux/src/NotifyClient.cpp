#include "NotifyClient.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QRegularExpression>

NotifyClient::NotifyClient(QObject *parent) : QObject(parent) {}

void NotifyClient::setServerUrl(const QString &value) {
    if (m_serverUrl == value) return;
    m_serverUrl = value.trimmed();
    emit settingsChanged();
}
void NotifyClient::setApiToken(const QString &value) {
    if (m_apiToken == value) return;
    m_apiToken = value;
    emit settingsChanged();
}
void NotifyClient::setTopic(const QString &value) {
    if (m_topic == value) return;
    m_topic = value.trimmed();
    m_messages.clear();
    emit messagesChanged();
    emit settingsChanged();
    refresh();
}
void NotifyClient::setStatus(const QString &value) {
    if (m_status == value) return;
    m_status = value;
    emit statusChanged();
}

bool NotifyClient::ready() {
    const QUrl url(m_serverUrl);
    const bool local = url.host() == QStringLiteral("localhost")
                       || url.host() == QStringLiteral("127.0.0.1");
    const bool secure = url.scheme() == QStringLiteral("https")
                        || (local && url.scheme() == QStringLiteral("http"));
    static const QRegularExpression topicRe(QStringLiteral("^[A-Za-z0-9_-]{1,64}$"));
    if (!url.isValid() || !secure || url.host().isEmpty() ||
        !url.userInfo().isEmpty() || (url.path() != QString() && url.path() != QStringLiteral("/")) ||
        !url.query().isEmpty() || !url.fragment().isEmpty() ||
        !topicRe.match(m_topic).hasMatch() || m_apiToken.size() < 32) {
        setStatus(QStringLiteral("Use an HTTPS origin, a valid topic and a token of at least 32 characters"));
        return false;
    }
    return true;
}

QNetworkRequest NotifyClient::makeRequest(const QString &suffix) const {
    QUrl url(m_serverUrl);
    url.setPath(QStringLiteral("/api/v1/topics/") + m_topic + suffix);
    QNetworkRequest request(url);
    request.setRawHeader("Authorization", QByteArray("Bearer ") + m_apiToken.toUtf8());
    request.setRawHeader("Accept", "application/json");
    request.setTransferTimeout(12000);
    return request;
}

void NotifyClient::refresh() {
    if (m_loading || !ready()) return;
    m_loading = true;
    QNetworkRequest request = makeRequest(QStringLiteral("/messages"));
    // Set the query separately: QUrl::setPath encodes a literal '?'.
    QUrl url = request.url();
    url.setPath(QStringLiteral("/api/v1/topics/") + m_topic + QStringLiteral("/messages"));
    url.setQuery(QStringLiteral("limit=50"));
    request.setUrl(url);
    const QString requestedTopic = m_topic;
    auto *reply = m_network.get(request);
    connect(reply, &QNetworkReply::finished, this, [this, reply, requestedTopic]() {
        if (m_topic != requestedTopic) {
            m_loading = false;
            reply->deleteLater();
            refresh();
            return;
        }
        m_loading = false;
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray body = reply->readAll();
        const bool ok = reply->error() == QNetworkReply::NoError && status == 200;
        reply->deleteLater();
        if (!ok) {
            setStatus(QStringLiteral("Could not load notifications (HTTP %1)").arg(status));
            return;
        }
        const QJsonDocument document = QJsonDocument::fromJson(body);
        if (!document.isObject() || !document.object().value(QStringLiteral("messages")).isArray()) {
            setStatus(QStringLiteral("Unexpected server response"));
            return;
        }
        m_messages = document.object().value(QStringLiteral("messages")).toArray().toVariantList();
        emit messagesChanged();
        setStatus(QStringLiteral("Connected · showing latest topic notifications"));
    });
}

void NotifyClient::publish(const QString &title, const QString &body, int priority) {
    if (!ready()) return;
    if (body.trimmed().isEmpty() || body.size() > 4096 || title.size() > 160 ||
        priority < 1 || priority > 5) {
        setStatus(QStringLiteral("Message fields are outside allowed limits"));
        return;
    }
    QNetworkRequest request = makeRequest(QStringLiteral("/messages"));
    request.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    const auto payload = QJsonDocument(QJsonObject{
        {QStringLiteral("title"), title},
        {QStringLiteral("body"), body},
        {QStringLiteral("priority"), priority}
    }).toJson(QJsonDocument::Compact);
    auto *reply = m_network.post(request, payload);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const bool ok = reply->error() == QNetworkReply::NoError && status == 201;
        reply->deleteLater();
        if (!ok) {
            setStatus(QStringLiteral("Publish failed (HTTP %1)").arg(status));
            return;
        }
        setStatus(QStringLiteral("Notification published"));
        refresh();
    });
}
