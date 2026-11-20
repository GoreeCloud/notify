cmake_minimum_required(VERSION 3.26)
project(GoreeCloudNotify VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 6.12 REQUIRED COMPONENTS Quick QuickControls2 Network)
qt_standard_project_setup(REQUIRES 6.12)

qt_add_executable(goreecloud-notify
    src/main.cpp
    src/NotifyClient.h
    src/NotifyClient.cpp
)

qt_add_qml_module(goreecloud-notify
    URI GoreeCloud.Notify
    VERSION 1.0
    QML_FILES
        qml/Main.qml
        qml/GoreeTokens.qml
)

target_link_libraries(goreecloud-notify PRIVATE
    Qt6::Quick
    Qt6::QuickControls2
    Qt6::Network
)

install(TARGETS goreecloud-notify
    BUNDLE DESTINATION .
    RUNTIME DESTINATION bin
)
