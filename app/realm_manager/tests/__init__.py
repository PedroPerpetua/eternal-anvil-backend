import random
from datetime import date, datetime, timedelta
from typing import Optional
from django.utils.timezone import make_aware
from extensions.utilities import clear_Nones, uuid
from realm_manager import models
from users.models import User
from users.tests import sample_user


def sample_game_world(
    *,
    id: Optional[str] = None,
    name: Optional[str] = None,
    code: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> models.GameWorld:
    if name is None:
        name = "_name"
    if code is None:
        code = uuid()
    if start is None:
        start = make_aware(datetime.now())
    if end is None:
        end = start + timedelta(hours=1)
    return models.GameWorld.objects.create(**clear_Nones(id=id, name=name, code=code, start=start, end=end))


def sample_realm(
    *,
    id: Optional[str] = None,
    name: Optional[str] = None,
    owner: Optional[User] = None,
    game_world: Optional[models.GameWorld] = None,
) -> models.Realm:
    if name is None:
        name = "_name"
    if owner is None:
        owner = sample_user()
    if game_world is None:
        game_world = sample_game_world()
    return models.Realm.objects.create(**clear_Nones(id=id, name=name, owner=owner, game_world=game_world))


def sample_account(
    *,
    id: Optional[str] = None,
    name: Optional[str] = None,
    owner: Optional[User] = None,
    game_world: Optional[models.GameWorld] = None,
    race: Optional[models.Account.Race] = None,
    economy: Optional[models.Account.Economy] = None,
    realm: Optional[models.Realm] = None,
) -> models.Account:
    if name is None:
        name = "_name"
    if owner is None:
        owner = sample_user()
    if game_world is None:
        game_world = realm.game_world if realm else sample_game_world()
    if race is None:
        race = random.choice(models.Account.Race.values)  # type: ignore # TODO
    if economy is None:
        economy = random.choice(models.Account.Economy.values)  # type: ignore # TODO
    return models.Account.objects.create(
        **clear_Nones(id=id, name=name, owner=owner, game_world=game_world, race=race, economy=economy, realm=realm)
    )


def sample_player(
    *, id: Optional[str] = None, user: Optional[User] = None, account: Optional[models.Account] = None
) -> models.Player:
    if user is None:
        user = sample_user()
    if account is None:
        account = sample_account()
    return models.Player.objects.create(**clear_Nones(id=id, user=user, account=account))


def sample_schedule(
    *,
    id: Optional[str] = None,
    player: Optional[models.Player] = None,
    monday: Optional[list[int]] = None,
    tuesday: Optional[list[int]] = None,
    wednesday: Optional[list[int]] = None,
    thursday: Optional[list[int]] = None,
    friday: Optional[list[int]] = None,
    saturday: Optional[list[int]] = None,
    sunday: Optional[list[int]] = None,
) -> models.Schedule:
    if player is None:
        player = sample_player()
    return models.Schedule.objects.create(
        **clear_Nones(
            id=id,
            player=player,
            monday=monday,
            tuesday=tuesday,
            wednesday=wednesday,
            thursday=thursday,
            friday=friday,
            saturday=saturday,
            sunday=sunday,
        )
    )


def sample_schedule_exception(
    *,
    id: Optional[str] = None,
    schedule: Optional[models.Schedule] = None,
    day: Optional[date] = None,
    changes: Optional[list[int]] = None,
) -> models.ScheduleException:
    if schedule is None:
        schedule = sample_schedule()
    if day is None:
        day = date.today()
    return models.ScheduleException.objects.create(**clear_Nones(id=id, schedule=schedule, day=day, changes=changes))
