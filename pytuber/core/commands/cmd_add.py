import contextlib
import io
from typing import List

import click
from lxml import etree
from tabulate import tabulate

from pytuber.core.models import (
    PlaylistManager,
    PlaylistType,
    Provider,
    TrackManager,
)
from pytuber.lastfm.commands.cmd_add import option_title
from pytuber.utils import magenta


@click.command("editor")
@option_title()
def add_from_editor(title: str) -> None:
    """Create playlist in a text editor."""
    marker = (
        "\n\n# Copy/Paste your track list and hit save!\n"
        "# One line per track, make sure it doesn't start with a #\n"
        "# Separate the track artist and title with a single dash `-`\n"
    )
    message = click.edit(marker)
    create_playlist(title, parse_text(message or ""))


@click.command("file")
@click.argument("file", type=click.Path(), required=True)
@click.option("--format", type=click.Choice(["txt", "xspf"]), default="txt")
@option_title()
def add_from_file(file: str, title: str, format: str) -> None:
    """Import a playlist from a text file."""

    with open(file, "r", encoding="UTF-8") as fp:
        text = fp.read()

    parsers = dict(xspf=parse_xspf, txt=parse_text)
    create_playlist(title, parsers[format](text or ""))


def parse_text(text):
    """
    Parse raw text format playlists, each line must contain a single.

    track with artist and title separated by a single dash. eg Queen - Bohemian Rhapsody

    :param str text:
    :return: A list of tracks
    """
    tracks: List[tuple] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split("-", 1)
        if len(parts) != 2:
            continue

        artist, track = list(map(str.strip, parts))
        if not artist or not track or (artist, track) in tracks:
            continue

        tracks.append((artist, track))

    return tracks


def parse_xspf(xml):
    """
    Parse xspf playlists and be as graceful as possible with errors.

    :param str xml:
    :return: A list of tracks
    """
    tracks = []
    with contextlib.suppress(etree.XMLSyntaxError):
        context = etree.iterparse(io.BytesIO(xml.encode("UTF-8")))
        for action, elem in context:
            if elem.tag.endswith("creator"):
                artist = elem.text.strip()
            elif elem.tag.endswith("title"):
                track = elem.text.strip()
            elif elem.tag.endswith("track"):
                if artist and track and (artist, track) not in tracks:
                    tracks.append((artist, track))
                artist = track = None
    return tracks


def create_playlist(title, tracks):
    if not tracks:
        return click.secho("Tracklist is empty, aborting...")

    click.clear()
    click.secho(
        "{}\n\n{}\n".format(
            tabulate(  # type: ignore
                [
                    (magenta("Title:"), title),
                    (magenta("Tracks:"), len(tracks)),
                ],
                tablefmt="plain",
                colalign=("right", "left"),
            ),
            tabulate(  # type: ignore
                [
                    (i + 1, track[0], track[1])
                    for i, track in enumerate(tracks)
                ],
                headers=("No", "Artist", "Track Name"),
            ),
        )
    )
    click.confirm("Are you sure you want to save this playlist?", abort=True)
    playlist = PlaylistManager.set(
        dict(
            type=PlaylistType.EDITOR,
            provider=Provider.user,
            title=title.strip(),
            tracks=[
                TrackManager.set(dict(artist=artist, name=name)).id
                for artist, name in tracks
            ],
        )
    )
    click.secho("Added playlist: {}!".format(playlist.id))
