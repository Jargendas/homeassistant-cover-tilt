"""Config flow for Cover Tilt integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import CONF_INVERT_DIRECTION, CONF_SLAT_ROTATION_TIME, CONF_SOURCE_ENTITY_ID, DOMAIN


class CoverTiltConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cover Tilt."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            rotation_time = float(user_input[CONF_SLAT_ROTATION_TIME])
            if rotation_time <= 0:
                errors[CONF_SLAT_ROTATION_TIME] = "must_be_positive"
            elif round(rotation_time, 1) != rotation_time:
                errors[CONF_SLAT_ROTATION_TIME] = "single_decimal"
            else:
                entity_id = user_input[CONF_SOURCE_ENTITY_ID]
                await self.async_set_unique_id(entity_id)
                self._abort_if_unique_id_configured()
                title = user_input.get(CONF_NAME) or entity_id
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_NAME: title,
                        CONF_SOURCE_ENTITY_ID: entity_id,
                        CONF_SLAT_ROTATION_TIME: rotation_time,
                        CONF_INVERT_DIRECTION: user_input.get(CONF_INVERT_DIRECTION, False),
                    },
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME): selector.TextSelector(),
                vol.Required(CONF_SOURCE_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="cover")
                ),
                vol.Required(CONF_SLAT_ROTATION_TIME, default=1.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional(CONF_INVERT_DIRECTION, default=False): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
