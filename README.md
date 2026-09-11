# tk_date_entry

*tk_date_entry* is a lightweight, dependency-free Tkinter `DateEntry` widget
with a drop-down calendar.

The widget provides a single-line entry showing a date in a configurable
format, with a drop-down calendar popup for visual date selection.

## Key Features

- **Drop-down calendar popup**

  A calendar popup opens below (or above, if there is no room) the entry,
  allowing visual selection of a day. The popup closes with the drop-down
  button (toggle), the `Escape` key, a click outside the popup, or when the
  application window loses the foreground.

- **Full keyboard and mouse navigation**

  Month and year navigation with arrows and comboboxes, month/year selector
  views, keyboard support on the entry, and tooltips showing the full
  localized date when hovering over a day.

- **Configurable date format**

  Any `strftime`-compatible pattern via `date_pattern` (default
  `%Y-%m-%d`), with live validation of typed dates.

- **Localization**

  Month and weekday names follow the current locale, or the one specified
  with the `locale` parameter.

- **Date range validation**

  Optional `mindate` and `maxdate` limits; out-of-range values are rejected
  (raising `ValueError` when `raise_exception` is set, or reported
  in-line otherwise).

- **Weekend and weekday customization**

  Configurable weekend days (`weekenddays`), first day of the week
  (`first_weekday`), optional week numbers (`show_week_numbers`) and
  optional days of adjacent months (`show_other_month_days`).

- **Robust popup behavior**

  The popup follows the application window when moved, never floats above
  unrelated applications, returns the focus to the entry when closed, and
  works consistently on Windows (including with `overrideredirect`
  windows), macOS and Linux.

- **Zero dependencies**

  No third-party packages required: only the Python standard library.

## Installation

Requires Python 3.9 or later (including Python 3.14).

```bash
pip install tk-date-entry
```

## Usage

### Basic usage with default settings

```python
import tkinter as tk
from tk_date_entry import DateEntry

root = tk.Tk()
root.title("DateEntry demo")

de = DateEntry(root, date_pattern="%Y-%m-%d")
de.pack(padx=20, pady=20)

root.mainloop()
```

### Complete example with all options

```python
import tkinter as tk
from datetime import date
from tk_date_entry import DateEntry

root = tk.Tk()
root.title("DateEntry")

de = DateEntry(
    root,
    date_pattern="%d/%m/%Y",   # display format
    first_weekday=0,           # 0 = Monday
    locale=None,               # None = system locale
    mindate=date(2020, 1, 1),  # minimum allowed date
    maxdate=date(2030, 12, 31),# maximum allowed date
    weekenddays=(5, 6),        # Saturday and Sunday
    show_week_numbers=False,   # show the week number column
    show_other_month_days=False,  # grey days of adjacent months
    validate=True,             # validate typed dates
    raise_exception=False,     # report invalid dates in-line
)
de.pack(padx=20, pady=20)

def show():
    print("Selected:", de.get_date())

tk.Button(root, text="Get date", command=show).pack(pady=5)

root.mainloop()
```

### API summary

```python
DateEntry(
    master,
    date_pattern="%Y-%m-%d",
    first_weekday=0,
    value=None,
    locale=None,
    mindate=None,
    maxdate=None,
    weekenddays=(5, 6),
    show_week_numbers=False,
    show_other_month_days=False,
    validate=True,
    raise_exception=False,
    **kwargs,
)
```

| Method | Description |
|--------|-------------|
| `get_date()` | Return the currently set date as a `datetime.date`, or `None` if empty. |
| `set_date(value)` | Set the date (`datetime.date`, `datetime.datetime`, `str` or `None`). |
| `get()` | Return the date as a string formatted with `date_pattern`. |
| `set(value)` | Alias of `set_date()` accepting a string. |
| `clear()` | Clear the entry. |
| `drop_down()` | Open/close the calendar popup (toggle). |
| `state(statespec)` | ttk-compatible state management (e.g. `['disabled']`). |

## Limitations

The calendar popup is a borderless `Toplevel` window. On Windows,
`overrideredirect` windows do not receive focus events, so the widget uses a
very light polling (a single Win32 call every 300 ms, only while the popup is
open) to detect when the application loses the foreground and close the
popup. On macOS and Linux the window manager handles this natively and no
polling is performed.

## License

EUPL-1.2 License - See [LICENSE](LICENSE) for details.
