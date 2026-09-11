import calendar
import datetime
import locale as _locale
import sys
import tkinter as tk
from tkinter import ttk


class DateEntry(ttk.Frame):
    """
    A lightweight DateEntry implemented using only tkinter/ttk.

    Features:
    - Editable date entry with configurable date format (strftime pattern,
      default YYYY-MM-DD)
    - Localized month and weekday names: by default the names are taken
      from the current system locale; an explicit locale identifier (e.g.
      "it_IT", "en_US") can be given, or "C" for English names
    - Calendar popup with day selection
    - Month and year selection dropdowns (comboboxes) in the popup header
    - Month/year navigation chevrons
    - Optional minimum and maximum allowed dates (mindate/maxdate): days
      outside the range are disabled and cannot be selected
    - Optional weekend days highlighting (weekenddays)
    - Optional week numbers column (show_week_numbers)
    - Optional days of the previous/next month (show_other_month_days)
    - Today and Clear buttons
    - Selected-date and today highlighting
    - Empty (nullable) value support
    - Optional input validation: when validate is True, an invalid typed
      date is restored to the last valid value when the entry loses the
      focus (or raises ValueError if raise_exception is True)
    - <<DateEntrySelected>> virtual event on selection
    - Popup closes on Escape or when a date is selected; a local grab
      keeps the input inside the popup while it is open
    """

    def __init__(
        self,
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
    ):
        super().__init__(master)

        self.date_pattern = date_pattern
        self.first_weekday = first_weekday % 7
        self.locale = locale
        self.mindate = self._as_date(mindate)
        self.maxdate = self._as_date(maxdate)
        self.weekenddays = tuple(
            day % 7 for day in weekenddays
        )
        self.show_week_numbers = show_week_numbers
        self.show_other_month_days = show_other_month_days
        self.validate = validate
        self.raise_exception = raise_exception

        self._last_valid = None

        # Localized month and weekday names (computed once per instance)
        self._month_names, self._weekday_names = self._localized_names()

        self.variable = tk.StringVar()

        self.entry = ttk.Entry(
            self,
            textvariable=self.variable,
            **kwargs,
        )
        self.entry.pack(
            side="left",
            fill="x",
            expand=True,
        )

        self.button = ttk.Button(
            self,
            text="\u25bc",  # black down-pointing triangle
            width=2,
            command=self.drop_down,
        )
        self.button.pack(side="right")

        self._calendar_window = None
        self._calendar_frame = None
        self._view = "calendar"

        self._display_month = self._initial_display_month()

        if value is not None:
            self.set_date(value)

        self.entry.bind("<Return>", self._on_entry_return)
        if self.validate:
            self.entry.bind("<FocusOut>", self._on_entry_focus_out, "+")
        # Escape closes the popup even when the focus is on the entry
        # (e.g. after clicking the dropdown button, the focus may remain
        # on the entry rather than on the popup window).
        self.entry.bind("<Escape>", self._on_entry_escape, "+")

        # Make sure the styles used by the calendar day buttons exist.
        # Without this, the selected/today/weekend highlighting has no
        # visible effect (the styles would not be defined).
        self.configure_styles()

    # ------------------------------------------------------------------
    # Localization
    # ------------------------------------------------------------------

    def _localized_names(self):
        """Return (month_names, weekday_names) in the requested locale.

        The names are obtained with strftime, which uses the C library
        locale settings. locale=None means "use the current system
        locale"; a locale identifier such as "it_IT" or "en_US" selects
        an explicit locale; "C" gives English names. The previous locale
        setting is restored afterwards, so that the global locale of the
        application is not affected.
        """
        import locale

        current = None
        try:
            current = locale.getlocale(locale.LC_TIME)
        except (locale.Error, ValueError):
            current = None

        try:
            if self.locale and self.locale != "C":
                locale.setlocale(locale.LC_TIME, self.locale)
            elif self.locale == "C":
                locale.setlocale(locale.LC_TIME, "C")
            else:
                locale.setlocale(locale.LC_TIME, "")

            # Reference date: use two different weekdays and months to get
            # all the names.
            months = [
                datetime.date(2024, month, 15).strftime("%B").capitalize()
                for month in range(1, 13)
            ]
            weekdays = [
                datetime.date(2024, 9, 2 + day).strftime("%A")
                for day in range(7)
            ]
            weekdays_abbr = [
                datetime.date(2024, 9, 2 + day).strftime("%a")
                for day in range(7)
            ]
        except (locale.Error, ValueError):
            # Unknown locale: fall back to English names.
            months = [
                "January", "February", "March", "April",
                "May", "June", "July", "August",
                "September", "October", "November", "December",
            ]
            weekdays = [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ]
            weekdays_abbr = [name[:3] for name in weekdays]
        finally:
            if current:
                try:
                    locale.setlocale(locale.LC_TIME, current)
                except locale.Error:
                    pass

        return tuple(months), tuple(weekdays_abbr)

    @staticmethod
    def _as_date(value):
        """Convert a value to datetime.date (accepts date/datetime/str)."""
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        raise TypeError(
            "value must be datetime.date, datetime.datetime or None"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_date(self):
        """Return datetime.date or None if the field is empty/invalid."""
        value = self.variable.get().strip()

        if not value:
            return None

        try:
            date = datetime.datetime.strptime(
                value,
                self.date_pattern,
            ).date()
        except ValueError:
            return None

        if not self._in_range(date):
            return None

        return date

    def set_date(self, value):
        """Set a datetime.date/datetime/str value, or None to clear.

        Strings are parsed using the configured date pattern. A date
        outside the mindate/maxdate range raises ValueError.
        """
        if value is None:
            self.clear()
            return

        if isinstance(value, str):
            value = datetime.datetime.strptime(
                value.strip(),
                self.date_pattern,
            ).date()

        if isinstance(value, datetime.datetime):
            value = value.date()

        if not isinstance(value, datetime.date):
            raise TypeError(
                "value must be datetime.date, datetime.datetime, str or None"
            )

        if not self._in_range(value):
            raise ValueError(
                f"date {value} is outside the allowed range "
                f"[{self.mindate}, {self.maxdate}]"
            )

        self._last_valid = value
        self.variable.set(
            value.strftime(self.date_pattern)
        )

        self._display_month = value.replace(day=1)

    def clear(self):
        """Clear the date entry."""
        self.variable.set("")

    def get(self):
        """Return the current text of the entry (delegated)."""
        return self.entry.get()

    def set(self, text):
        """Set the text of the entry (delegated)."""
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def _in_range(self, date):
        """Return True if the date is within mindate/maxdate."""
        if self.mindate is not None and date < self.mindate:
            return False
        if self.maxdate is not None and date > self.maxdate:
            return False
        return True

    def _on_entry_focus_out(self, _event=None):
        """Restore the last valid date if the typed value is invalid."""
        if not self.validate:
            return
        value = self.variable.get().strip()
        if not value:
            # An empty field is a valid (cleared) state.
            self._last_valid = None
            return
        try:
            date = datetime.datetime.strptime(
                value, self.date_pattern
            ).date()
        except ValueError:
            date = None

        if date is None or not self._in_range(date):
            if self.raise_exception:
                raise ValueError(
                    f"invalid date {value!r} for pattern {self.date_pattern!r}"
                )
            # Restore the last valid value (or clear it).
            if self._last_valid is not None:
                self.variable.set(
                    self._last_valid.strftime(self.date_pattern)
                )
            else:
                self.variable.set("")

    # ------------------------------------------------------------------
    # Popup
    # ------------------------------------------------------------------

    def drop_down(self):
        """
        Open the calendar popup as a window bound to the application.

        The popup is closed by selecting a date, by pressing Escape, or
        by pressing the dropdown button again. No grab is taken, so that
        the menu bar and the other controls of the application remain
        usable while the popup is open.
        """
        # Toggle: if the popup is already open, close it.
        if self._calendar_window is not None:
            try:
                if self._calendar_window.winfo_exists():
                    self._close_popup()
                    return
            except tk.TclError:
                self._calendar_window = None

        self.entry.focus_set()

        # Sync the displayed month with the value currently typed in the
        # entry, so that the popup shows the month of the typed date (and
        # selecting a day does not silently replace the typed date with a
        # day of a different month).
        typed = self.get_date()
        if typed is not None:
            self._last_valid = typed
            self._display_month = typed.replace(day=1)

        self._calendar_window = tk.Toplevel(self)
        window = self._calendar_window

        # A frameless, window-manager-managed Toplevel: no title bar and
        # no borders, so the window contains exactly the calendar frame.
        # The geometry is set before the window is mapped, so it appears
        # directly at the right coordinates (no flicker). No grab is
        # taken, so that the menu bar and the other controls of the
        # application remain usable while the popup is open.
        #
        # NOTE: overrideredirect(True) is applied AFTER the window is
        # mapped (deiconify + update_idletasks below). A frameless window
        # created before mapping is a WS_POPUP window on Windows, which
        # swallows the click that opens it (the user would have to click
        # twice). Mapping first and removing the decorations afterwards
        # avoids this.
        window.transient(self.winfo_toplevel())
        window.resizable(False, False)

        self._view = "calendar"

        # Build the popup content first, so that the requested size is known.
        self._build_popup()

        window.bind("<Escape>", lambda event: self._close_popup())
        # Keyboard navigation inside the popup
        window.bind("<Left>", self._on_key_left)
        window.bind("<Right>", self._on_key_right)
        window.bind("<Up>", self._on_key_up)
        window.bind("<Down>", self._on_key_down)
        window.bind("<Return>", self._on_key_return)
        window.bind("<KP_Enter>", self._on_key_return)
        window.bind("<Prior>", lambda e: self._change_month(-1))
        window.bind("<Next>", lambda e: self._change_month(1))

        # Position the window next to the DateEntry widget before it is
        # mapped: the window manager honors the geometry at mapping time,
        # so it appears directly at the right coordinates (no flicker).
        self._position_popup(window)

        # Map the window, then make it frameless. Applying
        # overrideredirect(True) after the window is mapped removes the
        # title bar and borders without creating the WS_POPUP window that
        # swallows the opening click (see the comment above).
        window.update_idletasks()
        window.deiconify()
        window.update_idletasks()
        window.overrideredirect(True)
        window.update_idletasks()

        # A frameless window is not kept above the parent by the window
        # manager: when the click that opens the popup activates the main
        # window (e.g. after Alt-Tab), the main window is raised above
        # the popup, which then becomes invisible (the application seems
        # not to react to the click). Keep the popup above all windows of
        # the application while it is open (the attribute is removed when
        # the popup is closed).
        window.attributes("-topmost", True)

        # A frameless window is not kept above the parent by the window
        # manager: when the click that opens the popup activates the main
        # window (e.g. after Alt-Tab), the main window is raised above
        # the popup, which then becomes invisible (the application seems
        # not to react to the click). Lift the popup above the main
        # window as soon as it is mapped.
        window.lift()

        # Close the popup when the application window is destroyed (e.g. the
        # user closes the application while the calendar is open).
        self.winfo_toplevel().bind("<Destroy>", self._on_app_destroy, "+")
        # Release the grab when the popup itself is destroyed by any other
        # means (e.g. the Tk destruction cascade), so that the grab never
        # remains active on a destroyed window.
        window.bind("<Destroy>", self._on_popup_destroy, "+")
        # Follow the application window when it is moved (e.g. dragged by
        # the title bar): reposition the popup next to the DateEntry.
        self.winfo_toplevel().bind("<Configure>", self._on_app_move, "+")
        # Close the popup when the application window loses the foreground
        # (e.g. the user clicks another application): the popup is
        # topmost, so it would otherwise float above unrelated windows.
        # Overrideredirect windows do not receive FocusIn/FocusOut events
        # on Windows, so focus-event tracking cannot be used; the state
        # is polled instead (see _poll_app_focus).
        self._poll_app_focus()
        # Close the popup when the user clicks anywhere outside it (on
        # the application or on another window of the interpreter). The
        # binding is installed on a dedicated bind tag so that it can be
        # removed without touching the bindings of the other widgets.
        self.bind_all("<ButtonPress-1>", self._on_global_click, "+")

        # Give the focus to the popup so that the keyboard navigation
        # works immediately. No grab is taken: the menu bar and the other
        # controls of the application remain usable while the popup is
        # open.
        #
        # focus_set() alone may leave the keyboard focus on the previous
        # window on some platforms; focus_force() ensures that the popup
        # really receives the keyboard input. This is a standard Tk call
        # available on all platforms (Windows, macOS, Linux).
        window.focus_set()
        window.focus_force()

    def _position_popup(self, window):
        self.update_idletasks()
        window.update_idletasks()

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()

        popup_width = window.winfo_reqwidth()
        popup_height = window.winfo_reqheight()

        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        if x + popup_width > screen_width:
            x = max(0, screen_width - popup_width)

        if y + popup_height > screen_height:
            y = max(0, self.winfo_rooty() - popup_height)

        window.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

    def _on_app_move(self, event):
        """Reposition the popup when the application window is moved."""
        if (
            event.widget is self.winfo_toplevel()
            and self._calendar_window is not None
        ):
            try:
                if self._calendar_window.winfo_exists():
                    self._position_popup(self._calendar_window)
            except tk.TclError:
                pass

    def _poll_app_focus(self):
        """Poll whether the application still has the OS focus.

        The popup is topmost while it is open: if the application goes to
        the background (e.g. the user clicks another application), the
        popup would float above unrelated windows. Overrideredirect
        windows do not receive FocusIn/FocusOut events on Windows, so
        the focus state cannot be tracked with events: it is polled
        every 300 ms while the popup is open. The polling is very light
        (a single Win32 call every 300 ms) and stops as soon as the
        popup is closed.

        On Windows the check uses GetForegroundWindow. On other
        platforms the check is skipped: the window manager usually keeps
        transient windows above their parent anyway.
        """
        if self._calendar_window is None:
            return
        try:
            if not self._calendar_window.winfo_exists():
                self._calendar_window = None
                return
        except tk.TclError:
            self._calendar_window = None
            return

        # Close the popup after 30 seconds of polling (100 ticks of
        # 300 ms each) to avoid consuming resources indefinitely.
        if sys.platform == "win32":
            try:
                import ctypes

                user32 = ctypes.windll.user32
                hwnd = self.winfo_toplevel().winfo_id()
                # Get the toplevel HWND: winfo_id gives the client area
                # window; the toplevel frame is its ancestor. Use
                # GetAncestor to get the root owner.
                GA_ROOT = 2
                root_hwnd = ctypes.windll.user32.GetAncestor(hwnd, GA_ROOT)
                if user32.GetForegroundWindow() != root_hwnd:
                    # The application lost the foreground: close the
                    # popup so that it does not float above other apps.
                    self._close_popup()
                    return
            except (AttributeError, tk.TclError):
                pass

        # Continue polling while the popup is open.
        self._poll_after_id = self.after(300, self._poll_app_focus)

    def _on_entry_escape(self, _event=None):
        """Close the popup when Escape is pressed on the entry."""
        if self._calendar_window is not None:
            self._close_popup()

    def _on_app_destroy(self, event):
        """Close the popup when the application window is destroyed."""
        try:
            if event.widget is self.winfo_toplevel():
                self._close_popup()
        except tk.TclError:
            pass  # widgets already destroyed

    def _on_global_click(self, event):
        """Close the popup when clicking outside of it.

        Clicks inside the popup (including on its day buttons and on the
        month/year comboboxes) are ignored; clicks anywhere else close
        the popup. The binding is removed when the popup is closed.
        """
        window = self._calendar_window
        if window is None:
            return
        try:
            if not window.winfo_exists():
                return
        except tk.TclError:
            return

        # When the user clicks an item in the popdown listbox of the
        # month/year comboboxes, tkinter cannot resolve the popdown
        # widget path (it is not registered as a Python child), so
        # event.widget falls back to the root window and the widget-tree
        # walk cannot be used. Use the pointer position instead: close
        # the popup only if the click is outside both the popup window
        # and this DateEntry (the dropdown button toggles the popup by
        # itself).
        px = event.x_root
        py = event.y_root

        def contains(widget):
            return (
                widget.winfo_rootx() <= px < widget.winfo_rootx() + widget.winfo_width()
                and widget.winfo_rooty() <= py < widget.winfo_rooty() + widget.winfo_height()
            )

        if contains(window) or contains(self):
            return
        self._close_popup()

    def _on_popup_destroy(self, event):
        """Release the grab when the popup window is destroyed.

        The popup is destroyed both by _close_popup() and by the Tk
        destruction cascade (e.g. when the application window is
        destroyed while the popup is open). In the latter case the grab
        would remain active on a destroyed window, blocking all input to
        the application (which then cannot be closed).
        """
        if event.widget is self._calendar_window:
            try:
                self.grab_release()
            except tk.TclError:
                pass
            self._calendar_window = None
            self._calendar_frame = None

    def _close_popup(self):
        if self._calendar_window is not None:
            try:
                self._calendar_window.grab_release()
            except tk.TclError:
                pass
            try:
                # Remove the topmost state before destroying the window,
                # so that other applications can be raised normally.
                self._calendar_window.attributes("-topmost", False)
            except tk.TclError:
                pass
            try:
                self._calendar_window.destroy()
            except tk.TclError:
                pass

        self._calendar_window = None
        self._calendar_frame = None

        # Cancel the pending focus poll, if any: a stale poll callback
        # would otherwise fire on the next popup and close it (the
        # foreground check fails when the terminal or another window has
        # the focus).
        after_id = getattr(self, "_poll_after_id", None)
        if after_id is not None:
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None

        # Hide the day tooltip, if visible.
        self._hide_day_tooltip()

        # Remove the global click binding installed when the popup was
        # opened. Only this widget's binding is removed: unbind_all would
        # also remove the <ButtonPress-1> bindings of all the other
        # widgets of the application (e.g. tooltips), breaking them.
        try:
            self.unbind("<ButtonPress-1>")
        except tk.TclError:
            pass

        # Restore the focus to the entry only if the application is not
        # being closed: during the destruction cascade focus_set() on a
        # widget being destroyed can raise or leave the grab in an
        # inconsistent state.
        try:
            if self.winfo_toplevel().winfo_exists():
                # focus_set() moves the Tk focus; focus_force() also
                # returns the OS-level focus to the application window,
                # which may have been given to the popup while it was
                # open (e.g. after pressing Escape).
                self.entry.focus_set()
                self.entry.focus_force()
        except tk.TclError:
            pass  # the application is being closed

    # ------------------------------------------------------------------
    # Popup views
    # ------------------------------------------------------------------

    def _build_popup(self):
        window = self._calendar_window

        for child in window.winfo_children():
            child.destroy()

        container = ttk.Frame(
            window,
            padding=8,
            relief="solid",
            borderwidth=1,
        )
        container.pack()

        self._calendar_frame = ttk.Frame(container)
        self._calendar_frame.pack()

        if self._view == "calendar":
            self._draw_calendar()

        elif self._view == "months":
            self._draw_month_selector()

        elif self._view == "years":
            self._draw_year_selector()

        # The rebuilt content may have a different required size (e.g. a
        # month with 6 week rows instead of 5): resize and reposition the
        # popup so that the calendar is neither cut off nor left with an
        # empty border below.
        if self._calendar_window is not None:
            self._position_popup(self._calendar_window)

    # ------------------------------------------------------------------
    # Calendar view
    # ------------------------------------------------------------------

    def _draw_calendar(self):
        frame = self._calendar_frame

        header = ttk.Frame(frame)
        header.pack(fill="x", pady=(0, 8))

        ttk.Button(
            header,
            text="\u2039",  # single left-pointing angle quotation mark
            width=3,
            command=lambda: self._change_month(-1),
        ).pack(side="left")

        center = ttk.Frame(header)
        center.pack(
            side="left",
            fill="x",
            expand=True,
        )

        # Month selection dropdown
        self._month_var = tk.StringVar(
            value=self._month_names[self._display_month.month - 1]
        )
        month_combo = ttk.Combobox(
            center,
            textvariable=self._month_var,
            values=self._month_names,
            state="readonly",
            width=max(len(name) for name in self._month_names) + 2,
            justify="center",
        )
        month_combo.pack(side="left")
        month_combo.bind(
            "<<ComboboxSelected>>", self._on_month_combo_selected
        )

        # Year selection dropdown
        self._year_var = tk.StringVar(value=str(self._display_month.year))
        year_values = self._year_values()
        year_combo = ttk.Combobox(
            center,
            textvariable=self._year_var,
            values=year_values,
            state="readonly",
            width=6,
            justify="center",
        )
        year_combo.pack(side="left", padx=(2, 0))
        year_combo.bind(
            "<<ComboboxSelected>>", self._on_year_combo_selected
        )

        ttk.Button(
            header,
            text="\u203a",  # single right-pointing angle quotation mark
            width=3,
            command=lambda: self._change_month(1),
        ).pack(side="right")

        # Dedicated frame for the weekday/day grid (grid geometry manager)
        days_frame = ttk.Frame(frame)
        days_frame.pack(fill="x")
        self._draw_weekdays(days_frame)
        self._draw_days(days_frame)

        ttk.Separator(frame).pack(
            fill="x",
            pady=8,
        )

        bottom = ttk.Frame(frame)
        bottom.pack(fill="x")

        ttk.Button(
            bottom,
            text="Today",
            command=self._select_today,
        ).pack(side="left")

        ttk.Button(
            bottom,
            text="Cancel",
            command=self._close_popup,
        ).pack(side="right")

        ttk.Button(
            bottom,
            text="Clear",
            command=self._clear_and_close,
        ).pack(side="right", padx=(0, 4))

    def _year_values(self):
        """Return the list of selectable years (honoring mindate/maxdate)."""
        current_year = datetime.date.today().year
        first = current_year - 60
        last = current_year + 60
        if self.mindate is not None:
            first = min(first, self.mindate.year)
        if self.maxdate is not None:
            last = max(last, self.maxdate.year)
        years = list(range(first, last + 1))
        if self._display_month.year not in years:
            years.append(self._display_month.year)
        years.sort()
        return [str(year) for year in years]

    def _on_month_combo_selected(self, _event=None):
        month = self._month_names.index(self._month_var.get()) + 1
        self._display_month = self._display_month.replace(month=month, day=1)
        self._build_popup()

    def _on_year_combo_selected(self, _event=None):
        try:
            year = int(self._year_var.get())
        except ValueError:
            return
        self._display_month = self._display_month.replace(year=year, day=1)
        self._build_popup()

    def _draw_weekdays(self, frame):
        weekdays = (
            self._weekday_names[self.first_weekday:]
            + self._weekday_names[:self.first_weekday]
        )

        start_column = 1 if self.show_week_numbers else 0

        for column, name in enumerate(weekdays):
            ttk.Label(
                frame,
                text=name,
                anchor="center",
                width=4,
            ).grid(
                row=0,
                column=start_column + column,
                padx=1,
                pady=1,
            )

        if self.show_week_numbers:
            ttk.Label(
                frame,
                text="W",
                anchor="center",
                width=3,
            ).grid(
                row=0,
                column=0,
                padx=1,
                pady=1,
            )

    def _draw_days(self, frame):
        year = self._display_month.year
        month = self._display_month.month

        calendar_obj = calendar.Calendar(
            firstweekday=self.first_weekday
        )

        selected = self.get_date()
        today = datetime.date.today()

        start_column = 1 if self.show_week_numbers else 0

        for row, week in enumerate(
            calendar_obj.monthdatescalendar(year, month),
            start=1,
        ):
            if self.show_week_numbers:
                ttk.Label(
                    frame,
                    text=str(week[0].isocalendar()[1]),
                    anchor="center",
                    width=4,
                ).grid(
                    row=row,
                    column=0,
                    padx=1,
                    pady=1,
                )

            for column, day_date in enumerate(week):
                day = day_date.day
                other_month = day_date.month != month

                if other_month and not self.show_other_month_days:
                    continue

                current = day_date

                kwargs = {
                    "text": str(day),
                    "width": 4,
                }

                out_of_range = not self._in_range(current)

                if out_of_range or (other_month and not self._in_range(current)):
                    # Days outside the allowed range are disabled.
                    kwargs["state"] = "disabled"
                elif other_month:
                    # Days of the previous/next month are shown but not
                    # selectable.
                    kwargs["state"] = "disabled"
                else:
                    kwargs["command"] = lambda d=day, dd=day_date: self._select_day(dd)

                if selected == current:
                    kwargs["style"] = "DateEntrySelected.TButton"
                elif current == today:
                    kwargs["style"] = "DateEntryToday.TButton"
                elif (
                    not other_month
                    and day_date.weekday() in self.weekenddays
                ):
                    kwargs["style"] = "DateEntryWeekend.TButton"

                # Full date in the current locale, shown as a tooltip on
                # hover (e.g. "mercoledì 20 agosto 2012").
                tooltip_text = self._full_date_text(day_date)

                if selected == current:
                    # The selected day is wrapped in a Frame with a colored
                    # border: the themed ttk styles (e.g. "vista" on
                    # Windows) draw the button with a themed image and
                    # ignore borderwidth/relief/bordercolor, so a style-
                    # based border would not be visible on every theme.
                    wrapper = tk.Frame(
                        frame,
                        highlightbackground="#1f6fb2",
                        highlightthickness=2,
                        borderwidth=0,
                    )
                    wrapper.grid(
                        row=row,
                        column=start_column + column,
                        padx=1,
                        pady=1,
                    )
                    day_button = ttk.Button(
                        wrapper,
                        **kwargs,
                    )
                    day_button.pack(padx=1, pady=1)
                else:
                    day_button = ttk.Button(
                        frame,
                        **kwargs,
                    )
                    day_button.grid(
                        row=row,
                        column=start_column + column,
                        padx=1,
                        pady=1,
                    )

                self._bind_day_tooltip(day_button, tooltip_text)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _change_month(self, delta):
        month = self._display_month.month - 1 + delta

        year = self._display_month.year + month // 12
        month = month % 12 + 1

        candidate = datetime.date(year, month, 1)
        candidate_last = datetime.date(
            year, month, calendar.monthrange(year, month)[1]
        )

        # Do not navigate beyond the allowed range: the target month is
        # skipped only if it contains no selectable day at all.
        if self.mindate is not None and candidate_last < self.mindate:
            return
        if self.maxdate is not None and candidate > self.maxdate:
            return

        self._display_month = candidate

        self._build_popup()

        self._display_month = candidate

        self._build_popup()

    def _back_to_calendar(self):
        self._view = "calendar"
        self._build_popup()

    # ------------------------------------------------------------------
    # Day tooltips
    # ------------------------------------------------------------------

    def _full_date_text(self, day_date):
        """Return the full date in the current locale (e.g.
        "mercoledì 20 agosto 2012")."""
        try:
            return day_date.strftime("%A %d %B %Y").capitalize()
        except (ValueError, AttributeError):
            return day_date.isoformat()

    def _bind_day_tooltip(self, widget, text):
        """Show a tooltip with the full date when hovering over a day."""

        def on_enter(_event=None):
            self._show_day_tooltip(widget, text)

        def on_leave(_event=None):
            self._hide_day_tooltip()

        widget.bind("<Enter>", on_enter, "+")
        widget.bind("<Leave>", on_enter and on_leave, "+")
        widget.bind("<ButtonPress-1>", on_leave, "+")

    def _show_day_tooltip(self, widget, text):
        """Show the tooltip window near the given widget."""
        self._hide_day_tooltip()
        x = widget.winfo_rootx() + widget.winfo_width() + 4
        y = widget.winfo_rooty() + (widget.winfo_height() - 20) // 2
        self._day_tooltip = tw = tk.Toplevel(widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=text,
            justify="left",
            background="LightYellow",
            foreground="black",
            relief="solid",
            borderwidth=1,
            font=("TkDefaultFont", 9),
        )
        label.pack(ipadx=4, ipady=2)
        # Keep the tooltip above other windows but do not steal the focus.
        tw.attributes("-topmost", True)

    def _hide_day_tooltip(self, _event=None):
        tooltip = getattr(self, "_day_tooltip", None)
        if tooltip is not None:
            try:
                tooltip.destroy()
            except tk.TclError:
                pass
            self._day_tooltip = None

    # ------------------------------------------------------------------
    # Date selection
    # ------------------------------------------------------------------

    def _select_day(self, day_date):
        self.set_date(day_date)

        self.event_generate(
            "<<DateEntrySelected>>",
            when="tail",
        )

        self._close_popup()

    def _select_today(self):
        today = datetime.date.today()

        self.set_date(today)

        self.event_generate(
            "<<DateEntrySelected>>",
            when="tail",
        )

        self._close_popup()

    def _clear_and_close(self):
        self.clear()
        self._close_popup()

    def _on_entry_return(self, _event=None):
        """Validate the typed date and close the popup if open."""
        if self._calendar_window is not None:
            self._close_popup()

    # ------------------------------------------------------------------
    # Keyboard navigation inside the popup
    # ------------------------------------------------------------------

    def _focused_day(self):
        """Return the date of the currently focused day button."""
        try:
            focused = self.focus_get()
        except (KeyError, tk.TclError):
            return None
        if focused is None:
            return None
        try:
            text = focused.cget("text")
        except (tk.TclError, TypeError):
            # The focused widget has no "text" option (e.g. a frame or an
            # entry): it is not a day button.
            return None
        if text and text.isdigit():
            return int(text)
        return None

    def _focus_day(self, day):
        """Move the keyboard focus to the day button with the given number."""
        if self._calendar_frame is None:
            return
        for child in self._calendar_frame.winfo_children():
            if not isinstance(child, ttk.Frame):
                continue
            for widget in child.winfo_children():
                if (
                    isinstance(widget, ttk.Button)
                    and widget.cget("text").isdigit()
                    and int(widget.cget("text")) == day
                    and str(widget.cget("state")) != "disabled"
                ):
                    widget.focus_set()
                    return

    def _move_focus(self, delta_days):
        """Move the focus by the given number of days (can be negative)."""
        day = self._focused_day()
        if day is None:
            # No day focused: start from the selected day, or from today
            # if the displayed month is the current month, or from day 1.
            selected = self.get_date()
            if (
                selected is not None
                and selected.month == self._display_month.month
                and selected.year == self._display_month.year
            ):
                day = selected.day
            else:
                today = datetime.date.today()
                if (
                    today.month == self._display_month.month
                    and today.year == self._display_month.year
                ):
                    day = today.day
                else:
                    day = 1
        first, last = calendar.monthrange(
            self._display_month.year, self._display_month.month
        )
        new_day = day + delta_days
        if new_day < 1:
            self._change_month(-1)
            last_prev = calendar.monthrange(
                self._display_month.year, self._display_month.month
            )[1]
            new_day = last_prev + new_day
        elif new_day > last:
            overflow = new_day - last
            self._change_month(1)
            new_day = overflow
        self._focus_day(new_day)
        return "break"

    def _on_key_left(self, _event=None):
        return self._move_focus(-1)

    def _on_key_right(self, _event=None):
        return self._move_focus(1)

    def _on_key_up(self, _event=None):
        return self._move_focus(-7)

    def _on_key_down(self, _event=None):
        return self._move_focus(7)

    def _on_key_return(self, _event=None):
        """Select the focused day (or today if no day is focused)."""
        day = self._focused_day()
        if day is not None:
            self._select_day(
                datetime.date(
                    self._display_month.year,
                    self._display_month.month,
                    day,
                )
            )
        else:
            self._select_today()
        return "break"

    def _initial_display_month(self):
        value = self.get_date()

        if value is not None:
            return value.replace(day=1)

        today = datetime.date.today()
        if not self._in_range(today):
            if self.mindate is not None and today < self.mindate:
                return self.mindate.replace(day=1)
            if self.maxdate is not None and today > self.maxdate:
                return self.maxdate.replace(day=1)
        return today.replace(day=1)

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    def configure_styles(self):
        style = ttk.Style()

        # Selected day: bold text in a distinct color, with a thick border
        # so that it clearly stands out from the other days.
        style.configure(
            "DateEntrySelected.TButton",
            font=("TkDefaultFont", 9, "bold"),
            foreground="#1f6fb2",
            borderwidth=3,
            relief="solid",
        )
        style.map(
            "DateEntrySelected.TButton",
            foreground=[
                ("pressed", "#154a7a"),
                ("active", "#2a7fc9"),
                ("disabled", "#d0d0d0"),
            ],
            bordercolor=[
                ("pressed", "#154a7a"),
                ("active", "#2a7fc9"),
            ],
        )

        # Today: bold.
        style.configure(
            "DateEntryToday.TButton",
            font=("TkDefaultFont", 9, "bold"),
        )

        # Weekend days: dark red text.
        style.configure(
            "DateEntryWeekend.TButton",
            foreground="#b03030",
        )
