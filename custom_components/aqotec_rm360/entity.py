"""Base entity for the aqotec RM360 integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_ID_PREFIX, MANUFACTURER, MODEL
from .coordinator import RM360Coordinator


class RM360Entity(CoordinatorEntity[RM360Coordinator]):
    """Common device wiring for all RM360 entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RM360Coordinator,
        description: EntityDescription,
        platform: str,
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self.entity_description = description

        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        # Only a suggestion: it applies when the entity is first registered
        # and never overrides a rename made afterwards.
        self.entity_id = f"{platform}.{ENTITY_ID_PREFIX}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def raw_value(self) -> float | int | None:
        """Return the decoded register value, if it was read this cycle."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        """A register the controller refused stays unavailable."""
        return super().available and self.raw_value is not None
