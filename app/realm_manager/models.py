from __future__ import annotations
from datetime import date
from typing import TYPE_CHECKING, Any
from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic
from extensions.models import AbstractBaseModel
from realm_manager.fields import DayScheduleField
from users.models import User


if TYPE_CHECKING:
    from django_stubs_ext.db.models.manager import RelatedManager


class GameWorld(AbstractBaseModel):
    """This model represents an Arkheim server."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255, unique=True)
    start = models.DateTimeField()
    end = models.DateTimeField()

    # Related managers
    realms: RelatedManager["Realm"]
    accounts: RelatedManager["Account"]

    def __str__(self) -> str:
        return f"GameWorld [{self.code}] {self.name}"


class Realm(AbstractBaseModel):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="owned_realms")
    game_world = models.ForeignKey(GameWorld, on_delete=models.CASCADE, related_name="realms")

    # Related managers
    accounts: RelatedManager["Account"]

    def __str__(self) -> str:
        return f"Realm {self.name}"


class Account(AbstractBaseModel):
    """This model represents an Account in an Arkheim server - an Avatar."""

    class Race(models.TextChoices):
        ELF = "ELF", "Elf"
        DWARF = "DWARF", "Dwarf"

    class Economy(models.TextChoices):
        MULTI_RES = "MULTI", "Multi Resource"
        SINGLE_WOOD = "WOOD", "Single Wood"
        SINGLE_IRON = "IRON", "Single Iron"
        SINGLE_CROP = "CROP", "Single Crop"

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="owned_accounts")
    game_world = models.ForeignKey(GameWorld, on_delete=models.CASCADE, related_name="accounts")
    race = models.CharField(max_length=10, choices=Race)
    economy = models.CharField(max_length=10, choices=Economy)
    realm = models.ForeignKey(Realm, on_delete=models.SET_NULL, related_name="accounts", null=True, blank=True)

    # Related managers
    players: RelatedManager["Player"]

    @property
    def users(self) -> models.query.QuerySet[User]:
        """Get the list of users in this account's players."""
        return User.objects.filter(player_accounts__account=self)

    def join_account(self, user: User) -> None:
        """Method to have a User join the Account."""
        Player.objects.create(user=user, account=self)

    def leave_account(self, user: User) -> None:
        """
        Method to have a User leave the Account.

        If the User is not part of the Account, or if the user is the owner, raises a ValidationError.
        """
        if user == self.owner:
            raise ValidationError(
                {"owner": ValidationError("The owner of the account cannot be removed.", code="failed_remove_owner")}
            )
        player = self.players.filter(user=user).first()
        if not player:
            raise ValidationError("The user is not part of this account.", code="not_player")
        player.delete()

    def change_owner(self, new_owner: User) -> None:
        """
        Method to change the owner of the Account.

        If the new owner is not part of the Account, raises a ValidationError.
        """
        if self.owner == new_owner:
            return
        if not self.players.filter(user=new_owner).exists():
            raise ValidationError(
                {"owner": ValidationError("The new owner is not a player in this account.", code="bad_owner")}
            )
        self.owner = new_owner
        self.save()

    def validate_realm_matches(self) -> None:
        """
        Ensure that the Account's GameWorld matches it's realm's GameWorld

        Since Django's unique constraint can't navigate trough multiple models, we validate it on a method.
        """
        if not self.realm:
            return
        if self.game_world != self.realm.game_world:
            raise ValidationError(
                "This account's game world and the realm's game world mismatch.", code="game_world_mismatch"
            )

    def validate_realm_size(self) -> None:
        """Ensure that the realm only has 15 members at most."""
        if not self.realm:
            return
        if self.realm.accounts.count() >= 15:
            raise ValidationError({"realm": ValidationError("This realm is full!", code="realm_full")})

    @atomic
    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override `save` to run our validators.

        We also want to make sure the owner is a player on this account. We run this as atomic in case it fails to
        create the player (for example, because of multi accounting).
        """
        self.validate_realm_matches()
        self.validate_realm_size()
        super().save(*args, **kwargs)
        # If the owner isn't a player of this account, make him one
        Player.objects.get_or_create(user=self.owner, account=self)

    def __str__(self) -> str:
        return f"Account {self.name}"


class Player(AbstractBaseModel):
    """
    This model represents the association between a person and an avatar - Player and Account.

    Multiple Users can be associated with the same Account - duals.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="player_accounts")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="players")

    # Related managers
    schedule: "Schedule"

    def validate_user_unique_per_game_world(self) -> None:
        """
        Ensure that the user is unique in the GameWorld.

        Since Django's unique constraint can't navigate trough multiple models, we validate it on a method.

        Note: this will also create an indirect UniqueTogether constraint on (User, Account).
        """
        if self.account.game_world.accounts.filter(players__user=self.user).exists():
            raise ValidationError(
                {"user": ValidationError("User is already present in this game world.", code="multi_account")}
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override `save` to run our validators."""
        self.validate_user_unique_per_game_world()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Player {self.user} @ {self.account}"


class Schedule(AbstractBaseModel):
    """This model represents the weekly schedule of a given Player."""

    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="schedule")
    monday = DayScheduleField()
    tuesday = DayScheduleField()
    wednesday = DayScheduleField()
    thursday = DayScheduleField()
    friday = DayScheduleField()
    saturday = DayScheduleField()
    sunday = DayScheduleField()

    # Related managers
    exceptions: RelatedManager["ScheduleException"]

    def get_day_schedule(self, date: date) -> list[int]:
        """Returns the schedule for a given day, applying any ScheduleExceptions if they exist."""
        ordered_days = [
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        ]
        base_schedule = ordered_days[date.isoweekday() - 1]  # Monday == 1 per isoweekday
        exception = self.exceptions.filter(day=date)
        if not exception.exists():
            return base_schedule
        return exception.get().apply_exception(base_schedule)

    def __str__(self) -> str:
        return f"Schedule for {self.player}"


class ScheduleException(AbstractBaseModel):
    """
    This model represents an exception to a player's schedule; because sometimes you take weekends off to be with your
    girlfriend.
    """

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="exceptions")
    day = models.DateField()
    changes = DayScheduleField()
    """
    Changes are saved the same way that a schedule is.
    The effective availability can be calculated by adding both the day's schedule and the changes, removing
    pairs of duplicates.
    """

    def apply_exception(self, schedule: list[int]) -> list[int]:
        """Compute the resulting schedule with this exception applied."""
        combined = schedule + self.changes
        item_count: dict[int, int] = {}
        for item in combined:
            item_count.setdefault(item, 0)
            item_count[item] += 1
        filtered = [item for item in item_count if item_count[item] == 1]
        return sorted(filtered)

    class Meta(AbstractBaseModel.Meta):
        constraints = (models.UniqueConstraint(fields=["schedule", "day"], name="one_exception_per_day"),)

    def __str__(self) -> str:
        return f"Schedule Exception for {self.schedule.player} [{self.day}]"
