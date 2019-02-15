from unittest import mock

from pytuber import cli
from pytuber.core.commands.cmd_add import (
    create_playlist,
    parse_text,
    parse_xspf,
)
from pytuber.core.models import PlaylistManager, PlaylistType, Provider
from tests.utils import CommandTestCase, PlaylistFixture


class CommandAddTests(CommandTestCase):
    @mock.patch("click.edit")
    @mock.patch("pytuber.core.commands.cmd_add.create_playlist")
    @mock.patch("pytuber.core.commands.cmd_add.parse_text")
    def test_add_from_editor(self, parse_text, create_playlist, clk_edit):
        clk_edit.return_value = "foo"
        parse_text.return_value = ["a", "b"]
        self.runner.invoke(
            cli, ["add", "editor", "--title", "My Cool Playlist"]
        )
        parse_text.assert_called_once_with("foo")
        create_playlist.assert_called_once_with("My Cool Playlist", ["a", "b"])

    @mock.patch("pytuber.core.commands.cmd_add.create_playlist")
    @mock.patch("pytuber.core.commands.cmd_add.parse_text")
    def test_add_from_txt_file(self, parse_text, create_playlist):
        parse_text.return_value = ["a", "b"]
        with self.runner.isolated_filesystem():
            with open("hello.txt", "w") as f:
                f.write("foo")

            self.runner.invoke(
                cli,
                ["add", "file", "hello.txt", "--title", "My Cool Playlist"],
            )

            parse_text.assert_called_once_with("foo")
            create_playlist.assert_called_once_with(
                "My Cool Playlist", ["a", "b"]
            )

    @mock.patch("pytuber.core.commands.cmd_add.create_playlist")
    @mock.patch("pytuber.core.commands.cmd_add.parse_xspf")
    def test_add_from_xspf_file(self, parse_xspf, create_playlist):
        parse_xspf.return_value = ["a", "b"]
        with self.runner.isolated_filesystem():
            with open("hello.xspf", "w") as f:
                f.write("foo")

            self.runner.invoke(
                cli,
                [
                    "add",
                    "file",
                    "hello.xspf",
                    "--title",
                    "My Cool Playlist",
                    "--format",
                    "xspf",
                ],
            )

            parse_xspf.assert_called_once_with("foo")
            create_playlist.assert_called_once_with(
                "My Cool Playlist", ["a", "b"]
            )


class CommandAddUtilsTests(CommandTestCase):
    def test_parse_text(self):
        text = "\n".join(
            (
                "Queen - Bohemian Rhapsody",
                " Queen - Bohemian Rhapsody",
                "Queen -I want to break free",
                "#" " ",
                "Wrong Format",
            )
        )
        expected = [
            ("Queen", "Bohemian Rhapsody"),
            ("Queen", "I want to break free"),
        ]
        self.assertEqual(expected, parse_text(text))

    def test_parse_xspf(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
            <playlist version="1" xmlns="http://xspf.org/ns/0/">
                <trackList>
                    <track>
                        <creator>Queen</creator>
                        <title>Bohemian Rhapsody</title>
                    </track>
                    <track>
                        <creator>Queen</creator>
                        <title>Bohemian Rhapsody</title>
                    </track>
                    <track>
                        <creator>Queen</creator>
                        <title>I want to break free</title>
                    </track>
                    <track>
                        <creator>No track</creator>
                    </track>
                    <track>
                        <title>No artist</title>
                    </track>
                </trackList>
            </playlist>"""

        expected = [
            ("Queen", "Bohemian Rhapsody"),
            ("Queen", "I want to break free"),
        ]
        self.assertEqual(expected, parse_xspf(xml))
        self.assertEqual([], parse_xspf(""))

    @mock.patch("pytuber.core.commands.cmd_add.magenta")
    @mock.patch.object(PlaylistManager, "set")
    @mock.patch("click.confirm")
    @mock.patch("click.secho")
    @mock.patch("click.clear")
    def test_create_playlist(self, clear, secho, confirm, set, magenta):
        magenta.side_effect = lambda x: x
        set.return_value = PlaylistFixture.one()
        tracks = [
            ("Queen", "Bohemian Rhapsody"),
            ("Queen", "I want to break free"),
        ]
        create_playlist("My Cool Playlist", tracks)

        expected_ouput = (
            "Title:  My Cool Playlist",
            "Tracks:  2",
            "",
            "  No  Artist    Track Name",
            "----  --------  --------------------",
            "   1  Queen     Bohemian Rhapsody",
            "   2  Queen     I want to break free",
        )

        self.assertOutput(expected_ouput, secho.call_args_list[0][0][0])
        self.assertEqual(
            "Added playlist: id_a!", secho.call_args_list[1][0][0]
        )

        clear.assert_called_once_with()
        confirm.assert_called_once_with(
            "Are you sure you want to save this playlist?", abort=True
        )
        set.assert_called_once_with(
            dict(
                type=PlaylistType.EDITOR,
                provider=Provider.user,
                title="My Cool Playlist",
                tracks=["55a4d2b", "b045fee"],
            )
        )

    @mock.patch("click.secho")
    def test_create_playlist_empty_tracks(self, secho):
        create_playlist("foo", [])
        secho.assert_called_once_with("Tracklist is empty, aborting...")
