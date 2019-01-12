from unittest import mock

import pydrag

from pytuber import cli
from pytuber.lastfm.models import PlaylistType, UserPlaylistType
from pytuber.lastfm.params import (
    ArtistParamType,
    CountryParamType,
    TagParamType,
    UserParamType,
)
from pytuber.lastfm.services import LastService
from pytuber.models import (
    ConfigManager,
    PlaylistManager,
    Provider,
    TrackManager,
)
from tests.utils import CommandTestCase, PlaylistFixture, TrackFixture


class CommandSetupTests(CommandTestCase):
    def test_create(self):
        self.assertIsNone(ConfigManager.get(Provider.lastfm, default=None))
        result = self.runner.invoke(cli, ["lastfm", "setup"], input="aaaa")

        expected_output = (
            "Last.fm Api Key: aaaa",
            "Last.fm configuration updated!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)

        actual = ConfigManager.get(Provider.lastfm)
        self.assertDictEqual({"api_key": "aaaa"}, actual.data)

    def test_update(self):
        ConfigManager.set(
            dict(provider=Provider.lastfm, data=dict(api_key="bbbb"))
        )

        self.assertEqual(
            dict(api_key="bbbb"), ConfigManager.get(Provider.lastfm).data
        )
        result = self.runner.invoke(
            cli, ["lastfm", "setup"], input="\n".join(("aaaa", "y"))
        )

        expected_output = (
            "Last.fm Api Key: aaaa",
            "Overwrite existing configuration? [y/N]: y",
            "Last.fm configuration updated!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)

        actual = ConfigManager.get(Provider.lastfm)
        self.assertDictEqual({"api_key": "aaaa"}, actual.data)


class CommandAddTests(CommandTestCase):
    @mock.patch.object(UserParamType, "convert")
    @mock.patch.object(PlaylistManager, "set")
    def test_user(self, create_playlist, convert):
        convert.return_value = "bbb"
        create_playlist.return_value = PlaylistFixture.one()
        result = self.runner.invoke(
            cli,
            ["lastfm", "add", "user"],
            input="\n".join(("aaa", "2", "50", "My Favorite  ")),
            catch_exceptions=False,
        )

        expected_output = (
            "Last.fm username: aaa",
            "Playlist Types",
            "[1] user_loved_tracks",
            "[2] user_top_tracks",
            "[3] user_recent_tracks",
            "[4] user_friends_recent_tracks",
            "Select a playlist type 1-4: 2",
            "Maximum tracks [50]: 50",
            "Optional Title: My Favorite  ",
            "Added playlist: id_a!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        create_playlist.assert_called_once_with(
            dict(
                type=UserPlaylistType.USER_TOP_TRACKS,
                provider=Provider.lastfm,
                arguments=dict(username="bbb"),
                limit=50,
                title="My Favorite",
            )
        )

    @mock.patch.object(PlaylistManager, "set")
    def test_chart(self, create_playlist):
        create_playlist.return_value = PlaylistFixture.one()
        result = self.runner.invoke(
            cli, ["lastfm", "add", "chart"], input="50\n "
        )

        expected_output = (
            "Maximum tracks [50]: 50",
            "Optional Title:  ",
            "Added playlist: id_a!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)

        create_playlist.assert_called_once_with(
            dict(
                type=PlaylistType.CHART,
                provider=Provider.lastfm,
                limit=50,
                title="",
            )
        )

    @mock.patch.object(CountryParamType, "convert")
    @mock.patch.object(PlaylistManager, "set")
    def test_country(self, create_playlist, country_param_type):
        country_param_type.return_value = "greece"
        create_playlist.return_value = PlaylistFixture.one()
        result = self.runner.invoke(
            cli, ["lastfm", "add", "country"], input=b"gr\n50\n "
        )

        expected_output = (
            "Country Code: gr",
            "Maximum tracks [50]: 50",
            "Optional Title:  ",
            "Added playlist: id_a!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        create_playlist.assert_called_once_with(
            dict(
                type=PlaylistType.COUNTRY,
                provider=Provider.lastfm,
                arguments=dict(country="greece"),
                limit=50,
                title="",
            )
        )

    @mock.patch.object(TagParamType, "convert")
    @mock.patch.object(PlaylistManager, "set")
    def test_tag(self, create_playlist, convert):
        convert.return_value = "rock"
        create_playlist.return_value = PlaylistFixture.one(synced=111)
        result = self.runner.invoke(
            cli, ["lastfm", "add", "tag"], input="rock\n50\n "
        )

        expected_output = (
            "Tag: rock",
            "Maximum tracks [50]: 50",
            "Optional Title:  ",
            "Updated playlist: id_a!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        create_playlist.assert_called_once_with(
            dict(
                type=PlaylistType.TAG,
                provider=Provider.lastfm,
                arguments=dict(tag="rock"),
                limit=50,
                title="",
            )
        )

    @mock.patch.object(ArtistParamType, "convert")
    @mock.patch.object(PlaylistManager, "set")
    def test_artist(self, create_playlist, artist_param):
        artist_param.return_value = "Queen"
        create_playlist.return_value = PlaylistFixture.one()
        result = self.runner.invoke(
            cli,
            ["lastfm", "add", "artist"],
            input="Queen\n50\nQueen....",
            catch_exceptions=False,
        )

        expected_output = (
            "Artist: Queen",
            "Maximum tracks [50]: 50",
            "Optional Title: Queen....",
            "Added playlist: id_a!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        create_playlist.assert_called_once_with(
            dict(
                type=PlaylistType.ARTIST,
                provider=Provider.lastfm,
                arguments=dict(artist="Queen"),
                limit=50,
                title="Queen....",
            )
        )


class CommandTagsTests(CommandTestCase):
    @mock.patch.object(LastService, "get_tags")
    @mock.patch.object(LastService, "__init__", return_value=None)
    def test_default(self, _, get_tags):
        get_tags.return_value = [
            pydrag.Tag(name="rock", count=1, reach=2),
            pydrag.Tag(name="rap", count=2, reach=4),
            pydrag.Tag(name="metal", count=3, reach=6),
        ]
        result = self.runner.invoke(cli, ["lastfm", "tags"])
        expected_output = (
            "No  Name      Count    Reach",
            "----  ------  -------  -------",
            "   0  rock          1        2",
            "   1  rap           2        4",
            "   2  metal         3        6",
        )

        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        get_tags.assert_called_once_with(refresh=False)

    @mock.patch.object(LastService, "get_tags")
    @mock.patch.object(LastService, "__init__", return_value=None)
    def test_force_refresh(self, _, get_tags):
        result = self.runner.invoke(cli, ["lastfm", "tags", "--refresh"])

        self.assertEqual(0, result.exit_code)
        get_tags.assert_called_once_with(refresh=True)


class CommandListPlaylistsTests(CommandTestCase):
    @mock.patch.object(PlaylistManager, "find")
    def test_list_without_id(self, find):
        find.return_value = PlaylistFixture.get(
            2,
            limit=[10, 15],
            youtube_id=["456ybnm", None],
            modified=[1546727685, None],
            synced=[None, 1546727285],
            uploaded=[None, 1546727385],
        )
        result = self.runner.invoke(cli, ["lastfm", "list"])

        expected_output = (
            "ID    YoutubeID    Title    Arguments      Limit  Modified          Synced            Uploaded",
            "----  -----------  -------  -----------  -------  ----------------  ----------------  ----------------",
            "id_a  456ybnm      Type A   a: 0              10  2019-01-05 22:34  -                 -",
            "id_b               Type B   b: 1              15  -                 2019-01-05 22:28  2019-01-05 22:29",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        find.assert_called_once_with(provider=Provider.lastfm)

    @mock.patch.object(TrackManager, "get")
    @mock.patch.object(PlaylistManager, "get")
    def test_list_with_id(self, get_playlist, get_track):
        playlist = PlaylistFixture.one(tracks=[1, 2, 3])

        get_playlist.return_value = playlist
        get_track.side_effect = TrackFixture.get(3, duration=[120, 1844, 0])

        result = self.runner.invoke(
            cli, ["lastfm", "list", playlist.id], catch_exceptions=False
        )

        expected_output = (
            "No  Artist    Track Name    Duration    YoutubeID",
            "----  --------  ------------  ----------  -----------",
            "   0  artist_a  name_a        0:02:00",
            "   1  artist_b  name_b        0:30:44",
            "   2  artist_c  name_c        -",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        get_playlist.assert_called_once_with(playlist.id)
        get_track.assert_has_calls([mock.call(id) for id in playlist.tracks])


class CommandRemovePlaylistTests(CommandTestCase):
    @mock.patch.object(PlaylistManager, "remove")
    def test_remove(self, remove):

        result = self.runner.invoke(
            cli, ["lastfm", "remove", "foo", "bar"], input="y"
        )

        expected_output = (
            "Do you want to continue? [y/N]: y",
            "Removed playlist: foo!",
            "Removed playlist: bar!",
        )
        self.assertEqual(0, result.exit_code)
        self.assertOutput(expected_output, result.output)
        remove.assert_has_calls([mock.call("foo"), mock.call("bar")])

    def test_remove_no_confirm(self):
        result = self.runner.invoke(
            cli, ["lastfm", "remove", "foo"], input="n"
        )

        expected_output = ("Do you want to continue? [y/N]: n", "Aborted!")
        self.assertEqual(1, result.exit_code)
        self.assertOutput(expected_output, result.output)


class CommandSyncPlaylistsTests(CommandTestCase):
    @mock.patch.object(TrackManager, "set")
    @mock.patch.object(LastService, "get_tracks")
    @mock.patch.object(PlaylistManager, "update")
    @mock.patch.object(PlaylistManager, "find")
    def test_sync_all(self, find, update, get_tracks, set):

        tracks = TrackFixture.get(6)
        playlists = PlaylistFixture.get(2)
        last_tracks = [
            pydrag.Track.from_dict(dict(name=track.name, artist=track.artist))
            for track in tracks
        ]

        set.side_effect = tracks
        find.return_value = playlists
        get_tracks.side_effect = [
            [last_tracks[0], last_tracks[1], last_tracks[2]],
            [last_tracks[3], last_tracks[4], last_tracks[5]],
        ]

        result = self.runner.invoke(
            cli, ["lastfm", "sync"], catch_exceptions=False
        )

        self.assertEqual(0, result.exit_code)
        find.assert_called_once_with(provider=Provider.lastfm)
        get_tracks.assert_has_calls(
            [
                mock.call(a=0, limit=100, type="type_a"),
                mock.call(b=1, limit=100, type="type_b"),
            ]
        )
        set.assert_has_calls(
            [
                mock.call(
                    {"artist": "artist_a", "name": "name_a", "duration": None}
                ),
                mock.call(
                    {"artist": "artist_b", "name": "name_b", "duration": None}
                ),
                mock.call(
                    {"artist": "artist_c", "name": "name_c", "duration": None}
                ),
                mock.call(
                    {"artist": "artist_d", "name": "name_d", "duration": None}
                ),
                mock.call(
                    {"artist": "artist_e", "name": "name_e", "duration": None}
                ),
                mock.call(
                    {"artist": "artist_f", "name": "name_f", "duration": None}
                ),
            ]
        )

        update.assert_has_calls(
            [
                mock.call(playlists[0], dict(tracks=["id_a", "id_b", "id_c"])),
                mock.call(playlists[1], dict(tracks=["id_d", "id_e", "id_f"])),
            ]
        )

    @mock.patch.object(TrackManager, "set")
    @mock.patch.object(LastService, "get_tracks")
    @mock.patch.object(PlaylistManager, "update")
    @mock.patch.object(PlaylistManager, "find")
    def test_sync_one(self, find, update, get_tracks, set):
        tracks = TrackFixture.get(3)
        playlists = PlaylistFixture.get(2)
        last_tracks = [
            pydrag.Track.from_dict(dict(name=track.name, artist=track.artist))
            for track in tracks
        ]

        set.side_effect = tracks
        find.return_value = playlists
        get_tracks.side_effect = [
            [last_tracks[0], last_tracks[1], last_tracks[2]]
        ]

        result = self.runner.invoke(
            cli, ["lastfm", "sync", playlists[1].id], catch_exceptions=False
        )

        self.assertEqual(0, result.exit_code)
        find.assert_called_once_with(provider=Provider.lastfm)
        get_tracks.assert_called_once_with(b=1, limit=100, type="type_b")
        set.assert_has_calls(
            [
                mock.call(
                    {"artist": "artist_a", "name": "name_a", "duration": None}
                ),
                mock.call(
                    {"artist": "artist_b", "name": "name_b", "duration": None}
                ),
                mock.call(
                    {"artist": "artist_c", "name": "name_c", "duration": None}
                ),
            ]
        )

        update.assert_called_once_with(
            playlists[1], dict(tracks=["id_a", "id_b", "id_c"])
        )
