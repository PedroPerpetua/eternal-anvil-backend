from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.timezone import make_aware
from extensions.utilities import uuid
from realm_manager import models
from realm_manager.tests import (
    sample_account,
    sample_game_world,
    sample_player,
    sample_realm,
    sample_schedule,
    sample_schedule_exception,
)
from users.tests import sample_user


class TestGameWorld(TestCase):
    """Test the GameWorld model."""

    def test_creation(self) -> None:
        """Test creating a GameWorld."""
        game_world = models.GameWorld.objects.create(
            name="_name",
            code="_code",
            start=make_aware(datetime.now()),
            end=make_aware(datetime.now() + timedelta(hours=1)),
        )
        self.assertEqual(f"GameWorld [{game_world.code}] {game_world.name}", str(game_world))


class TestRealm(TestCase):
    """Test the Realm model."""

    def test_creation(self) -> None:
        """Test creating a Realm."""
        owner = sample_user()
        game_world = sample_game_world()
        realm = models.Realm.objects.create(name="_name", owner=owner, game_world=game_world)
        self.assertEqual(f"Realm {realm.name}", str(realm))


class TestAccount(TestCase):
    """Test the Account model."""

    def test_creation(self) -> None:
        """Test creating an Account."""
        owner = sample_user()
        game_world = sample_game_world()
        account = models.Account.objects.create(
            name="_name",
            owner=owner,
            game_world=game_world,
            race=models.Account.Race.ELF,
            economy=models.Account.Economy.MULTI_RES,
        )
        self.assertEqual(f"Account {account.name}", str(account))
        # Make sure the owner was associated as a player
        player = models.Player.objects.filter(user=owner, account=account)
        self.assertTrue(player.exists())

    def test_realm_same_game_world(self) -> None:
        """Test that the Account Realm's GameWorld must match the Account's GameWorld."""
        game_world_1 = sample_game_world()
        realm = sample_realm(game_world=game_world_1)
        game_world_2 = sample_game_world()
        # Attempt creation
        with self.assertRaises(ValidationError) as ctx:
            sample_account(game_world=game_world_2, realm=realm)
        self.assertEqual("game_world_mismatch", ctx.exception.error_dict["realm"][0].code)
        # Attempt saving
        account = sample_account(game_world=game_world_2)
        account.realm = realm
        with self.assertRaises(ValidationError) as ctx:
            account.save()
        self.assertEqual("game_world_mismatch", ctx.exception.error_dict["realm"][0].code)

    def test_realm_limit(self) -> None:
        """Test that an Account can only be added to a Realm if the Realm has space."""
        realm = sample_realm()
        [sample_account(realm=realm) for _ in range(15)]
        # Attempt creation
        with self.assertRaises(ValidationError) as ctx:
            sample_account(realm=realm)
        self.assertEqual("realm_full", ctx.exception.error_dict["realm"][0].code)
        # Attempt saving
        account = sample_account(game_world=realm.game_world)
        account.realm = realm
        with self.assertRaises(ValidationError) as ctx:
            account.save()
        self.assertEqual("realm_full", ctx.exception.error_dict["realm"][0].code)

    @patch("realm_manager.models.Player.objects.get_or_create")
    def test_player_creation_atomic(self, player_create_mock: MagicMock) -> None:
        """Test that if the Owner's Player creation fails, the Account is not created."""
        # Make sure that the player creation raises an exception
        player_create_mock.side_effect = Exception()
        # Set up data
        account_id = uuid()
        # Create an account
        with self.assertRaises(Exception):
            sample_account(id=account_id)
        self.assertFalse(models.Account.objects.filter(id=account_id).exists())


class TestPlayer(TestCase):
    """Test the Player model."""

    def test_creation(self) -> None:
        """Test creating a Player."""
        user = sample_user()
        account = sample_account()
        player = models.Player.objects.create(user=user, account=account)
        self.assertEqual(f"Player {player.user} @ {player.account}", str(player))

    def test_unique_user_per_game_world(self) -> None:
        """Test that a User can only be a player once per GameWorld."""
        user = sample_user()
        game_world = sample_game_world()
        # This will create a player for the user
        sample_account(owner=user, game_world=game_world)
        with self.assertRaises(ValidationError) as ctx:
            sample_account(owner=user, game_world=game_world)
        self.assertEqual("multi_account", ctx.exception.error_dict["user"][0].code)

    def test_unique_user_different_game_world(self) -> None:
        """Test that the user can create players in different game worlds."""
        user = sample_user()
        game_world_1 = sample_game_world()
        sample_account(owner=user, game_world=game_world_1)
        # This shouldn't raise an exception
        try:
            game_world_2 = sample_game_world()
            sample_account(owner=user, game_world=game_world_2)
            self.assertTrue(True)
        except ValidationError as ve:  # pragma: no cover
            error = ve.error_dict.get("user")
            if error is not None and len(error) == 1 and error[0].code == "multi_account":
                self.fail("Validation error for multi_account raised.")
            raise


class TestSchedule(TestCase):
    """Test the Schedule model."""

    def test_creation(self) -> None:
        """Test creating a Schedule."""
        player = sample_player()
        schedule = models.Schedule.objects.create(player=player)
        self.assertEqual(f"Schedule for {schedule.player}", str(schedule))

    def test_get_day_schedule(self) -> None:
        """Test getting a specific day's schedule."""
        day = date(2024, 1, 1)  # First of January 2024 -> Monday
        schedule = sample_schedule(monday=[0, 10, 25])
        self.assertEqual(schedule.monday, schedule.get_day_schedule(day))

    def test_get_day_schedule_with_exception(self) -> None:
        """Test getting a specific day's schedule, with an existing exception."""
        day = date(2024, 1, 1)  # First of January 2024 -> Monday
        schedule = sample_schedule(monday=[0, 10, 25])  # 0-10 Y, 10-25 N, 25-End Y
        sample_schedule_exception(schedule=schedule, day=day, changes=[10, 15])  # Flip between 10-15
        expected = [0, 15, 25]  # 0-10 Y, 10-15 Y, 15-25 N, 25-End Y -> 0-15 Y, 15-25 N, 25-End Y
        self.assertEqual(expected, schedule.get_day_schedule(day))


class TestScheduleException(TestCase):
    """Test the ScheduleException model."""

    def test_creation(self) -> None:
        """Test creating a ScheduleException."""
        schedule = sample_schedule()
        day = date.today()
        exception = models.ScheduleException.objects.create(schedule=schedule, day=day, changes=[0, 1])
        self.assertEqual(f"Schedule Exception for {exception.schedule.player} [{exception.day}]", str(exception))

    def test_apply_exception(self) -> None:
        """Test applying an exception on a daily schedule."""
        original = [0, 25, 50, 75, 100]  # 0-25 Y, 25-50 N, 50-75 Y, 75-100 N, 100-End Y
        changes = [20, 60, 100]  # Flip between 20-60 and again at 100
        expected = [0, 20, 25, 50, 60, 75]  # 0-20 Y, 20-25 N, 25-50 Y, 50-60 N, 60-75 Y, 75-End N
        exception = sample_schedule_exception(changes=changes)
        self.assertEqual(expected, exception.apply_exception(original))
