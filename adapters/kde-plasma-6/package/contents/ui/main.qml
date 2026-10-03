import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore

PlasmoidItem {
    id: root
    preferredRepresentation: fullRepresentation

    property var catalog: ({"frames": {"neutral": ["●", "●", "#FFFFFF"]}, "modes": []})
    property var sequence: ["neutral"]
    property int sequenceIndex: 0
    property int ticksRemaining: 0
    property int nextMoment: 8

    implicitWidth: 220
    implicitHeight: 36

    Component.onCompleted: {
        const xhr = new XMLHttpRequest()
        xhr.open("GET", Qt.resolvedUrl("../data/anime_modes.json"))
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 0)
                root.catalog = JSON.parse(xhr.responseText)
        }
        xhr.send()
    }

    Timer {
        interval: 1500
        repeat: true
        running: true
        onTriggered: {
            if (root.ticksRemaining > 0) {
                root.ticksRemaining--
                if (root.ticksRemaining === 0) {
                    root.sequence = ["neutral"]
                    root.sequenceIndex = 0
                } else {
                    root.sequenceIndex = (root.sequenceIndex + 1) % root.sequence.length
                }
            } else if (--root.nextMoment <= 0 && root.catalog.modes.length > 0) {
                const mode = root.catalog.modes[Math.floor(Math.random() * root.catalog.modes.length)]
                root.sequence = mode.sequence
                root.sequenceIndex = 0
                root.ticksRemaining = root.sequence.length
                root.nextMoment = 8 + Math.floor(Math.random() * 9)
            }
        }
    }

    fullRepresentation: Rectangle {
        color: "#000000"
        radius: 12
        implicitWidth: 220
        implicitHeight: 36

        RowLayout {
            anchors.centerIn: parent
            spacing: 52

            Repeater {
                model: 2
                delegate: Text {
                    required property int index
                    readonly property var frame: root.catalog.frames[root.sequence[root.sequenceIndex]] || root.catalog.frames.neutral
                    text: frame[index]
                    color: frame[2]
                    font.pixelSize: 30
                    font.bold: true
                    font.family: "DejaVu Sans"
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.MiddleButton
            onClicked: mouse => {
                root.sequence = mouse.button === Qt.LeftButton
                    ? ["love", "sparkle", "love", "happy"]
                    : ["blink", "sleepy", "sleepy", "neutral"]
                root.sequenceIndex = 0
                root.ticksRemaining = root.sequence.length
            }
        }
    }
}
