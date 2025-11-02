"""
quran_visualizer.py
====================

An interactive program that lays out the entire Arabic Qurʼān on a square
grid.  Each word in the Qurʼān is represented by a coloured cell whose
colour corresponds to its sura (chapter).  The program fetches the
authoritative Uthmānī script of the Qurʼān from the public
``alquran.cloud`` API and then arranges every word sequentially into a
square grid whose side length is the ceiling of the square‑root of the
total number of words.  Cells are tiny coloured squares to ensure the
whole Qurʼān fits into a reasonably sized view.  When the user hovers
over or clicks on a cell the original Arabic word, its sura and ayah
location are displayed in a status bar.  Search tools allow users to
highlight cells matching a given word, root or phonological pattern (see
below), or to highlight all cells belonging to a selected sura or ayah.

Key features
------------

* **Sura‑coded colours:** Each of the 114 suras receives a unique hue on
  the colour wheel.  Cells belonging to the same sura share the same
  colour which makes sura boundaries immediately visible.
* **Square layout:** Words are placed left‑to‑right, top‑to‑bottom into
  a square whose side length is ``ceil(sqrt(N_words))``.  Empty cells at
  the end of the square are simply left blank.
* **Interactive inspection:** Hovering over a cell shows the word,
  its sura number and ayah number.  Clicking a cell fixes the
  information display so that it does not change until another cell is
  clicked.
* **Search functionality:** A control panel allows users to perform
  several types of search:

  - **Word search:** highlight cells containing the search term.  The
    search ignores diacritics and case.
  - **Ayah search:** highlight all cells belonging to a given sura and
    ayah (for example ``2:255``).
  - **Root search:** a simple heuristic for finding words built on a
    given triliteral root.  The search removes diacritics and looks
    for the root letters in sequence (not necessarily consecutively) in
    the simplified word.  This does not perform full morphological
    analysis but is a pragmatic approximation useful for exploration.
  - **Phonological pattern search:** highlight words whose simplified
    Arabic representation contains a specified substring.  This can be
    used to find rhyming patterns or repeated phoneme sequences.

* **Connection lines:** Optionally draw lines connecting highlighted
  cells to visualise relations between occurrences of the search term.

Because the program eschews external libraries for Arabic natural
language processing, the root search uses a very simple heuristic
instead of a proper morphological analyser.  Nevertheless, it provides
a useful starting point for exploring lexical patterns without any
dependencies beyond the Python standard library and ``tkinter``.

To run the program, simply execute this file with Python 3.  A network
connection is required on first launch to download the Qurʼān text
from ``api.alquran.cloud``.  If that service is unavailable, you can
replace ``QURAN_API_URL`` with another endpoint that returns JSON in
the same structure.
"""

import json
import math
import threading
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except ImportError as exc:
    raise SystemExit(
        "The `requests` library is required. It should be available in this environment."
    ) from exc

# Tkinter is imported lazily so that this module can be imported in
# environments without GUI support (e.g. for testing helper
# functions).  When running the GUI, ``main()`` will attempt to
# import Tkinter and exit with a clear message if it fails.
tk = None  # type: ignore
ttk = None  # type: ignore
messagebox = None  # type: ignore

def _import_tkinter() -> None:
    """Attempt to import Tkinter and populate global references.

    This helper should be called when constructing the GUI.  It
    populates the global variables ``tk``, ``ttk`` and ``messagebox``
    on success, otherwise raises ``ImportError``.
    """
    global tk, ttk, messagebox
    if tk is not None:
        return
    try:
        import tkinter as _tk
        from tkinter import ttk as _ttk, messagebox as _messagebox
    except ImportError as exc:
        raise ImportError(
            "Tkinter is required to run the GUI. Please install it or use a different environment."
        ) from exc
    tk = _tk
    ttk = _ttk
    messagebox = _messagebox


###############################################################################
# Data structures


@dataclass
class WordCell:
    """Metadata for a single word cell in the grid."""

    text: str            # The original Arabic word with diacritics
    clean: str           # The word after removing diacritics and punctuation
    sura: int            # Sura index (1‑based)
    ayah: int            # Ayah index within its sura (1‑based)
    canvas_id: Optional[int] = None  # Tkinter canvas item id
    row: int = 0         # Row position in grid
    col: int = 0         # Column position in grid


