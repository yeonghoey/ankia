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
    instance = vlc.Instance()
    main_player = instance.media_player_new(filepath)
    chop_player = instance.media_player_new()

    audio = AudioSegment.from_file(filepath)
    marks = deque([0, 0], 2)

    main_display = urwid.Text(filepath)
    divider1 = urwid.Divider()
    time_slider = TimeSlider('normal', 'complete', current=0, done=len(audio))
    divider2 = urwid.Divider()
    mark_display = urwid.Text('')
    chop_display = urwid.Text('')

    pile = urwid.Pile([
        main_display,
        divider1,
        time_slider,
        divider2,
        mark_display,
        chop_display])

    filler = urwid.Filler(urwid.Padding(pile, width=80, left=4), 'top')

    ctx = {
        'anki_media': anki_media,
        'audio':audio,
        'marks': marks,
        'main_player': main_player,
        'chop_player': chop_player,

        'main_display': main_display,
        'time_slider': time_slider,
        'mark_display': mark_display,
        'chop_display': chop_display,
    }

    handler = input_handler(ctx)
    loop = urwid.MainLoop(filler, PALETTE, unhandled_input=handler)
    main_player.play()

    main_player.get_instance().log_unset()
    loop.set_alarm_in(0.5, tick, ctx)
    loop.run()


def tick(loop, ctx):
    marks = ctx['marks']
    main_player = ctx['main_player']
    time_slider = ctx['time_slider']
    mark_display = ctx['mark_display']
    t = max(main_player.get_time(), 0)
    time_slider.current = t
    mark_display.set_text('%s - %s' % tuple(format_dt(x) for x in lr(marks)))
    loop.set_alarm_in(0.333, tick, ctx)
    loop.screen.clear()


def input_handler(ctx):
    anki_media = ctx['anki_media']
    audio = ctx['audio']
    marks = ctx['marks']
    main_player = ctx['main_player']
    chop_player = ctx['chop_player']
    time_slider = ctx['time_slider']

    def toggle():
        if main_player.is_playing():
            pause(main_player)
        else:
            if chop_player.is_playing():
                chop_player.stop()
            play(main_player)

    def seek(s):
        t = offset(main_player.get_time(), (s * 1000))
        main_player.set_time(t)

    def offset(t, os):
        return min(max(t + os, 0), len(audio))

    def mark():
        marks.append(main_player.get_time())

    def chop():
        l, r = lr(marks)
        audio_slice = audio[l:r]
        now = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = now + '.mp3'
        filepath = os.path.join(anki_media, filename)
        audio_slice.export(filepath, format='mp3')
        anki_sound_field = '[sound:%s]' % filename
        pyperclip.copy(anki_sound_field)
        chop_player.set_mrl(filepath)
        chop_player.play()

    def handle(key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        if key is ' ':
            toggle()
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
        if key is 'a':
            l, r = lr(marks)
            marks.append(offset(l, -200))
            marks.append(r)
        if key is 's':
            l, r = lr(marks)
            marks.append(offset(l, 200))
            marks.append(r)
        if key is 'z':
            l, r = lr(marks)
            marks.append(l)
            marks.append(offset(r, -200))
        if key is 'x':
            l, r = lr(marks)
            marks.append(l)
            marks.append(offset(r, 200))
        if key is 'c':
            pause(main_player)
            chop()

    return handle


def format_dt(ms1):
    s1, ms = divmod(ms1, 1000)
    m1, s = divmod(s1, 60)
    h, m = divmod(m1, 60)
    return '%d:%02d:%02d.%d' % (h, m, s, ms // 100)


def lr(marks):
    a, b = marks
    l, r = min(a, b), max(a, b)
    return l, r


def play(player):
    player.set_pause(0)


def pause(player):
    player.set_pause(1)


if __name__ == "__main__":
    main()
