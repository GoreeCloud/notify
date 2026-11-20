#include "NotifyClient.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>

int main(int argc, char *argv[]) {
    QGuiApplication app(argc, argv);
    QGuiApplication::setApplicationName(QStringLiteral("GoreeCloud Notify"));
    QGuiApplication::setOrganizationName(QStringLiteral("GoreeCloud"));

    NotifyClient client;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("notify"), &client);
    engine.loadFromModule(QStringLiteral("GoreeCloud.Notify"), QStringLiteral("Main"));
    if (engine.rootObjects().isEmpty()) return 1;
    return app.exec();
}