###############################################################################
# Helper functions


def remove_diacritics(text: str) -> str:
    """Return a version of the input string with all combining marks removed.

    This function strips Arabic diacritics (e.g. Harakat) by discarding
    characters whose Unicode category is ``Mn`` (Non‑spacing mark).  It
    also removes tatweel (U+0640) and some punctuation.  The result is
    used for normalised comparison and pattern matching.
    """
    # Normalise to NFKD form to separate base letters from combining marks
    decomposed = unicodedata.normalize("NFKD", text)
    cleaned_chars = []
    for ch in decomposed:
        cat = unicodedata.category(ch)
        # Skip combining marks and tatweel
        if cat == "Mn" or ch == "\u0640":
            continue
        # Skip punctuation from Arabic and ASCII ranges
        if cat.startswith("P") or cat in {"«", "»", "،", "؛", "؟"}:
            continue
        cleaned_chars.append(ch)
    return "".join(cleaned_chars)


def load_quran_text(api_url: str) -> List[WordCell]:
    """Download the Qurʼān text from a remote API and return a list of WordCell objects.

    This helper retains backwards‑compatibility with the original implementation
    which expected to fetch the Qurʼān from an HTTP endpoint returning a JSON
    structure with ``data.surahs``.  The resulting list of ``WordCell``
    instances records each word's original form, a diacritics‑stripped version
    (via :func:`remove_diacritics`), and its sura and ayah numbers.

    Parameters
    ----------
    api_url: str
        Endpoint that returns JSON with a top level ``data.surahs`` list.
        Each sura should have ``number`` and ``ayahs`` where each ayah
        has ``number`` and ``text`` fields.

    Returns
    -------
    List[WordCell]
        A flat list of word metadata objects.

    """
    print("Fetching Qurʼān text from", api_url)
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        raise SystemExit(f"Failed to fetch Qurʼān text: {exc}")
    payload = response.json()
    if payload.get("code") != 200:
        raise SystemExit(
            f"Unexpected response code {payload.get('code')}: {payload.get('status')}"
        )
    surahs = payload["data"]["surahs"]
    words: List[WordCell] = []
    for sura in surahs:
        sura_number = sura.get("number")
        for ayah in sura.get("ayahs", []):
            ayah_number = ayah.get("numberInSurah")
            text = ayah.get("text", "").strip()
            # Some API responses include an invisible BOM at the start
            if text.startswith("\ufeff"):
                text = text.lstrip("\ufeff")
            tokens = text.split()
            for token in tokens:
                clean_token = remove_diacritics(token)
                if not clean_token:
                    continue
                words.append(
                    WordCell(
                        text=token,
                        clean=clean_token,
                        sura=sura_number,
                        ayah=ayah_number,
                    )
                )
    return words


