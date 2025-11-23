
- seperate search mode and reveal otp mode. When searching we don't need the activate the countdown loop. That is only activated when the search has filtered down to 1 entry.

- there should be a config option to set the default of color mode true or false. the config dir should be ~/.config/aegis-cli not ~/.config/aegis

- When the countdown number is less than 10, color the number red

- Have a press the 'ctrl+g' key to filter by group. This would use the same search filter function to select a group, then the list would only show entries that belong to that group, that can be searched in the usual way.

- When an item is revealed, show "Press <Enter> to copy the OTP code to the clipboard.", and this should do that. This needs to support Xorg or Wayland (we would set the clipboard tool used in the config.json). If no config entry is set don't show this interactive option message

