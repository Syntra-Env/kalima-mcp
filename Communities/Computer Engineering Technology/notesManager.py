import curses
import glob
import json
import os
import re
import sys
import textwrap
import webbrowser


# ---------------- Utility Functions ----------------

def load_items_from_md(file_path):
    """
    Load items from a markdown file.
    Each non‑empty line becomes a dictionary with its text.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return [{"text": line.strip()} for line in f if line.strip()]


def extract_references(text):
    """
    Extract reference strings from text, maintaining their exact positions and grouping.
    Returns a list of tuples: (position, numbers, original_text)
    """
    pattern = re.compile(r'\[(\d+(?:-\d+)?(?:,\s?\d+(?:-\d+)?)*)\]')
    result = []
    
    for match in pattern.finditer(text):
        numbers = []
        ref_str = match.group(1)
        # Parse individual references and ranges
        for part in ref_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                numbers.extend(range(start, end + 1))
            else:
                numbers.append(int(part))
        # Store position, numbers, and original text
        result.append((match.start(), numbers, match.group(0)))
    
    return sorted(result, key=lambda x: x[0])


def parse_reference_string(ref_string):
    """
    Given a reference string (e.g. "3, 5-7"), return a list of all references as integers.
    """
    refs = []
    for part in ref_string.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            refs.extend(range(start, end + 1))
        else:
            refs.append(int(part))
    return refs


def compress_refs(ref_groups):
    """
    Compress reference numbers into bracketed groups.
    Each inner list in ref_groups represents reference numbers that appeared together in the text.
    Only compress consecutive numbers that appeared together in the text.
    """
    if not ref_groups:
        return ""
        
    out = []
    for group in ref_groups:
        if len(group) == 1:
            out.append(f"[{group[0]}]")
            continue
            
        # Sort numbers within each group while keeping groups separate
        sorted_nums = sorted(group)
        subgroups = []
        current = [sorted_nums[0]]
        
        # Only compress consecutive numbers within the same group
        for num in sorted_nums[1:]:
            if num == current[-1] + 1:
                current.append(num)
            else:
                subgroups.append(current)
                current = [num]
        subgroups.append(current)
        
        # Format each subgroup
        for nums in subgroups:
            if len(nums) == 1:
                out.append(f"[{nums[0]}]")
            else:
                out.append(f"[{nums[0]}-{nums[-1]}]")
                
    return " ".join(out)


def update_references(original_index_map, reverse_index_map):
    """
    Update the reference strings inside each item.
    Maintains the exact positions and grouping of references as they appear in the text.
    """
    updated_items = []
    
    for orig_idx in range(len(original_index_map)):
        text = original_index_map[orig_idx]
        refs = extract_references(text)
        
        if refs:
            # Start with the original text and replace references from end to beginning
            # to maintain correct positions
            result = text
            for pos, numbers, orig_text in reversed(refs):
                # Map the numbers to their new positions
                new_refs = [reverse_index_map[ref] for ref in numbers if ref in reverse_index_map]
                if new_refs:
                    # Maintain single group compression only when original had it
                    if len(numbers) > 1 and all(a + 1 == b for a, b in zip(numbers[:-1], numbers[1:])):
                        # Original was a range, try to keep it as range if possible
                        new_refs = sorted(new_refs)
                        if all(a + 1 == b for a, b in zip(new_refs[:-1], new_refs[1:])):
                            new_ref_text = f"[{new_refs[0]}-{new_refs[-1]}]"
                        else:
                            new_ref_text = f"[{','.join(map(str, new_refs))}]"
                    else:
                        # Original was separate numbers
                        new_ref_text = f"[{','.join(map(str, new_refs))}]"
                    
                    result = result[:pos] + new_ref_text + result[pos + len(orig_text):]
            
            updated_items.append(result.strip())
        else:
            updated_items.append(text)
    
    return updated_items


def update_item_index(item_text, new_index):
    """
    Remove any existing leading number (and period) in item_text,
    then prepend new_index followed by a period.
    """
    text = re.sub(r'^\d+\.\s*', '', item_text)
    return f"{new_index}. {text}"


def display_help(stdscr):
    """Display a centered help menu with a color legend."""
    stdscr.clear()
    help_lines = [
        "HELP MENU",
        "",
        "UP/DOWN/LEFT/RIGHT: Navigate or move items",
        "Enter: Edit item",
        "/: Search",
        "m: Move item",
        "l: Toggle line highlighting",
        "h: Help menu",
        "q: Quit",
        "s: Save changes",
        "w: Web search",
        "",
        "Color Legend:",
        "Blue: No links",
        "Green: Single link",
        "Cyan: Continuous link",
        "Magenta: Discontinuous links",
        "Yellow: Linked-to item",
        "",
        "Press any key to return..."
    ]
    max_y, max_x = stdscr.getmaxyx()
    start_y = max(0, (max_y - len(help_lines)) // 2)  # Ensure start_y is non-negative
    for idx, line in enumerate(help_lines):
        x = max(0, (max_x - len(line)) // 2)  # Ensure x is non-negative
        if start_y + idx < max_y:  # Ensure we don't write beyond the screen height
            stdscr.addnstr(start_y + idx, x, line, max_x - x)  # Adjust max length to fit within the screen width
    stdscr.refresh()
    stdscr.getch()


def search_in_edge(text):
    """Search the given text in available web browser."""
    # Remove item number and references
    clean_text = re.sub(r'^\d+\.\s*', '', text)  # Remove leading number
    clean_text = re.sub(r'\[\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*\]', '', clean_text)  # Remove references
    query = clean_text.strip()
    
    # Try to find an available browser
    try:
        # Try browsers in order of preference
        for browser in ['edge', 'chrome', 'firefox', 'safari', 'opera']:
            try:
                webbrowser.get(browser).open(f'https://www.bing.com/search?q={query}')
                return
            except webbrowser.Error:
                continue
        
        # If no specific browser works, use the default
        webbrowser.open(f'https://www.bing.com/search?q={query}')
    except Exception:
        # If all fails, try one last time with the generic open
        try:
            webbrowser.open_new(f'https://www.bing.com/search?q={query}')
        except Exception:
            pass  # Silently fail if no browser can be opened


# ---------------- Main Interactive Editor ----------------

def interactive_edit(stdscr, original_index_map):
    """
    Main interactive editor using curses.
    Supports navigating, editing, search, move and help commands.
    """
    curses.curs_set(1)
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    # Color pairs for various highlights
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_YELLOW)    # Selection highlight (base)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)       # Inline editing cursor
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)      # No links highlight
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_CYAN)      # Single link highlight
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_GREEN)     # Continuous link highlight
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_MAGENTA)   # Discontinuous links highlight
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_WHITE)     # Selected text: black on white
    curses.init_pair(8, curses.COLOR_YELLOW, curses.COLOR_BLUE)     # Linked-to highlight

    line_highlighting = True  # New: line highlighting enabled by default

    current_order = list(range(len(original_index_map)))
    cursor = 0
    editing = False
    edit_buffer = ""
    edit_cursor = 0
    scroll_offset = 0
    status_message = "NORMAL mode"

    # Search mode variables
    searching = False
    search_buffer = ""
    search_index = 0
    filtered_items = []  # Add filtered items list for search mode

    # Move mode variables
    move_mode = False
    move_buffer = ""
    move_search_index = 0
    move_source = None

    # Setup double buffering
    curses.use_default_colors()
    stdscr.nodelay(0)
    stdscr.timeout(-1)

    while True:
        # Only clear when mode changes or content updates
        if editing or searching or move_mode:
            stdscr.erase()  # Use erase instead of clear for smoother updates
        else:
            stdscr.erase()

        max_y, max_x = stdscr.getmaxyx()
        available_rows = max_y - 3  # bottom status line & margin

        reverse_index_map = {orig_idx: new_idx for new_idx, orig_idx in enumerate(current_order)}
        updated_items = update_references(original_index_map, reverse_index_map)

        # Compute a mapping of incoming links for each item.
        incoming_links = {i: 0 for i in range(len(original_index_map))}
        for idx in current_order:
            item_text = updated_items[idx]
            ref_matches = re.findall(r'\[(\d+(?:-\d+)?(?:,\s?\d+(?:-\d+)?)*)\]', item_text)
            for ref_str in ref_matches:
                numbers = parse_reference_string(ref_str)
                for num in numbers:
                    if num in incoming_links:
                        incoming_links[num] += 1

        # Compute absolute y-positions for items (taking wrapping into account)
        item_y_positions = []
        y = 2  # start drawing items at y=2
        for idx in current_order:
            item_index = reverse_index_map[idx]
            text = update_item_index(updated_items[idx], item_index)
            wrapped = textwrap.wrap(text, width=max_x - 1) or [""]
            item_y_positions.append(y)
            y += len(wrapped)
        content_height = y

        # Compute display y for current cursor.
        display_y = item_y_positions[cursor] - item_y_positions[scroll_offset] + 2
        # Adjust scroll_offset if needed.
        while scroll_offset > 0 and display_y < 2:
            scroll_offset -= 1
            display_y = item_y_positions[cursor] - item_y_positions[scroll_offset] + 2
        while display_y >= max_y - 1:
            scroll_offset += 1
            if scroll_offset >= len(item_y_positions):
                scroll_offset = len(item_y_positions) - 1
                break
            display_y = item_y_positions[cursor] - item_y_positions[scroll_offset] + 2

        # Adjust drawing logic for search mode
        if searching:
            # Filter items that match search term
            filtered_items = [idx for idx in range(len(current_order))
                              if search_buffer.lower() in update_item_index(
                                  updated_items[current_order[idx]], idx).lower()]

            # Draw only filtered items
            y_pos = 2
            for item_idx in filtered_items:
                idx = current_order[item_idx]
                item_index = reverse_index_map[idx]
                displayed_text = update_item_index(updated_items[idx], item_index)
                wrapped_lines = textwrap.wrap(displayed_text, width=max_x - 1) or [""]

                for line in wrapped_lines:
                    if y_pos >= max_y - 1:
                        break
                    line_padded = line.ljust(max_x - 1)
                    if item_idx == filtered_items[search_index % len(filtered_items)] if filtered_items else -1:
                        stdscr.attron(curses.color_pair(7))
                        stdscr.addnstr(y_pos, 0, line_padded, max_x - 1)
                        stdscr.attroff(curses.color_pair(7))
                    else:
                        stdscr.addnstr(y_pos, 0, line_padded, max_x - 1)
                    y_pos += 1
        else:
            # Original drawing code for normal mode
            y_pos = 2
            for idx in current_order[scroll_offset:]:
                item_index = reverse_index_map[idx]
                displayed_text = update_item_index(updated_items[idx], item_index)
                wrapped_lines = textwrap.wrap(displayed_text, width=max_x - 1) or [""]
                refs_in_item = re.findall(r'\[[^\]]+\]', displayed_text)
                # Default color choices based on references.
                if not refs_in_item:
                    color_pair = curses.color_pair(3)
                elif len(refs_in_item) == 1:
                    if '-' in refs_in_item[0]:
                        color_pair = curses.color_pair(5)
                    else:
                        color_pair = curses.color_pair(4)
                else:
                    color_pair = curses.color_pair(6)

                # If the item is linked to (incoming link count > 0), override with color pair 8.
                if incoming_links.get(item_index, 0) > 0:
                    chosen_color = curses.color_pair(8)
                else:
                    chosen_color = color_pair

                for line in wrapped_lines:
                    if y_pos >= max_y - 1:
                        break
                    # Pad the line so the background covers the full width.
                    line_padded = line.ljust(max_x - 1)
                    if item_index == cursor:
                        stdscr.attron(curses.color_pair(7))
                        stdscr.addnstr(y_pos, 0, line_padded, max_x - 1)
                        stdscr.attroff(curses.color_pair(7))
                    else:
                        if line_highlighting:
                            stdscr.addnstr(y_pos, 0, line_padded, max_x - 1, chosen_color)
                        else:
                            stdscr.addnstr(y_pos, 0, line_padded, max_x - 1)
                    y_pos += 1

        # In edit mode, display the edit buffer with inline cursor highlight.
        if editing:
            line_base = item_y_positions[cursor] - item_y_positions[scroll_offset] + 2
            wrap_width = max_x - 1
            
            # Show index prefix (uneditable) followed by edit buffer
            index_prefix = f"{reverse_index_map[current_order[cursor]]}. "
            display_text = index_prefix + edit_buffer
            wrapped = textwrap.wrap(display_text, width=wrap_width) or [""]

            # Draw all wrapped lines
            edit_y = line_base
            for line in wrapped:
                stdscr.addnstr(edit_y, 0, line.ljust(wrap_width), wrap_width)
                edit_y += 1

            # Compute cursor position (offset by index prefix length on first line)
            cursor_line = 0
            cursor_x = len(index_prefix) + edit_cursor
            
            # Show cursor (always visible)
            highlight_y = line_base + cursor_line
            stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            if cursor_x < len(wrapped[cursor_line]):
                stdscr.addch(highlight_y, cursor_x, wrapped[cursor_line][cursor_x])
            else:
                stdscr.addch(highlight_y, cursor_x, ' ')  # Show cursor even after text
            stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            stdscr.move(highlight_y, cursor_x)

        # Bottom status/search line.
        if searching:
            bottom_line = "/" + search_buffer
        elif move_mode:
            bottom_line = "Move: " + move_buffer
        else:
            mode_indicator = "INSERT" if editing else "NORMAL"
            bottom_line = f"-- {mode_indicator} -- | {status_message}"
        stdscr.addstr(max_y - 1, 0, bottom_line[:max_x - 1])

        # Batch all screen updates and refresh once
        stdscr.noutrefresh()
        curses.doupdate()

        key = stdscr.getch()

        # ---------- HELP COMMAND ----------
        if key == ord('h') and not (editing or searching or move_mode):  # Only allow in normal mode
            display_help(stdscr)
            continue

        # ---------- MOVE MODE ----------
        if move_mode:
            if key in (curses.KEY_BACKSPACE, 127, 8):
                move_buffer = move_buffer[:-1]
                move_search_index = 0
            elif key in (10, 13):
                move_matches = [idx for idx in range(len(current_order))
                                if move_buffer.lower() in update_item_index(
                                    updated_items[current_order[idx]], idx).lower()]
                if move_matches:
                    target = move_matches[move_search_index % len(move_matches)]
                    moved_item = current_order.pop(move_source)
                    if move_source < target:
                        target -= 1
                    current_order.insert(target + 1, moved_item)
                    cursor = target + 1
                    status_message = f"Item moved to position {cursor}."
                else:
                    status_message = "No matching move target found."
                move_mode = False
                move_buffer = ""
                move_search_index = 0
                move_source = None
            elif key == 27:
                move_mode = False
                move_buffer = ""
                move_search_index = 0
                move_source = None
                status_message = "Move cancelled."
            elif key == curses.KEY_DOWN:
                move_search_index += 1
            elif key == curses.KEY_UP:
                move_search_index -= 1
            elif 32 <= key <= 126:
                move_buffer += chr(key)
                move_search_index = 0

            if move_buffer:
                move_matches = [idx for idx in range(len(current_order))
                                if move_buffer.lower() in update_item_index(
                                    updated_items[current_order[idx]], idx).lower()]
                if move_matches:
                    move_search_index %= len(move_matches)
                    target = move_matches[move_search_index]
                    cursor = target
                    status_message = f"Move target {move_search_index+1} of {len(move_matches)} selected."
                else:
                    status_message = "No matching move target found."
            else:
                status_message = "Move mode: enter target search term."
            continue

        # ---------- SEARCH MODE ----------
        if searching:
            if key in (10, 13) and filtered_items:  # Enter with matches
                cursor = filtered_items[search_index % len(filtered_items)]
                searching = False
                search_buffer = ""
                status_message = "Search item selected."
            elif key == 27:  # Escape
                searching = False
                search_buffer = ""
                status_message = "Search cancelled."
            elif key == curses.KEY_DOWN and filtered_items:
                search_index = (search_index + 1) % len(filtered_items)
            elif key == curses.KEY_UP and filtered_items:
                search_index = (search_index - 1) % len(filtered_items)
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                search_buffer = search_buffer[:-1]
                search_index = 0
            elif 32 <= key <= 126:  # Printable characters
                search_buffer += chr(key)
                search_index = 0

            if search_buffer and key not in (curses.KEY_UP, curses.KEY_DOWN):
                filtered_items = [idx for idx in range(len(current_order))
                                  if search_buffer.lower() in update_item_index(
                                      updated_items[current_order[idx]], idx).lower()]
                if filtered_items:
                    if search_index >= len(filtered_items):
                        search_index = 0
                    cursor = filtered_items[search_index]
                    status_message = f"Search result {search_index+1} of {len(filtered_items)} selected."
            continue

        # ---------- EDIT MODE ----------
        if editing:
            if key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                if key == curses.KEY_LEFT and edit_cursor > 0:
                    edit_cursor -= 1
                elif key == curses.KEY_RIGHT and edit_cursor < len(edit_buffer):
                    edit_cursor += 1
            elif key in (10, 13):  # Enter to save
                original_index_map[current_order[cursor]] = edit_buffer
                editing = False
                status_message = "Edit saved."
            elif key == 27:  # Escape to cancel
                editing = False
                status_message = "Edit cancelled."
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if edit_cursor > 0:
                    edit_buffer = edit_buffer[:edit_cursor-1] + edit_buffer[edit_cursor:]
                    edit_cursor -= 1
            elif 32 <= key <= 126:  # Printable characters
                edit_buffer = edit_buffer[:edit_cursor] + chr(key) + edit_buffer[edit_cursor:]
                edit_cursor += 1
            continue

        # ---------- NORMAL MODE ----------
        if key in (10, 13):  # Enter to start editing
            new_index = reverse_index_map[current_order[cursor]]
            base_text = re.sub(r'^\d+\.\s*', '', updated_items[current_order[cursor]])
            # Keep the index prefix separate from editable content
            index_prefix = f"{new_index}. "
            edit_buffer = base_text
            edit_cursor = 0  # Start at beginning of editable text
            editing = True
            status_message = "Editing item."
            continue

        if key == ord('m'):
            move_mode = True
            move_buffer = ""
            move_search_index = 0
            move_source = cursor
            status_message = "Move mode: enter target search term."
            continue
        elif key == ord('/'):
            searching = True
            search_buffer = ""
            search_index = 0
            status_message = "Searching..."
        elif key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
            status_message = f"Selection moved to {cursor}."
        elif key == curses.KEY_DOWN:
            cursor = min(len(current_order) - 1, cursor + 1)
            status_message = f"Selection moved to {cursor}."
        elif key == curses.KEY_LEFT:
            if cursor > 0:
                current_order[cursor], current_order[cursor - 1] = current_order[cursor - 1], current_order[cursor]
                cursor -= 1
                status_message = f"Item moved to position {cursor}."
        elif key == curses.KEY_RIGHT:
            if cursor < len(current_order) - 1:
                current_order[cursor], current_order[cursor + 1] = current_order[cursor + 1], current_order[cursor]
                cursor += 1
                status_message = f"Item moved to position {cursor}."
        elif key == ord('l'):
            line_highlighting = not line_highlighting
            status_message = "Line highlighting " + ("enabled." if line_highlighting else "disabled.")
        elif key == ord('a') and not (editing or searching or move_mode):  # Add new item in normal mode
            new_item_text = "New Item"  # Default text for the new item
            current_order.insert(cursor + 1, len(original_index_map))  # Insert new item after the current one
            original_index_map[len(original_index_map)] = new_item_text  # Add to the original index map
            cursor += 1  # Move cursor to the new item
            status_message = "New item added."
            continue
        elif key == ord('d') and not (editing or searching or move_mode):  # Delete selected item in normal mode
            if len(current_order) > 1:  # Ensure at least one item remains
                deleted_item = current_order.pop(cursor)  # Remove the selected item
                del original_index_map[deleted_item]  # Remove from the original index map

                # Update cursor position
                if cursor >= len(current_order):
                    cursor = len(current_order) - 1

                # Rebuild reverse_index_map and update references
                reverse_index_map = {orig_idx: new_idx for new_idx, orig_idx in enumerate(current_order)}
                updated_items = update_references(original_index_map, reverse_index_map)

                # Update indexes in original_index_map
                for i, orig_idx in enumerate(current_order):
                    original_index_map[orig_idx] = update_item_index(updated_items[orig_idx], i)

                status_message = "Item deleted."
            else:
                status_message = "Cannot delete the last remaining item."
            continue
        elif key == ord('s') and not (editing or searching or move_mode):  # Save command in normal mode
            reverse_index_map = {orig_idx: new_idx for new_idx, orig_idx in enumerate(current_order)}
            updated_items = update_references(original_index_map, reverse_index_map)
            final_items = [update_item_index(updated_items[orig_idx], i) for i, orig_idx in enumerate(current_order)]
            with open("output.md", "w", encoding="utf-8") as f:  # Save to the original markdown file
                for line in final_items:
                    f.write(line + "\n")
            status_message = "Changes saved to file."
            continue
        elif key == ord('w') and not (editing or searching or move_mode):  # Web search in normal mode
            current_text = updated_items[current_order[cursor]]
            search_in_edge(current_text)
            status_message = "Searching in Edge..."
            continue
        elif key == ord('q'):
            break

    return current_order


# ---------------- Main Entry Point ----------------

def main():
    os.system('cls')  # Clear terminal before starting curses
    md_files = glob.glob("*.md")
    if not md_files:
        print("No markdown file found in the current directory!")
        sys.exit(1)
    markdown_file = md_files[0]
    items = load_items_from_md(markdown_file)
    original_index_map = {i: items[i]["text"] for i in range(len(items))}
    current_order = curses.wrapper(interactive_edit, original_index_map)
    
    reverse_index_map = {orig_idx: new_idx for new_idx, orig_idx in enumerate(current_order)}
    updated_items = update_references(original_index_map, reverse_index_map)
    final_items = [update_item_index(updated_items[orig_idx], i) for i, orig_idx in enumerate(current_order)]
    
    # Save the final items back to the markdown file
    with open(markdown_file, "w", encoding="utf-8") as f:
        for line in final_items:
            f.write(line + "\n")
    
    os.system('cls')  # Clear terminal after curses
    print("\nFinal Output (file updated):")
    for line in final_items:
        print(line)


if __name__ == "__main__":
    main()