def load_quran_local(path: str) -> List[WordCell]:
    """Load Qurʼān text from a local JSON file.

    The file should contain a mapping from sura numbers (as strings)
    to lists of verses.  Each verse is expected to have keys
    ``chapter`` (the sura number), ``verse`` (the ayah number within
    the sura) and ``text`` (the Arabic text).  This format matches the
    structure of the public ``quran-json`` dataset hosted on GitHub.

    Parameters
    ----------
    path: str
        Path to a JSON file on disk.

    Returns
    -------
    List[WordCell]
        A flat list of word metadata objects.

    Examples
    --------
    >>> words = load_quran_local("/path/to/quran.json")
    >>> len(words)  # number of words in the Qurʼān
    77430

    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    words: List[WordCell] = []
    for sura_key, verses in data.items():
        try:
            sura_number = int(sura_key)
        except ValueError:
            # Skip unexpected keys
            continue
        for verse in verses:
            ayah_number = verse.get("verse")
            text = verse.get("text", "").strip()
            if text.startswith("\ufeff"):
                text = text.lstrip("\ufeff")
            tokens = text.split()
            for token in tokens:
                clean_token = remove_diacritics(token)
                if not clean_token:
                    continue
                words.append(
                    WordCell(
                        text=token,
                        clean=clean_token,
                        sura=sura_number,
                        ayah=ayah_number,
                    )
                )
    return words


def generate_colour_map(num_items: int) -> List[str]:
    """Generate a list of visually distinct colours for sura coding.

    Colours are generated by evenly spacing hues around the colour wheel
    (0‑360°) while keeping saturation and value fixed.  The returned
    strings are hex colour codes (e.g. ``"#aabbcc"``).
    """
    colours = []
    for i in range(num_items):
        hue = i / max(1, num_items)
        # Convert HSV to RGB (simple formula)
        import colorsys

        r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.95)
        # Convert to 0‑255 range and hex
        colours.append("#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255)))
    return colours


###############################################################################
# GUI application


class QuranVisualizer:
    """A Tkinter application to visualise the Qurʼān on a square grid."""

    def __init__(self, words: List[WordCell]):
        # Ensure Tkinter is available
        _import_tkinter()
        # Inherit from tk.Tk after importing
        class _QuranWindow(tk.Tk):
            pass
        # Reassign our class to extend tk.Tk for proper MRO
        self.__class__ = _QuranWindow  # type: ignore
        _QuranWindow.__init__(self)
        self.title("Qurʼān Square Visualizer")
        self.words = words
        self.total = len(words)
        # Determine square size (number of columns/rows)
        self.side = int(math.ceil(math.sqrt(self.total)))
        # Pixel size of each cell.  Reduce this value if performance
        # becomes an issue; small values produce a more compact visualisation.
        self.cell_size = 6
        # Precompute colours for the 114 suras
        self.sura_colours = generate_colour_map(114)
        # Data mapping canvas items to WordCell objects
        self.item_to_cell: Dict[int, WordCell] = {}
        # Keep track of highlighted items
        self.highlighted_items: List[int] = []
        # Lines connecting highlighted items
        self.connection_lines: List[int] = []
        # Create GUI components
        self._create_widgets()
        # Populate canvas
        self._draw_grid()

    def _create_widgets(self) -> None:
        """Create and lay out the widgets (canvas, scrollbars, controls)."""
        # Top frame for controls
        control_frame = ttk.Frame(self)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=4, pady=4)

        # Word search controls
        ttk.Label(control_frame, text="Word search:").pack(side=tk.LEFT)
        self.word_var = tk.StringVar()
        word_entry = ttk.Entry(control_frame, textvariable=self.word_var, width=20)
        word_entry.pack(side=tk.LEFT)
        ttk.Button(
            control_frame,
            text="Search",
            command=self._search_word,
        ).pack(side=tk.LEFT, padx=(2, 8))

        # Ayah search controls
        ttk.Label(control_frame, text="Ayah (sura:ayah):").pack(side=tk.LEFT)
        self.ayah_var = tk.StringVar()
        ayah_entry = ttk.Entry(control_frame, textvariable=self.ayah_var, width=10)
        ayah_entry.pack(side=tk.LEFT)
        ttk.Button(
            control_frame,
            text="Go",
            command=self._search_ayah,
        ).pack(side=tk.LEFT, padx=(2, 8))

        # Root search controls
        ttk.Label(control_frame, text="Root (3 letters):").pack(side=tk.LEFT)
        self.root_var = tk.StringVar()
        root_entry = ttk.Entry(control_frame, textvariable=self.root_var, width=10)
        root_entry.pack(side=tk.LEFT)
        ttk.Button(
            control_frame,
            text="Find",
            command=self._search_root,
        ).pack(side=tk.LEFT, padx=(2, 8))

        # Phonological pattern search controls
        ttk.Label(control_frame, text="Phonological pattern:").pack(side=tk.LEFT)
        self.phono_var = tk.StringVar()
        phono_entry = ttk.Entry(control_frame, textvariable=self.phono_var, width=10)
        phono_entry.pack(side=tk.LEFT)
        ttk.Button(
            control_frame,
            text="Find",
            command=self._search_phono,
        ).pack(side=tk.LEFT, padx=(2, 8))

        # Checkbox to toggle connection lines
        self.draw_lines_var = tk.IntVar(value=0)
        ttk.Checkbutton(
            control_frame,
            text="Connect occurrences",
            variable=self.draw_lines_var,
            command=self._update_lines,
        ).pack(side=tk.LEFT, padx=(8, 8))

        # Sura selection
        ttk.Label(control_frame, text="Highlight sura:").pack(side=tk.LEFT)
        self.sura_choice = tk.StringVar(value="All")
        sura_options = ["All"] + [f"{i:03d}" for i in range(1, 115)]
        sura_menu = ttk.OptionMenu(
            control_frame,
            self.sura_choice,
            sura_options[0],
            *sura_options,
            command=lambda _: self._highlight_sura()
        )
        sura_menu.pack(side=tk.LEFT, padx=(2, 2))

        # Status bar
        self.status_var = tk.StringVar(value="Hover over a cell to see details.")
        status_label = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # Canvas with scrollbars
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(
            canvas_frame,
            bg="white",
            width=800,
            height=600,
            scrollregion=(0, 0, self.side * self.cell_size, self.side * self.cell_size),
        )
        h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        # Bind events for hover and click
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Button-1>", self._on_click)

    def _draw_grid(self) -> None:
        """Draw the square grid and assign canvas ids to word cells."""
        cell_size = self.cell_size
        side = self.side
        for idx, cell in enumerate(self.words):
            r = idx // side
            c = idx % side
            x0 = c * cell_size
            y0 = r * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            colour = self.sura_colours[(cell.sura - 1) % len(self.sura_colours)]
            item = self.canvas.create_rectangle(x0, y0, x1, y1, fill=colour, outline="")
            cell.canvas_id = item
            cell.row = r
            cell.col = c
            self.item_to_cell[item] = cell
        # Fill remaining grid positions with blank cells (optional: draw border)
        for idx in range(len(self.words), side * side):
            r = idx // side
            c = idx % side
            x0 = c * cell_size
            y0 = r * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="white", outline="")

    def _on_mouse_move(self, event: object) -> None:
        """Update the status bar with information about the cell under the cursor."""
        # Translate screen coordinates to canvas coordinates
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        # Find the closest item (rectangle) at this coordinate
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        if not items:
            self.status_var.set("")
            return
        item = items[-1]
        cell = self.item_to_cell.get(item)
        if cell:
            self.status_var.set(
                f"Sura {cell.sura}, Ayah {cell.ayah}, Word: {cell.text}"
            )

    def _on_click(self, event: object) -> None:
        """Fix the status display on click and show details for the clicked cell."""
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        if not items:
            return
        item = items[-1]
        cell = self.item_to_cell.get(item)
        if cell:
            messagebox.showinfo(
                "Word details",
                f"Sura {cell.sura}\nAyah {cell.ayah}\nWord: {cell.text}\nSimplified: {cell.clean}"
            )

    def _clear_highlights(self) -> None:
        """Remove any existing highlight colours and connection lines."""
        # Reset fill colour for previously highlighted items
        for item in self.highlighted_items:
            cell = self.item_to_cell.get(item)
            if cell:
                colour = self.sura_colours[(cell.sura - 1) % len(self.sura_colours)]
                self.canvas.itemconfigure(item, fill=colour)
        self.highlighted_items.clear()
        # Remove connection lines
        for line in self.connection_lines:
            self.canvas.delete(line)
        self.connection_lines.clear()

    def _highlight_cells(self, items: List[int], highlight_colour: str = "#ff0000") -> None:
        """Highlight specified canvas items with a given colour."""
        for item in items:
            self.canvas.itemconfigure(item, fill=highlight_colour)
        self.highlighted_items = items
        self._update_lines()

    def _update_lines(self) -> None:
        """Update or remove connection lines based on the current highlighted items."""
        # Remove any existing lines
        for line in self.connection_lines:
            self.canvas.delete(line)
        self.connection_lines.clear()
        if not self.draw_lines_var.get():
            return
        if len(self.highlighted_items) < 2:
            return
        # Draw lines connecting consecutive highlighted cells in the order of appearance
        sorted_items = sorted(
            self.highlighted_items,
            key=lambda i: (self.item_to_cell[i].row, self.item_to_cell[i].col),
        )
        for i in range(len(sorted_items) - 1):
            item1 = sorted_items[i]
            item2 = sorted_items[i + 1]
            c1 = self.item_to_cell[item1]
            c2 = self.item_to_cell[item2]
            # Compute centre coordinates of each cell
            x1 = c1.col * self.cell_size + self.cell_size / 2
            y1 = c1.row * self.cell_size + self.cell_size / 2
            x2 = c2.col * self.cell_size + self.cell_size / 2
            y2 = c2.row * self.cell_size + self.cell_size / 2
            line = self.canvas.create_line(x1, y1, x2, y2, fill="blue", width=1.0)
            self.connection_lines.append(line)

    def _search_word(self) -> None:
        """Highlight cells whose cleaned word contains the search term."""
        term = remove_diacritics(self.word_var.get().strip())
        self._clear_highlights()
        if not term:
            return
        matches = [cell.canvas_id for cell in self.words if term in cell.clean]
        self._highlight_cells(matches, highlight_colour="#ffcc00")

    def _search_ayah(self) -> None:
        """Highlight all cells belonging to the specified sura and ayah."""
        query = self.ayah_var.get().strip()
        self._clear_highlights()
        if not query:
            return
        try:
            parts = query.split(":")
            sura_num = int(parts[0])
            ayah_num = int(parts[1]) if len(parts) > 1 else 1
        except (ValueError, IndexError):
            messagebox.showerror("Invalid format", "Please enter in the form sura:ayah, e.g. 2:255")
            return
        matches = [cell.canvas_id for cell in self.words if cell.sura == sura_num and cell.ayah == ayah_num]
        self._highlight_cells(matches, highlight_colour="#66ccff")

    def _search_root(self) -> None:
        """Heuristic search for words containing the letters of a root in order."""
        root = remove_diacritics(self.root_var.get().strip())
        self._clear_highlights()
        if not root:
            return
        # Only consider first 3 letters of root for triliteral roots
        root_letters = [ch for ch in root if unicodedata.category(ch).startswith("L")][:3]
        if not root_letters:
            return
        matches: List[int] = []
        for cell in self.words:
            # Skip if cell.clean shorter than root
            if len(cell.clean) < len(root_letters):
                continue
            pos = 0
            found = True
            for letter in root_letters:
                idx = cell.clean.find(letter, pos)
                if idx == -1:
                    found = False
                    break
                pos = idx + 1
            if found:
                matches.append(cell.canvas_id)
        self._highlight_cells(matches, highlight_colour="#99ff99")

    def _search_phono(self) -> None:
        """Search for a phonological pattern (substring) in simplified words."""
        pattern = remove_diacritics(self.phono_var.get().strip())
        self._clear_highlights()
        if not pattern:
            return
        matches = [cell.canvas_id for cell in self.words if pattern in cell.clean]
        self._highlight_cells(matches, highlight_colour="#ff99cc")

    def _highlight_sura(self) -> None:
        """Highlight all cells of the selected sura, or reset to default if 'All'."""
        choice = self.sura_choice.get()
        self._clear_highlights()
        if choice == "All":
            return
        try:
            sura_num = int(choice)
        except ValueError:
            return
        matches = [cell.canvas_id for cell in self.words if cell.sura == sura_num]
        self._highlight_cells(matches, highlight_colour=self.sura_colours[(sura_num - 1) % len(self.sura_colours)])


###############################################################################
# Main entry point


def main() -> None:
    """Launch the Qurʼān visualiser.

    This function attempts to load the Qurʼān text from a local JSON file
    named ``quran.json`` in the current working directory.  If the file
    exists and is readable, it is parsed using :func:`load_quran_local`.
    Otherwise, the program falls back to fetching the text from the
    public API at ``api.alquran.cloud`` via :func:`load_quran_text`.

    The local file option allows the visualiser to operate offline
    after a single download of the dataset, which is particularly
    useful in environments where outbound HTTP requests are restricted.
    """
    import os

    local_path = os.path.join(os.path.dirname(__file__), "quran.json")
    words: List[WordCell]
    if os.path.isfile(local_path):
        try:
            print(f"Loading Qurʼān from local file {local_path}…")
            words = load_quran_local(local_path)
        except Exception as exc:
            print(f"Failed to load local file: {exc}. Falling back to API.")
            words = None  # type: ignore
    else:
        words = None  # type: ignore

    if not words:
        # API endpoint for the complete Qurʼān in Uthmānī script
        QURAN_API_URL = "https://api.alquran.cloud/v1/quran/quran-uthmani"
        words = load_quran_text(QURAN_API_URL)

    app = QuranVisualizer(words)
    app.mainloop()


if __name__ == "__main__":
    main()