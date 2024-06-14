from typing import TYPE_CHECKING, Any, Optional
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


if TYPE_CHECKING:
    BaseField = ArrayField[list[int], list[int]]
else:
    BaseField = ArrayField


class DayScheduleField(BaseField):
    """
    The DayScheduleField represents a series of intervals over the course of 24 hours. It's a PositiveInteger
    ArrayField that can have unique values from 0 to 288.

    Values are tied with their correspondent 5 minute interval. For example:
    - 0 -> 00:00
    - 1 -> 00:05
    - 20 -> 01:40
    - 288 -> 23:55

    Each value on this array represents a "flip" on the availability. So, an array of [0, 10, 15] means "available
    from 0 to 10, unavailable from 10 to 15, available from 15 till end of day". Translates to "Available from 00:00
    to 00:50, unavailable from 00:50 to 01:15, available from 01:15 till 24:00".
    """

    description = "Represents intervals over the course of 24 hours."

    def __init__(self, base_field: Optional[models.Field] = None, **kwargs: Any) -> None:
        if base_field is None:
            base_field = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(288)])
        kwargs.setdefault("blank", True)
        kwargs.setdefault("default", list)
        super().__init__(base_field, **kwargs)

    def validate(self, value: list[int], model_instance: Optional[models.Model]) -> None:
        """Override Validate to ensure that the values are unique."""
        super().validate(value, model_instance)
        # Make sure the values are unique
        if len(value) > len(set(value)):
            raise ValidationError("Values must be unique", code="items_not_unique", params={"value": value})

    def pre_save(self, model_instance: models.Model, add: bool) -> list[int]:
        """Override the pre_save to make sure the value is always sorted."""
        value: list[int] = super().pre_save(model_instance, add)
        return sorted(value)
