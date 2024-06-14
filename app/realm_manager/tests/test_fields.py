from django.core.exceptions import ValidationError
from extensions.models.base import AbstractBaseModel
from extensions.utilities.test import AbstractModelTestCase
from realm_manager.fields import DayScheduleField


class TestDayScheduleField(AbstractModelTestCase):

    class ConcreteModelWithField(AbstractBaseModel):
        field = DayScheduleField()

    MODELS = [ConcreteModelWithField]

    def test_values_unique(self) -> None:
        """Test that the values passed to the field have to be unique"""
        # Attempt creation
        with self.assertRaises(ValidationError) as ctx:
            self.ConcreteModelWithField._default_manager.create(field=[1, 1])
        self.assertEqual("items_not_unique", ctx.exception.error_dict["field"][0].code)
        # Attempt saving
        obj = self.ConcreteModelWithField._default_manager.create(field=[0, 1])
        obj.field = [1, 1]
        with self.assertRaises(ValidationError) as ctx:
            obj.save()
        self.assertEqual("items_not_unique", ctx.exception.error_dict["field"][0].code)

    def test_values_min(self) -> None:
        """Test that values are minimum at 0."""
        # Attempt creation
        with self.assertRaises(ValidationError) as ctx:
            self.ConcreteModelWithField._default_manager.create(field=[-1])
        self.assertEqual("item_invalid", ctx.exception.error_dict["field"][0].code)
        # Attempt saving
        obj = self.ConcreteModelWithField._default_manager.create(field=[])
        obj.field = [-1]
        with self.assertRaises(ValidationError) as ctx:
            obj.save()
        self.assertEqual("item_invalid", ctx.exception.error_dict["field"][0].code)

    def test_values_max(self) -> None:
        """Test that the values are maxed at 288."""
        # Attempt creation
        with self.assertRaises(ValidationError) as ctx:
            self.ConcreteModelWithField._default_manager.create(field=[289])
        self.assertEqual("item_invalid", ctx.exception.error_dict["field"][0].code)
        # Attempt saving
        obj = self.ConcreteModelWithField._default_manager.create(field=[])
        obj.field = [289]
        with self.assertRaises(ValidationError) as ctx:
            obj.save()
        self.assertEqual("item_invalid", ctx.exception.error_dict["field"][0].code)

    def test_sort_on_save(self) -> None:
        """Test that the values are sorted on save."""
        values = [5, 2, 3, 1, 4]
        # Attempt creation
        created = self.ConcreteModelWithField._default_manager.create(field=values)
        created.refresh_from_db()
        self.assertEqual(sorted(values), created.field)
        # Attempt saving
        obj = self.ConcreteModelWithField._default_manager.create(field=[])
        obj.field = values
        obj.save()
        obj.refresh_from_db()
        self.assertEqual(sorted(values), obj.field)
