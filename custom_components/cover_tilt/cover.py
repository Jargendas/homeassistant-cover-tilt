"""Cover platform for Cover Tilt integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
    STATE_CLOSING,
    STATE_OPENING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_SLAT_ROTATION_TIME, CONF_SOURCE_ENTITY_ID


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Cover Tilt cover entity from config entry."""
    async_add_entities([CoverTiltEntity(hass, entry)])


class CoverTiltEntity(CoverEntity):
    """Proxy cover entity with additional tilt support."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._source_entity_id: str = entry.data[CONF_SOURCE_ENTITY_ID]
        self._rotation_time: float = entry.data[CONF_SLAT_ROTATION_TIME]
        self._attr_unique_id = f"{entry.entry_id}_tilt"
        self._attr_name = entry.data.get(CONF_NAME)
        self._cover_position: int | None = None
        self._tilt_position: int | None = None
        self._is_opening = False
        self._is_closing = False
        self._available = False
        self._source_has_tilt = False
        self._performing_tilt_action = False
        self._performing_position_action = False
        self._unsub_state_change: Callable[[], None] | None = None

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        return (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.OPEN_TILT
            | CoverEntityFeature.CLOSE_TILT
            | CoverEntityFeature.STOP_TILT
            | CoverEntityFeature.SET_TILT_POSITION
        )

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of the cover."""
        return self._cover_position

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current tilt position."""
        return self._tilt_position

    @property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        if self._cover_position is None:
            return None
        return self._cover_position == 0

    @property
    def available(self) -> bool:
        """Return if the source entity is available."""
        return self._available

    async def async_added_to_hass(self) -> None:
        """Subscribe to source entity state changes."""
        self._sync_from_source_state(self.hass.states.get(self._source_entity_id))
        self._unsub_state_change = async_track_state_change_event(
            self.hass, self._source_entity_id, self._handle_source_state_change
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe listeners."""
        if self._unsub_state_change is not None:
            self._unsub_state_change()
            self._unsub_state_change = None

    @callback
    def _handle_source_state_change(self, event) -> None:
        """Handle state changes from source cover."""
        self._sync_from_source_state(event.data.get("new_state"))

    @callback
    def _sync_from_source_state(self, state: State | None) -> None:
        """Sync state from the wrapped source entity."""
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._available = False
            self._is_opening = False
            self._is_closing = False
            self.async_write_ha_state()
            return

        self._available = True

        # During tilt actions, don't update position (slat rotation briefly
        # moves the cover but the virtual position should stay the same).
        if not self._performing_tilt_action:
            new_position = state.attributes.get(ATTR_CURRENT_POSITION)
            old_position = self._cover_position
            self._cover_position = new_position

            # For external position changes (not initiated by the virtual
            # entity), update tilt based on movement direction: going up sets
            # tilt to 100 %, going down sets tilt to 0 %.
            if (
                not self._performing_position_action
                and not self._source_has_tilt
                and old_position is not None
                and new_position is not None
                and old_position != new_position
            ):
                self._tilt_position = 100 if new_position > old_position else 0

        if ATTR_CURRENT_TILT_POSITION in state.attributes:
            self._source_has_tilt = True
            if not self._performing_tilt_action and not self._performing_position_action:
                self._tilt_position = state.attributes.get(ATTR_CURRENT_TILT_POSITION)

        self._is_opening = state.state == STATE_OPENING
        self._is_closing = state.state == STATE_CLOSING
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs) -> None:
        """Open the cover."""
        await self._call_cover_service(SERVICE_OPEN_COVER)

    async def async_close_cover(self, **kwargs) -> None:
        """Close the cover."""
        await self._call_cover_service(SERVICE_CLOSE_COVER)

    async def async_stop_cover(self, **kwargs) -> None:
        """Stop the cover."""
        await self._call_cover_service(SERVICE_STOP_COVER)

    async def async_set_cover_position(self, **kwargs) -> None:
        """Move cover to a specific position, then re-apply saved tilt."""
        saved_tilt = self._tilt_position
        self._performing_position_action = True
        try:
            await self._call_cover_service(
                SERVICE_SET_COVER_POSITION,
                {ATTR_POSITION: kwargs[ATTR_POSITION]},
            )
        finally:
            self._performing_position_action = False
        # Re-apply tilt after position change (only for simulated tilt).
        if saved_tilt is not None and not self._source_has_tilt:
            await self.async_set_cover_tilt_position(
                **{ATTR_TILT_POSITION: saved_tilt}
            )

    async def async_open_cover_tilt(self, **kwargs) -> None:
        """Open cover tilt fully."""
        await self.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 100})

    async def async_close_cover_tilt(self, **kwargs) -> None:
        """Close cover tilt fully."""
        await self.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 0})

    async def async_stop_cover_tilt(self, **kwargs) -> None:
        """Stop cover tilt."""
        await self._call_cover_service(SERVICE_STOP_COVER)

    async def async_set_cover_tilt_position(self, **kwargs) -> None:
        """Set cover tilt position with timed movement."""
        target = int(kwargs[ATTR_TILT_POSITION])
        current = 0 if self._tilt_position is None else self._tilt_position

        if target == current:
            return

        service = SERVICE_OPEN_COVER if target > current else SERVICE_CLOSE_COVER
        duration = self._rotation_time * abs(target - current) / 100

        self._performing_tilt_action = True
        try:
            await self._call_cover_service(service)
            await asyncio.sleep(duration)
            await self._call_cover_service(SERVICE_STOP_COVER)
        finally:
            self._performing_tilt_action = False

        if not self._source_has_tilt:
            self._tilt_position = target
            self.async_write_ha_state()

    async def _call_cover_service(self, service: str, data: dict | None = None) -> None:
        """Call cover service on source entity."""
        service_data = {ATTR_ENTITY_ID: self._source_entity_id}
        if data:
            service_data.update(data)

        await self.hass.services.async_call(
            "cover",
            service,
            service_data,
            blocking=True,
        )
