# -*- coding: utf-8 -*-
from collections import deque
from datetime import datetime
import os
import sys

import click
from pydub import AudioSegment
import pyperclip
import urwid
import vlc


PALETTE = [
    ('normal', 'black', 'light gray'),
    ('complete', 'black', 'dark red'),
]


class TimeSlider(urwid.ProgressBar):

    def get_text(self):
        return format_dt(self.current)


@click.command()
@click.option('--anki-media', envvar='ANKI_MEDIA')
@click.argument('filepath')
def main(anki_media, filepath):
    audio = AudioSegment.from_file(filepath)
    marks = deque([0, 0], 2)
    player = vlc.MediaPlayer(filepath)
    slider = TimeSlider('normal', 'complete', current=0, done=len(audio))
    display = urwid.Text('', align='center')
    pile = urwid.Pile([slider, display])
    filler = urwid.Filler(pile)

    ctx = {
        'anki_media': anki_media,
        'audio':audio,
        'marks': marks,
        'player': player,
        'slider': slider,
        'display': display,
        'cut_player': None,
    }

    handler = input_handler(ctx)
    loop = urwid.MainLoop(filler, PALETTE, unhandled_input=handler)
    player.play()

    player.get_instance().log_unset()
    tick(loop, ctx)
    loop.run()


def tick(loop, ctx):
    marks = ctx['marks']
    player = ctx['player']
    slider = ctx['slider']
    display = ctx['display']
    t = max(player.get_time(), 0)
    slider.current = t
    display.set_text('%s - %s' % tuple(format_dt(x) for x in lr(marks)))
    loop.set_alarm_in(0.5, tick, ctx)


def input_handler(ctx):
    anki_media = ctx['anki_media']
    audio = ctx['audio']
    marks = ctx['marks']
    player = ctx['player']
    slider = ctx['slider']

    def seek(s):
        ms = player.get_time() + (s * 1000)
        t = min(max(ms, 0), len(audio))
        player.set_time(t)

    def mark():
        marks.append(player.get_time())

    def cut():
        l, r = lr(marks)
        audio_slice = audio[l:r]
        now = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = now + '.mp3'
        filepath = os.path.join(anki_media, filename)
        audio_slice.export(filepath, format='mp3')
        anki_sound_field = '[sound:%s]' % filename
        pyperclip.copy(anki_sound_field)

    def handle(key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        if key is ' ':
            player.pause()
        if key is 'j':
            seek(-3)
        if key is 'J':
            seek(-10)
        if key is 'k':
            mark()
        if key is 'l':
            seek(3)
        if key is 'L':
            seek(10)
        if key is 'enter':
            cut()

    return handle


def format_dt(ms):
    raw = ms // 1000
    r, s = divmod(raw, 60)
    h, m = divmod(r, 60)
    return '%02d:%02d:%02d' % (h, m, s)


def lr(marks):
    a, b = marks
    l, r = min(a, b), max(a, b)
    return l, r


if __name__ == "__main__":
    main()
