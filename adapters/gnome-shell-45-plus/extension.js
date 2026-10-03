import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

export default class MochiCompanionExtension extends Extension {
    enable() {
        const file = Gio.File.new_for_path(`${this.path}/anime_modes.json`);
        const [, contents] = file.load_contents(null);
        this._catalog = JSON.parse(new TextDecoder().decode(contents));
        this._sequence = ['neutral'];
        this._index = 0;
        this._ticks = 0;
        this._nextMoment = 8;

        this._indicator = new PanelMenu.Button(0.0, this.metadata.name, false);
        this._box = new St.BoxLayout({
            style: 'background-color: #000000; border-radius: 12px; padding: 0 18px; spacing: 52px; min-width: 184px;',
        });
        this._left = new St.Label({style: 'font-size: 30px; font-weight: 800;'});
        this._right = new St.Label({style: 'font-size: 30px; font-weight: 800;'});
        this._box.add_child(this._left);
        this._box.add_child(this._right);
        this._indicator.add_child(this._box);
        this._indicator.connect('button-press-event', (_actor, event) => {
            const button = event.get_button();
            this._sequence = button === Clutter.BUTTON_PRIMARY
                ? ['love', 'sparkle', 'love', 'happy']
                : button === Clutter.BUTTON_MIDDLE
                    ? ['blink', 'sleepy', 'sleepy', 'neutral']
                    : ['focused', 'rage', 'angry', 'neutral'];
            this._index = 0;
            this._ticks = this._sequence.length;
            this._render();
            return Clutter.EVENT_STOP;
        });
        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, 'center');
        this._render();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            this._step();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _step() {
        if (this._ticks > 0) {
            this._ticks--;
            if (this._ticks === 0) {
                this._sequence = ['neutral'];
                this._index = 0;
            } else {
                this._index = (this._index + 1) % this._sequence.length;
            }
        } else if (--this._nextMoment <= 0) {
            const modes = this._catalog.modes;
            const mode = modes[Math.floor(Math.random() * modes.length)];
            this._sequence = mode.sequence;
            this._index = 0;
            this._ticks = this._sequence.length;
            this._nextMoment = 12 + Math.floor(Math.random() * 13);
        }
        this._render();
    }

    _render() {
        const name = this._sequence[this._index] ?? 'neutral';
        const frame = this._catalog.frames[name] ?? this._catalog.frames.neutral;
        const color = frame[2];
        this._left.text = frame[0];
        this._right.text = frame[1];
        this._left.style = `font-size: 30px; font-weight: 800; color: ${color};`;
        this._right.style = `font-size: 30px; font-weight: 800; color: ${color};`;
    }

    disable() {
        if (this._timer) {
            GLib.Source.remove(this._timer);
            this._timer = null;
        }
        this._indicator?.destroy();
        this._indicator = null;
        this._catalog = null;
    }
}
