from typing import Any
from django.contrib import admin
from django.http import HttpRequest
from core.admin import admin_site
from realm_manager import models


# TODO: This needs a overhaul for usability


class ReadOnlyInline(admin.TabularInline):
    max_num = 0
    can_delete = False

    def get_readonly_fields(self, request: HttpRequest, obj: Any | None = ...) -> list[str] | tuple[Any, ...]:
        return super().get_readonly_fields(request, obj) + self.fields  # type: ignore


class InlineRealm(ReadOnlyInline):
    model = models.Realm
    fields = ("name", "owner")


class InlineAccount_GameWorld(ReadOnlyInline):
    model = models.Account
    fields = ("name", "owner", "player_count")

    def player_count(self, instance: models.Account) -> int:
        return instance.players.count()


@admin.register(models.GameWorld, site=admin_site)
class GameWorldAdmin(admin.ModelAdmin):
    inlines = (InlineRealm, InlineAccount_GameWorld)


class InlineAccount_Realm(ReadOnlyInline):
    model = models.Account
    fields = ("name", "owner", "player_count", "race", "economy")

    def player_count(self, instance: models.Account) -> int:
        return instance.players.count()


@admin.register(models.Realm, site=admin_site)
class RealmAdmin(admin.ModelAdmin):
    inlines = (InlineAccount_Realm,)


class InlinePlayer(ReadOnlyInline):
    model = models.Player
    fields = ("user",)


@admin.register(models.Account, site=admin_site)
class AccountAdmin(admin.ModelAdmin):
    inlines = (InlinePlayer,)


class ScheduleInline(admin.TabularInline):
    model = models.Schedule


@admin.register(models.Player, site=admin_site)
class PlayerAdmin(admin.ModelAdmin):
    inlines = (ScheduleInline,)


class ScheduleExceptionInline(admin.TabularInline):
    model = models.ScheduleException


@admin.register(models.Schedule, site=admin_site)
class ScheduleAdmin(admin.ModelAdmin):
    inlines = (ScheduleExceptionInline,)


@admin.register(models.ScheduleException, site=admin_site)
class ScheduleException(admin.ModelAdmin): ...
